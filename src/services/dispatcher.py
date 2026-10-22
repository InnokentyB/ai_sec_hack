"""Dispatch and receipt reconciliation after atomic authorization."""

import logging
import sqlite3
from typing import TYPE_CHECKING, cast

import httpx

from core.canonical import Json
from core.crypto import verify
from core.models import ExecutionProposal
from services.policy import DOCUMENTS, Denied

if TYPE_CHECKING:
    from services.authorization import Runtime

logger = logging.getLogger(__name__)


def confirm(runtime: "Runtime", attempt: Json, receipt: Json) -> Json:
    """Confirm only a trusted receipt bound to the exact attempted action."""
    runtime.receiver_key()
    payload = verify(receipt, runtime.keys.public, "receiver")
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
    if runtime.testing and runtime.fail_result_write:
        raise sqlite3.OperationalError("injected result write failure")
    with runtime.store.connection() as db:
        current = runtime.store.get(db, "attempt", cast(str, attempt["attempt_id"]))
        assert current is not None
        if current["execution_status"] == "confirmed":
            return current
        current.update(execution_status="confirmed", receipt=receipt)
        runtime.store.put(db, "attempt", cast(str, current["attempt_id"]), current)
        runtime.event(db, "DISPATCH_CONFIRMED", cast(str, current["authenticated_actor"]), current)
        return current


def execute(runtime: "Runtime", actor: str, proposal: ExecutionProposal) -> Json:
    """Reserve before network I/O; preserve uncertainty on every post-reserve failure."""
    attempt, fresh = runtime.reserve(actor, proposal)
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
        signed_action = runtime.keys.signed(actor, payload)
        attempt["signed_action"] = signed_action
        with runtime.store.connection() as db:
            attempt["execution_status"] = "dispatching"
            runtime.store.put(db, "attempt", cast(str, attempt["attempt_id"]), attempt)
            runtime.event(db, "DISPATCH_STARTED", actor, attempt)
        receipt = runtime.receiver.receive(
            {**signed_action, "document": DOCUMENTS[proposal.document_id]["bytes"]}
        )
        return confirm(runtime, attempt, receipt)
    except (httpx.HTTPError, OSError, ValueError, KeyError, sqlite3.Error):
        attempt["execution_status"] = "uncertain"
        try:
            with runtime.store.connection() as db:
                runtime.store.put(db, "attempt", cast(str, attempt["attempt_id"]), attempt)
                runtime.event(db, "DISPATCH_UNCERTAIN", actor, attempt)
        except sqlite3.Error:
            logger.exception("Unable to persist uncertain dispatch; startup recovery required")
        return attempt


def reconcile(runtime: "Runtime", attempt_id: str) -> Json:
    """Read-only receiver lookup; absent evidence never releases a budget."""
    with runtime.store.connection() as db:
        attempt = runtime.store.get(db, "attempt", attempt_id)
    if attempt is None or attempt["execution_status"] not in ("uncertain", "confirmed"):
        raise Denied("INVALID_INPUT", 409)
    if attempt["execution_status"] == "confirmed":
        return attempt
    try:
        receipt = runtime.receiver.lookup(cast(str, attempt["idempotency_key"]))
        if receipt:
            return confirm(runtime, attempt, receipt)
    except (httpx.HTTPError, OSError, ValueError, KeyError, sqlite3.Error):
        logger.exception("Receipt reconciliation failed; reservation remains uncertain")
    return attempt
