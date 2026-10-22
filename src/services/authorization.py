"""Authorization, authenticated proposals and transactional root-wide reservations."""

import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import cast
from uuid import uuid4

import httpx

from core.canonical import Json, bytes_hash, digest
from core.crypto import Keys, verify
from core.models import ChildProposal, ExecutionProposal, RootProposal
from receiver.service import LocalReceiver
from services.ledger import append
from services.storage import Store

DOCUMENTS = {
    "doc-v1": {
        "document_id": "doc-v1",
        "version_id": "v1",
        "bytes": "Synthetic delegation document v1. No personal data.",
    },
    "doc-v2": {
        "document_id": "doc-v2",
        "version_id": "v2",
        "bytes": "Synthetic delegation document v2. Changed content.",
    },
}
for _document in DOCUMENTS.values():
    _document["snapshot_hash"] = bytes_hash(_document["bytes"].encode())


class Denied(Exception):
    """A fail-closed domain decision with a safe, stable reason code."""

    def __init__(self, reason: str, status: int = 403) -> None:
        self.reason = reason
        self.status = status
        super().__init__(reason)


class RemoteReceiver:
    """Bounded private-network transport; no automatic retry of external effects."""

    def __init__(self, url: str, keys: Keys) -> None:
        self.url = url.rstrip("/")
        self.keys = keys

    def public(self) -> dict[str, str]:
        """Obtain receiver public key during trusted private-network provisioning."""
        with httpx.Client(timeout=5, trust_env=False) as client:
            result = client.get(self.url + "/public-key")
            result.raise_for_status()
            return cast(dict[str, str], result.json())

    def receive(self, envelope: Json) -> Json:
        """Send one signed executor attempt exactly once."""
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.post(self.url + "/rpc", json=envelope)
            response.raise_for_status()
            return cast(Json, response.json()["receipt"])

    def query(self, operation: str, **fields: object) -> Json:
        """Sign a read-only service query; credentials never enter URLs."""
        signed = self.keys.signed(
            "authorization", {"operation": operation, "time": time.time(), **fields}
        )
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.post(self.url + "/rpc", json=signed)
            response.raise_for_status()
            return cast(Json, response.json())

    def lookup(self, key: str) -> Json | None:
        """Look up a receipt without dispatching."""
        return cast(Json | None, cast(Json, self.query("lookup", idempotency_key=key)["receipt"]))

    def inbox(self) -> list[Json]:
        """Read the isolated synthetic inbox."""
        return cast(list[Json], self.query("inbox")["messages"])


