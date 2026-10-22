"""Signed evidence bundles and offline verification against independent trust pins."""

import io
import json
import zipfile
from typing import cast

from core.canonical import Json, bytes_hash, canonical, digest
from core.crypto import fingerprint, verify
from services.authorization import DOCUMENTS, Runtime
from services.ledger import chain_hash

MEMBERS = {
    "snapshot.json",
    "grants.json",
    "events.jsonl",
    "receipt.json",
    "attempts.json",
    "public.json",
}
MAX_PACK = 10 * 1024 * 1024


def export_pack(runtime: Runtime) -> bytes:
    """Take an atomic local snapshot and bind every member to a signed checkpoint."""
    runtime.receiver_key()
    with runtime.store.connection() as db:
        roots = runtime.store.all(db, "root")
        children = runtime.store.all(db, "child")
        attempts = runtime.store.all(db, "attempt")
        events = runtime.store.events(db)
    files = {
        "snapshot.json": canonical(DOCUMENTS),
        "grants.json": canonical({"roots": roots, "children": children}),
        "events.jsonl": b"\n".join((canonical(event) for event in events)),
        "receipt.json": canonical([cast(Json, a["receipt"]) for a in attempts if "receipt" in a]),
        "attempts.json": canonical(attempts),
        "public.json": canonical(runtime.keys.public),
    }
    manifest = {
        "schema_version": "1",
        "case_id": "synthetic-case",
        "files": {name: bytes_hash(data) for name, data in files.items()},
        "event_count": len(events),
        "final_hash": cast(str, cast(Json, events[-1]["payload"])["current_hash"])
        if events
        else "0" * 64,
    }
    files["manifest.json"] = canonical(runtime.keys.signed("authorization", manifest))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def verify_pack(pack: bytes, trusted_fingerprints: dict[str, str]) -> Json:
    """Reject missing trust, unexpected members, signature/hash/chain/linkage tampering."""
    try:
        return _verify(pack, trusted_fingerprints)
    except (KeyError, TypeError, UnicodeError, zipfile.BadZipFile, OverflowError) as error:
        raise ValueError("INVALID_EVIDENCE") from error


