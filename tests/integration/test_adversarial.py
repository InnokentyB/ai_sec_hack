"""Boundary, recovery and tamper scenarios beyond the happy path."""

import io
import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from core.canonical import canonical
from services.exporter import verify_pack
from test_contract import actor, child, execute, owner, root


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    """Create a synthetic case without live providers."""
    return TestClient(create_app(data_dir=tmp_path, testing=True))


def test_s03_cancel_creates_nothing(client: TestClient) -> None:
    """Rendering and abandoning a form cannot authorize an action."""
    assert client.get("/", headers=owner(client)).status_code == 200
    assert client.get("/api/state", headers=owner(client)).json()["events"] == []


@pytest.mark.parametrize("minutes", [0, 11, "5", None])
def test_s04_s30_invalid_expiry(client: TestClient, minutes: object) -> None:
    """Expiry bounds reject coercion and out-of-range values."""
    response = client.post(
        "/api/roots",
        headers=owner(client),
        json={
            "request_id": "x",
            "document_id": "doc-v1",
            "recipient_id": "Anna",
            "minutes": minutes,
            "delegation_allowed": True,
        },
    )
    assert response.status_code == 422


def test_s08_redelegation(client: TestClient) -> None:
    """Executors cannot issue children even when they know root IDs."""
    grant = root(client)
    delegation = child(client, grant)
    payload = {
        "root_id": grant["grant_id"],
        "executor_id": "C",
        "recipient_id": "Anna",
        "snapshot_hash": grant["snapshot_hash"],
        "action": "deliver_document",
        "audience": "synthetic-inbox",
        "expires_at": grant["expires_at"],
    }
    response = client.post("/api/children", headers=actor(client, "B"), json=payload)
    assert response.json()["reason"] == "REDELEGATION_DENIED"
    assert delegation["delegation_allowed"] is False


@pytest.mark.parametrize("offset,allowed", [(-0.001, True), (0, False)])
def test_s11_exact_expiry(client: TestClient, offset: float, allowed: bool) -> None:
    """Server-time expiry is exclusive at the exact boundary."""
    grant = root(client)
    delegation = child(client, grant)
    client.app.state.runtime.clock = lambda: grant["expires_at"] + offset
    response = execute(client, delegation)
    assert (response.status_code == 200) is allowed
    if not allowed:
        assert response.json()["reason"] == "EXPIRED"


def test_s16_receiver_idempotency(client: TestClient) -> None:
    """Receiver exact replay returns the original receipt; changed payload conflicts."""
    rt = client.app.state.runtime
    delegation = child(client, root(client))
    captured: list[dict] = []
    original = rt.receiver.receive

    def capture(envelope: dict) -> dict:
        captured.append(envelope)
        return original(envelope)

    with patch.object(rt.receiver, "receive", capture):
        first = execute(client, delegation).json()["receipt"]
    assert original(captured[0]) == first
    payload = captured[0]["payload"].copy()
    payload["attempt_id"] = "different"
    with pytest.raises(ValueError, match="CONFLICT"):
        original({**rt.keys.signed("B", payload), "document": captured[0]["document"]})
    assert len(rt.receiver.inbox()) == 1


def test_s19_missing_receipt_does_not_free_budget(client: TestClient) -> None:
    """No receipt is absence of evidence, never permission to resend."""
    rt = client.app.state.runtime
    delegation = child(client, root(client))
    rt.receiver.unavailable = True
    assert execute(client, delegation).json()["execution_status"] == "uncertain"
    assert (
        client.post("/api/attempts/attempt-1/reconcile", headers=owner(client)).json()[
            "execution_status"
        ]
        == "uncertain"
    )
    assert execute(client, delegation, "new").status_code == 409


@pytest.mark.parametrize("revoke_first", [True, False])
def test_s20_serialized_revoke(client: TestClient, revoke_first: bool) -> None:
    """Both serialization orders preserve the revoke/reserve contract."""
    from core.models import ExecutionProposal

    rt = client.app.state.runtime
    grant = root(client)
    delegation = child(client, grant)
    if revoke_first:
        rt.revoke(grant["grant_id"])
        assert execute(client, delegation).json()["reason"] == "REVOKED"
    else:
        attempt, fresh = rt.reserve(
            "B",
            ExecutionProposal(
                child_id=delegation["grant_id"],
                attempt_id="reserved",
                document_id="doc-v1",
                recipient_id="Anna",
            ),
        )
        assert fresh and attempt["execution_status"] == "reserved"
        assert rt.revoke(grant["grant_id"])["dispatch_may_have_started"] is True


def test_s21_unavailable_pre_dispatch(client: TestClient) -> None:
    """A failed authorization write must prevent receiver calls."""
    rt = client.app.state.runtime
    delegation = child(client, root(client))
    with (
        patch.object(rt.store, "connection", side_effect=sqlite3.OperationalError("injected")),
        patch.object(rt.receiver, "receive") as send,
    ):
        response = execute(client, delegation)
    assert response.status_code == 503
    send.assert_not_called()