class Runtime:
    """Own one case and enforce capabilities at each durable transition."""

    def __init__(self, directory: Path, testing: bool = False) -> None:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory = directory
        self.keys = Keys(directory / "keys")
        self.keys.publish(directory / "public.json")
        if not testing:
            self.keys.publish(Path(os.environ["LEDGER_PUBLIC_OUTPUT"]))
        credentials_path = directory / "credentials.json"
        if not credentials_path.exists():
            fd = os.open(credentials_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as output:
                json.dump(
                    {role: secrets.token_urlsafe(32) for role in ("owner", "A", "B", "C")}, output
                )
        self.credentials: dict[str, str] = json.loads(credentials_path.read_text())
        self.store = Store(directory / "ledger.db")
        self.clock = time.time
        self.testing = testing
        self.fail_result_write = False
        if testing:
            local = LocalReceiver(directory, self.keys.public.copy())
            self.receiver: LocalReceiver | RemoteReceiver = local
            self.keys.public.update(local.keys.public)
        else:
            self.receiver = RemoteReceiver(os.environ["LEDGER_RECEIVER_URL"], self.keys)
            receiver_file = directory / "receiver-public.json"
            if receiver_file.exists():
                self.keys.public.update(json.loads(receiver_file.read_text()))
        with self.store.connection() as db:
            for attempt in self.store.all(db, "attempt"):
                if attempt["execution_status"] in ("reserved", "dispatching"):
                    attempt["execution_status"] = "uncertain"
                    self.store.put(db, "attempt", cast(str, attempt["attempt_id"]), attempt)
                    self.event(db, "RECOVERY_UNCERTAIN", "authorization", attempt)

    def receiver_key(self) -> None:
        """Pin receiver identity once; never silently accept key rotation."""
        if "receiver" not in self.keys.public and isinstance(self.receiver, RemoteReceiver):
            public = self.receiver.public()
            if set(public) != {"receiver"}:
                raise ValueError("UNKNOWN_KEY")
            self.keys.public.update(public)
            (self.directory / "receiver-public.json").write_text(json.dumps(public))

    def principal(self, token: str) -> str:
        """Derive actor only from a provisioned opaque credential."""
        for role, credential in self.credentials.items():
            if hmac.compare_digest(token, credential):
                return role
        raise Denied("UNAUTHENTICATED", 401)

    def event(self, db: sqlite3.Connection, kind: str, actor: str, payload: Json) -> None:
        """Append signed evidence with the domain transaction."""
        append(db, self.keys, kind, actor, payload, self.clock())

    def valid_root(self, record: Json) -> Json:
        """Validate a signed root and current expiry/revocation state."""
        grant = verify(cast(Json, record["envelope"]), self.keys.public, "authorization")
        if record["revoked"]:
            raise Denied("REVOKED")
        if self.clock() >= cast(float, grant["expires_at"]):
            raise Denied("EXPIRED")
        return grant

    def approve(self, proposal: RootProposal) -> Json:
        """Create exactly one signed root for an explicit owner confirmation ID."""
        if proposal.document_id not in DOCUMENTS or proposal.recipient_id != "Anna":
            raise Denied("INVALID_INPUT", 422)
        with self.store.connection() as db:
            previous = self.store.get(db, "request", proposal.request_id)
            if previous:
                if previous["digest"] != digest(proposal.model_dump()):
                    raise Denied("IDEMPOTENCY_CONFLICT", 409)
                record = self.store.get(db, "root", cast(str, previous["grant_id"]))
                assert record is not None
                return cast(Json, cast(Json, record["envelope"])["payload"])
            now = self.clock()
            grant: Json = {
                "grant_id": str(uuid4()),
                "case_id": "synthetic-case",
                "owner_id": "owner",
                "orchestrator_id": "A",
                "action": "deliver_document",
                "snapshot_hash": DOCUMENTS[proposal.document_id]["snapshot_hash"],
                "document_id": proposal.document_id,
                "recipient_id": proposal.recipient_id,
                "audience": "synthetic-inbox",
                "issued_at": now,
                "expires_at": now + proposal.minutes * 60,
                "max_uses": 1,
                "delegation_allowed": proposal.delegation_allowed,
            }
            signed = self.keys.signed("authorization", grant)
            self.store.put(
                db,
                "root",
                cast(str, grant["grant_id"]),
                {"envelope": signed, "revoked": False, "reserved_by": None},
            )
            self.store.put(
                db,
                "request",
                proposal.request_id,
                {"digest": digest(proposal.model_dump()), "grant_id": cast(str, grant["grant_id"])},
            )
            self.event(db, "ROOT_GRANT_ISSUED", "owner", signed)
            return grant

    def delegate(self, actor: str, proposal: ChildProposal) -> Json:
        """Only A may issue a capability whose scope is no broader than its root."""
        failure: Denied | None = None
        result: Json = {}
        with self.store.connection() as db:
            try:
                if actor != "A":
                    raise Denied("REDELEGATION_DENIED")
                record = self.store.get(db, "root", proposal.root_id)
                if record is None:
                    raise Denied("INVALID_INPUT", 404)
                grant = self.valid_root(record)
                if not grant["delegation_allowed"]:
                    raise Denied("REDELEGATION_DENIED")
                if (
                    proposal.executor_id not in ("B", "C")
                    or proposal.delegation_allowed
                    or any(
                        (
                            getattr(proposal, field) != grant[field]
                            for field in ("recipient_id", "snapshot_hash", "action", "audience")
                        )
                    )
                    or (proposal.expires_at > cast(float, grant["expires_at"]))
                    or (proposal.expires_at <= self.clock())
                ):
                    raise Denied("SCOPE_ESCALATION")
                result = {
                    **proposal.model_dump(exclude={"root_id"}),
                    "grant_id": str(uuid4()),
                    "parent_id": proposal.root_id,
                    "case_id": cast(str, grant["case_id"]),
                    "authenticated_issuer": actor,
                    "issued_at": self.clock(),
                    "max_uses": 1,
                }
                signed = self.keys.signed("A", result)
                self.store.put(db, "child", cast(str, result["grant_id"]), signed)
                self.event(db, "CHILD_GRANT_DELEGATED", actor, signed)
            except Denied as error:
                failure = error
                self.event(
                    db,
                    "DELEGATION_BLOCKED",
                    actor,
                    {"reason": error.reason, "root_id": proposal.root_id},
                )
        if failure:
            raise failure
        return result

    def revoke(self, root_id: str) -> Json:
        """Serialize revocation against reservations; already-sent work stays tracked."""
        with self.store.connection() as db:
            record = self.store.get(db, "root", root_id)
            if record is None:
                raise Denied("INVALID_INPUT", 404)
            record["revoked"] = True
            self.store.put(db, "root", root_id, record)
            self.event(
                db,
                "ROOT_REVOKED",
                "owner",
                {"root_id": root_id, "reserved_by": record["reserved_by"]},
            )
            return {"revoked": True, "dispatch_may_have_started": record["reserved_by"] is not None}

    def reserve(self, actor: str, proposal: ExecutionProposal) -> tuple[Json, bool]:
        """Atomically validate all grants, persist evidence, and reserve the shared slot."""
        failure: Denied | None = None
        result: Json = {}
        with self.store.connection() as db:
            existing = self.store.get(db, "attempt", proposal.attempt_id)
            if existing:
                if cast(str, existing["authenticated_actor"]) != actor or cast(
                    str, existing["request_digest"]
                ) != digest(proposal.model_dump()):
                    raise Denied("IDEMPOTENCY_CONFLICT", 409)
                if existing["execution_status"] == "blocked":
                    raise Denied(cast(str, existing["reason"]), cast(int, existing["http_status"]))
                return (existing, False)
            try:
                signed_child = self.store.get(db, "child", proposal.child_id)
                if signed_child is None:
                    raise Denied("INVALID_INPUT", 404)
                child = verify(signed_child, self.keys.public, "A")
                record = self.store.get(db, "root", cast(str, child["parent_id"]))
                if record is None:
                    raise Denied("INVALID_SIGNATURE")
                root = verify(cast(Json, record["envelope"]), self.keys.public, "authorization")
                if (
                    cast(str, child["case_id"]) != cast(str, root["case_id"])
                    or cast(str, child["authenticated_issuer"]) != "A"
                    or child["delegation_allowed"]
                    or (cast(int, child["max_uses"]) != 1)
                    or (cast(float, child["expires_at"]) > cast(float, root["expires_at"]))
                    or any(
                        (
                            child[field] != root[field]
                            for field in ("action", "snapshot_hash", "recipient_id", "audience")
                        )
                    )
                ):
                    raise Denied("INVALID_SIGNATURE")
                if actor != cast(str, child["executor_id"]):
                    raise Denied("WRONG_ACTOR")
                document = DOCUMENTS.get(proposal.document_id)
                if document is None or document["snapshot_hash"] != cast(
                    str, child["snapshot_hash"]
                ):
                    raise Denied("DOCUMENT_CHANGED")
                if proposal.recipient_id != cast(str, child["recipient_id"]):
                    raise Denied("SCOPE_ESCALATION")
                self.valid_root(record)
                if self.clock() >= cast(float, child["expires_at"]):
                    raise Denied("EXPIRED")
                if record["reserved_by"] is not None:
                    raise Denied("LIMIT_RESERVED_OR_USED", 409)
                result = {
                    "attempt_id": proposal.attempt_id,
                    "case_id": cast(str, root["case_id"]),
                    "root_id": cast(str, root["grant_id"]),
                    "child_id": cast(str, child["grant_id"]),
                    "authenticated_actor": actor,
                    "request_digest": digest(proposal.model_dump()),
                    "actual_action_digest": digest(
                        {
                            "action": cast(str, child["action"]),
                            "snapshot_hash": cast(str, child["snapshot_hash"]),
                            "recipient_id": proposal.recipient_id,
                        }
                    ),
                    "idempotency_key": str(uuid4()),
                    "decision": "allowed",
                    "reason": "AUTHORIZED",
                    "execution_status": "reserved",
                    "document_id": proposal.document_id,
                    "snapshot_hash": cast(str, child["snapshot_hash"]),
                    "recipient_id": proposal.recipient_id,
                }
                record["reserved_by"] = proposal.attempt_id
                self.store.put(db, "root", cast(str, root["grant_id"]), record)
                self.store.put(db, "attempt", proposal.attempt_id, result)
                self.event(db, "ATTEMPT_RESERVED", actor, result)
            except (Denied, ValueError) as error:
                failure = error if isinstance(error, Denied) else Denied(str(error))
                result = {
                    "attempt_id": proposal.attempt_id,
                    "child_id": proposal.child_id,
                    "authenticated_actor": actor,
                    "request_digest": digest(proposal.model_dump()),
                    "decision": "blocked",
                    "reason": failure.reason,
                    "http_status": failure.status,
                    "execution_status": "blocked",
                }
                self.store.put(db, "attempt", proposal.attempt_id, result)
                self.event(db, "ATTEMPT_BLOCKED", actor, result)
        if failure:
            raise failure
        return (result, True)

    def confirm(self, attempt: Json, receipt: Json) -> Json:
        """Confirm only a trusted receipt bound to the exact attempted action."""
        self.receiver_key()
        payload = verify(receipt, self.keys.public, "receiver")
        for field in (
            "attempt_id",
            "root_id",
            "child_id",
            "case_id",
            "snapshot_hash",
            "recipient_id",
            "idempotency_key",
        ):
            if payload[field] != attempt[field]:
                raise ValueError("INVALID_RECEIPT")
        if cast(str, payload["receiver_id"]) != "synthetic-inbox":
            raise ValueError("WRONG_AUDIENCE")
        if self.testing and self.fail_result_write:
            raise sqlite3.OperationalError("injected result write failure")
        with self.store.connection() as db:
            current = self.store.get(db, "attempt", cast(str, attempt["attempt_id"]))
            assert current is not None
            if current["execution_status"] == "confirmed":
                return current
            current.update(execution_status="confirmed", receipt=receipt)
            self.store.put(db, "attempt", cast(str, current["attempt_id"]), current)
            self.event(db, "DISPATCH_CONFIRMED", cast(str, current["authenticated_actor"]), current)
            return current

    def execute(self, actor: str, proposal: ExecutionProposal) -> Json:
        """Reserve before network I/O; preserve uncertainty on every post-reserve failure."""
        attempt, fresh = self.reserve(actor, proposal)
        if not fresh:
            return attempt
        try:
            payload = {
                field: attempt[field]
                for field in (
                    "attempt_id",
                    "case_id",
                    "root_id",
                    "child_id",
                    "authenticated_actor",
                    "idempotency_key",
                    "snapshot_hash",
                    "recipient_id",
                )
            }
            payload.update(action="deliver_document", audience="synthetic-inbox")
            signed_action = self.keys.signed(actor, payload)
            attempt["signed_action"] = signed_action
            with self.store.connection() as db:
                attempt["execution_status"] = "dispatching"
                self.store.put(db, "attempt", cast(str, attempt["attempt_id"]), attempt)
                self.event(db, "DISPATCH_STARTED", actor, attempt)
            receipt = self.receiver.receive(
                {**signed_action, "document": DOCUMENTS[proposal.document_id]["bytes"]}
            )
            return self.confirm(attempt, receipt)
        except (httpx.HTTPError, OSError, ValueError, KeyError, sqlite3.Error):
            attempt["execution_status"] = "uncertain"
            try:
                with self.store.connection() as db:
                    self.store.put(db, "attempt", cast(str, attempt["attempt_id"]), attempt)
                    self.event(db, "DISPATCH_UNCERTAIN", actor, attempt)
            except sqlite3.Error:
                pass
            return attempt

    def reconcile(self, attempt_id: str) -> Json:
        """Read-only receiver lookup; absent evidence never releases a budget."""
        with self.store.connection() as db:
            attempt = self.store.get(db, "attempt", attempt_id)
        if attempt is None or attempt["execution_status"] not in ("uncertain", "confirmed"):
            raise Denied("INVALID_INPUT", 409)
        if attempt["execution_status"] == "confirmed":
            return attempt
        try:
            receipt = self.receiver.lookup(cast(str, attempt["idempotency_key"]))
            if receipt:
                return self.confirm(attempt, receipt)
        except (httpx.HTTPError, OSError, ValueError, KeyError, sqlite3.Error):
            pass
        return attempt

    def state(self) -> Json:
        """Project persisted case state for the owner, including actual receiver records."""
        with self.store.connection() as db:
            state = {
                "documents": DOCUMENTS,
                "roots": self.store.all(db, "root"),
                "children": self.store.all(db, "child"),
                "attempts": self.store.all(db, "attempt"),
                "events": self.store.events(db),
                "now": self.clock(),
            }
        try:
            state["inbox"] = self.receiver.inbox()
            state["receiver_available"] = True
        except (httpx.HTTPError, OSError):
            state["inbox"] = []
            state["receiver_available"] = False
        return state