def _verify(pack: bytes, trust: dict[str, str]) -> Json:
    if len(pack) > MAX_PACK:
        raise ValueError("PACK_TOO_LARGE")
    with zipfile.ZipFile(io.BytesIO(pack)) as archive:
        if set(archive.namelist()) != MEMBERS | {"manifest.json"} or len(archive.namelist()) != 7:
            raise ValueError("INVALID_MANIFEST")
        if sum((member.file_size for member in archive.infolist())) > MAX_PACK:
            raise ValueError("PACK_TOO_LARGE")
        files = {name: archive.read(name) for name in archive.namelist()}
    public = json.loads(files["public.json"])
    for role in ("authorization", "A", "B", "C", "ledger", "receiver"):
        if role not in trust or role not in public or fingerprint(public[role]) != trust[role]:
            raise ValueError("UNKNOWN_KEY")
    manifest = verify(json.loads(files["manifest.json"]), public, "authorization")
    if (
        manifest["schema_version"] != "1"
        or cast(str, manifest["case_id"]) != "synthetic-case"
        or set(cast(dict[str, str], manifest["files"])) != MEMBERS
    ):
        raise ValueError("INVALID_MANIFEST")
    for name, expected in cast(dict[str, str], manifest["files"]).items():
        if bytes_hash(files[name]) != expected:
            raise ValueError("INVALID_MANIFEST_HASH")
    events = [json.loads(line) for line in files["events.jsonl"].splitlines()]
    previous = "0" * 64
    signed_roots: dict[str, Json] = {}
    signed_children: dict[str, Json] = {}
    confirmed: dict[str, Json] = {}
    reserved_roots: set[str] = set()
    for sequence, signed_event in enumerate(events, 1):
        event = verify(signed_event, public, "ledger")
        if (
            cast(int, event["sequence"]) != sequence
            or cast(str, event["previous_hash"]) != previous
            or cast(str, event["case_id"]) != cast(str, manifest["case_id"])
            or (cast(str, event["payload_digest"]) != digest(cast(Json, event["payload"])))
            or (
                cast(str, event["current_hash"])
                != chain_hash(previous, cast(str, event["payload_digest"]), sequence)
            )
        ):
            raise ValueError("INVALID_CHAIN")
        previous = cast(str, event["current_hash"])
        payload = cast(Json, event["payload"])
        if cast(str, event["kind"]) == "ROOT_GRANT_ISSUED":
            root = verify(payload, public, "authorization")
            signed_roots[cast(str, root["grant_id"])] = payload
        elif cast(str, event["kind"]) == "CHILD_GRANT_DELEGATED":
            child = verify(payload, public, "A")
            signed_children[cast(str, child["grant_id"])] = payload
        elif cast(str, event["kind"]) == "ATTEMPT_RESERVED":
            if cast(str, payload["root_id"]) in reserved_roots:
                raise ValueError("ROOT_BUDGET_EXCEEDED")
            reserved_roots.add(cast(str, payload["root_id"]))
        elif cast(str, event["kind"]) == "DISPATCH_CONFIRMED":
            confirmed[cast(str, payload["attempt_id"])] = cast(Json, payload["receipt"])
    if (
        cast(int, manifest["event_count"]) != len(events)
        or cast(str, manifest["final_hash"]) != previous
    ):
        raise ValueError("INVALID_CHECKPOINT")
    snapshots = json.loads(files["snapshot.json"])
    for snapshot in snapshots.values():
        if bytes_hash(cast(str, snapshot["bytes"]).encode()) != cast(
            str, snapshot["snapshot_hash"]
        ):
            raise ValueError("DOCUMENT_CHANGED")
    grants = json.loads(files["grants.json"])
    roots: dict[str, Json] = {}
    children: dict[str, Json] = {}
    for record in cast(list[Json], grants["roots"]):
        root = verify(cast(Json, record["envelope"]), public, "authorization")
        if (
            signed_roots.get(cast(str, root["grant_id"])) != cast(Json, record["envelope"])
            or cast(str, root["snapshot_hash"])
            != cast(str, snapshots[cast(str, root["document_id"])]["snapshot_hash"])
            or cast(str, root["case_id"]) != cast(str, manifest["case_id"])
        ):
            raise ValueError("INVALID_ROOT_LINK")
        roots[cast(str, root["grant_id"])] = root
    for signed in cast(list[Json], grants["children"]):
        child = verify(signed, public, "A")
        root = roots[cast(str, child["parent_id"])]
        if (
            signed_children.get(cast(str, child["grant_id"])) != signed
            or cast(str, child["case_id"]) != cast(str, root["case_id"])
            or child["delegation_allowed"]
            or (cast(float, child["expires_at"]) > cast(float, root["expires_at"]))
            or (cast(str, child["executor_id"]) not in ("B", "C"))
            or any(
                (
                    child[key] != root[key]
                    for key in ("snapshot_hash", "recipient_id", "action", "audience")
                )
            )
        ):
            raise ValueError("INVALID_CHILD_LINK")
        children[cast(str, child["grant_id"])] = child
    if set(roots) != set(signed_roots) or set(children) != set(signed_children):
        raise ValueError("MISSING_GRANT")
    receipts = json.loads(files["receipt.json"])
    attempts = {
        cast(str, attempt["attempt_id"]): attempt for attempt in json.loads(files["attempts.json"])
    }
    seen: set[str] = set()
    for signed_receipt in receipts:
        receipt = verify(signed_receipt, public, "receiver")
        attempt = attempts[cast(str, receipt["attempt_id"])]
        child = children[cast(str, receipt["child_id"])]
        action = verify(
            cast(Json, attempt["signed_action"]), public, cast(str, child["executor_id"])
        )
        if (
            cast(str, action["authenticated_actor"]) != cast(str, child["executor_id"])
            or cast(str, action["action"]) != "deliver_document"
            or cast(str, action["audience"]) != "synthetic-inbox"
            or any(
                (
                    action[key] != attempt[key]
                    for key in (
                        "attempt_id",
                        "case_id",
                        "root_id",
                        "child_id",
                        "snapshot_hash",
                        "recipient_id",
                        "idempotency_key",
                    )
                )
            )
        ):
            raise ValueError("INVALID_EXECUTOR_SIGNATURE_LINK")
        if (
            cast(str, receipt["attempt_id"]) in seen
            or confirmed.get(cast(str, receipt["attempt_id"])) != signed_receipt
            or attempt["execution_status"] != "confirmed"
            or (cast(str, receipt["receiver_id"]) != "synthetic-inbox")
            or (cast(str, child["parent_id"]) != cast(str, receipt["root_id"]))
            or (cast(str, child["snapshot_hash"]) != cast(str, receipt["snapshot_hash"]))
            or (cast(str, child["recipient_id"]) != cast(str, receipt["recipient_id"]))
            or any(
                (
                    attempt[key] != receipt[key]
                    for key in (
                        "attempt_id",
                        "case_id",
                        "root_id",
                        "child_id",
                        "snapshot_hash",
                        "recipient_id",
                        "idempotency_key",
                    )
                )
            )
        ):
            raise ValueError("INVALID_RECEIPT_LINK")
        seen.add(cast(str, receipt["attempt_id"]))
    if seen != set(confirmed):
        raise ValueError("MISSING_RECEIPT")
    return {
        "valid": True,
        "events": len(events),
        "receipts": len(receipts),
        "final_hash": previous,
        "meaning": "Integrity relative to supplied trust pins; no legal signature or independent history completeness.",
    }