def test_s22_result_write_failure_restart(client: TestClient) -> None:
    """Receipt persistence failure remains uncertain and recovers without redelivery."""
    rt = client.app.state.runtime
    delegation = child(client, root(client))
    rt.fail_result_write = True
    assert execute(client, delegation).json()["execution_status"] == "uncertain"
    restarted = TestClient(create_app(data_dir=rt.directory, testing=True))
    assert (
        restarted.post("/api/attempts/attempt-1/reconcile", headers=owner(restarted)).json()[
            "execution_status"
        ]
        == "confirmed"
    )
    assert len(restarted.app.state.runtime.receiver.inbox()) == 1


def test_s22_recover_reserved_on_restart(client: TestClient) -> None:
    """A crash after reserve recovers as uncertain and never makes a new slot."""
    from core.models import ExecutionProposal

    rt = client.app.state.runtime
    delegation = child(client, root(client))
    rt.reserve(
        "B",
        ExecutionProposal(
            child_id=delegation["grant_id"],
            attempt_id="crashed",
            document_id="doc-v1",
            recipient_id="Anna",
        ),
    )
    restarted = TestClient(create_app(data_dir=rt.directory, testing=True))
    assert (
        restarted.get("/api/state", headers=owner(restarted)).json()["attempts"][0][
            "execution_status"
        ]
        == "uncertain"
    )
    assert execute(restarted, delegation, "new").status_code == 409


@pytest.mark.parametrize("kind", ["root", "child"])
def test_s26_corrupt_runtime_signature(client: TestClient, kind: str) -> None:
    """Runtime mutations of stored grants fail before receiver invocation."""
    rt = client.app.state.runtime
    grant = root(client)
    delegation = child(client, grant)
    identifier = grant["grant_id"] if kind == "root" else delegation["grant_id"]
    with rt.store.connection() as db:
        record = rt.store.get(db, kind, identifier)
        envelope = record["envelope"] if kind == "root" else record
        envelope["payload"]["recipient_id"] = "Mallory"
        rt.store.put(db, kind, identifier, record)
    assert execute(client, delegation).json()["reason"] == "INVALID_SIGNATURE"
    assert rt.receiver.inbox() == []


def test_s26_fake_receipt(client: TestClient) -> None:
    """HTTP success with an invalid receipt never becomes confirmed."""
    rt = client.app.state.runtime
    delegation = child(client, root(client))
    with patch.object(
        rt.receiver,
        "receive",
        return_value={"key_id": "receiver", "payload": {}, "signature": "bad"},
    ):
        result = execute(client, delegation)
    assert result.json()["execution_status"] == "uncertain"


def test_s27_cookie_csrf(client: TestClient) -> None:
    """A stolen cross-site form cannot use the owner's ambient session."""
    token = client.app.state.runtime.credentials["owner"]
    client.cookies.set("ledger_session", token)
    response = client.post("/api/roots", json={})
    assert response.status_code == 403
    assert response.json()["reason"] == "CSRF_REJECTED"
    assert (
        client.post(
            "/login", data={"token": token}, headers={"Origin": "https://hostile.invalid"}
        ).status_code
        == 403
    )


def test_s29_no_credentials_in_evidence(client: TestClient) -> None:
    """Exports contain the allowed snapshot, but never credentials or private keys."""
    rt = client.app.state.runtime
    execute(client, child(client, root(client)))
    pack = client.get("/api/export", headers=owner(client)).content
    with zipfile.ZipFile(io.BytesIO(pack)) as archive:
        content = b"\n".join(archive.read(name) for name in archive.namelist())
    for token in rt.credentials.values():
        assert token.encode() not in content
    assert b"PRIVATE KEY" not in content
    assert b"Synthetic delegation document" in content
    events = client.get("/api/state", headers=owner(client)).json()["events"]
    assert "Synthetic delegation document" not in json.dumps(events)


@pytest.mark.parametrize("member", ["snapshot.json", "events.jsonl", "receipt.json", "grants.json"])
def test_s24_modified_member(client: TestClient, member: str) -> None:
    """Any removed event, changed document, grant or receipt breaks the manifest."""
    rt = client.app.state.runtime
    execute(client, child(client, root(client)))
    pack = client.get("/api/export", headers=owner(client)).content
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(pack)) as source, zipfile.ZipFile(output, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            if name == member:
                data = (
                    b"\n".join(data.splitlines()[:-1])
                    if name == "events.jsonl"
                    else canonical({"altered": True})
                )
            target.writestr(name, data)
    with pytest.raises(ValueError):
        verify_pack(output.getvalue(), rt.keys.trust())
