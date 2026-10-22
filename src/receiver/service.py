"""Independent receiver: authenticate signed attempts, persist once, sign receipts."""

import json
import os
import time
from pathlib import Path
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request

from core.canonical import Json, bytes_hash, digest
from core.crypto import Keys, verify
from receiver.storage import InboxStore


class LocalReceiver:
    """Synthetic inbox with stable signed receipts and isolated persistent keys."""

    def __init__(self, directory: Path, trusted: dict[str, str]) -> None:
        self.store = InboxStore(directory / "receiver_inbox.db")
        self.keys = Keys(directory / "receiver-keys", ("receiver",))
        self.trusted = trusted
        self.lose_response = False
        self.unavailable = False

    def receive(self, envelope: Json) -> Json:
        """Verify executor signature, deduplicate the exact payload, and issue a receipt."""
        if self.unavailable:
            raise TimeoutError("receiver unavailable")
        role = envelope.get("key_id")
        if role not in ("B", "C"):
            raise ValueError("WRONG_ACTOR")
        document = cast(str, envelope["document"])
        signed = {key: value for key, value in envelope.items() if key != "document"}
        payload = verify(signed, self.trusted, role)
        if (
            cast(str, payload["authenticated_actor"]) != role
            or cast(str, payload["recipient_id"]) != "Anna"
            or cast(str, payload["snapshot_hash"]) != bytes_hash(document.encode())
            or (cast(str, payload["action"]) != "deliver_document")
            or (cast(str, payload["audience"]) != "synthetic-inbox")
        ):
            raise ValueError("SCOPE_ESCALATION")
        key = cast(str, payload["idempotency_key"])
        with self.store.connection() as db:
            existing = self.store.get(db, "message", key)
            if existing:
                if existing["digest"] != digest(payload):
                    raise ValueError("IDEMPOTENCY_CONFLICT")
                return cast(Json, existing["receipt"])
            receipt = self.keys.signed(
                "receiver",
                {
                    "receipt_id": str(uuid4()),
                    "attempt_id": cast(str, payload["attempt_id"]),
                    "root_id": cast(str, payload["root_id"]),
                    "child_id": cast(str, payload["child_id"]),
                    "case_id": cast(str, payload["case_id"]),
                    "receiver_id": "synthetic-inbox",
                    "snapshot_hash": cast(str, payload["snapshot_hash"]),
                    "recipient_id": cast(str, payload["recipient_id"]),
                    "idempotency_key": key,
                    "received_at": time.time(),
                },
            )
            self.store.put(
                db,
                "message",
                key,
                {"digest": digest(payload), "receipt": receipt, "document": document},
            )
        if self.lose_response:
            raise TimeoutError("response lost after durable acceptance")
        return receipt

    def lookup(self, key: str) -> Json | None:
        """Read an existing receipt; reconciliation never dispatches."""
        with self.store.connection() as db:
            message = self.store.get(db, "message", key)
            return cast(Json, message["receipt"]) if message else None

    def inbox(self) -> list[Json]:
        """Return persisted synthetic messages to the trusted app transport."""
        with self.store.connection() as db:
            return self.store.all(db, "message")


def create_app() -> FastAPI:
    """Create the private-network receiver; every data route uses signed requests."""
    directory = Path(os.environ.get("LEDGER_DATA", "/data"))
    directory.mkdir(parents=True, exist_ok=True)
    keys_path = Path(os.environ.get("LEDGER_PUBLIC_KEYS", "/trust/public.json"))
    receiver = LocalReceiver(directory, {})
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def trust() -> dict[str, str]:
        return cast(dict[str, str], json.loads(keys_path.read_text()))

    @app.get("/health")
    def health() -> Json:
        return {"status": "ok"}

    @app.post("/rpc")
    async def rpc(request: Request) -> Json:
        try:
            envelope = await request.json()
            receiver.trusted = trust()
            role = envelope.get("key_id")
            if role in ("B", "C"):
                return {"receipt": receiver.receive(envelope)}
            query = verify(envelope, receiver.trusted, "authorization")
            if abs(time.time() - cast(float, query["time"])) > 30:
                raise ValueError("EXPIRED")
            if query["operation"] == "lookup":
                return {"receipt": receiver.lookup(cast(str, query["idempotency_key"]))}
            if query["operation"] == "inbox":
                return {"messages": receiver.inbox()}
            raise ValueError("INVALID_INPUT")
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise HTTPException(403, "INVALID_RECEIVER_REQUEST") from error

    @app.get("/public-key")
    def public_key() -> dict[str, str]:
        return receiver.keys.public

    return app
