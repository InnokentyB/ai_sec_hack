"""Signed, linked evidence events committed with their domain mutation."""

import json
import sqlite3
from typing import cast
from uuid import uuid4

from core.canonical import Json, bytes_hash, digest
from core.crypto import Keys
from services.storage import Store


def chain_hash(previous: str, payload_digest: str, sequence: int) -> str:
    """Hash the previous checkpoint, payload digest and unambiguous sequence."""
    return bytes_hash(f"{previous}{payload_digest}{sequence}".encode())


def append(
    db: sqlite3.Connection, keys: Keys, kind: str, actor: str, payload: Json, now: float
) -> None:
    """Append one signed event atomically with authorization or execution state."""
    events = Store.events(db)
    sequence = len(events) + 1
    previous = cast(str, cast(Json, events[-1]["payload"])["current_hash"]) if events else "0" * 64
    payload_digest = digest(payload)
    body = {
        "event_id": str(uuid4()),
        "case_id": "synthetic-case",
        "sequence": sequence,
        "previous_hash": previous,
        "kind": kind,
        "actor_id": actor,
        "server_time": now,
        "payload": payload,
        "payload_digest": payload_digest,
        "current_hash": chain_hash(previous, payload_digest, sequence),
    }
    db.execute(
        "INSERT INTO events VALUES(?,?)", (sequence, json.dumps(keys.signed("ledger", body)))
    )
