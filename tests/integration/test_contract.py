"""Executable acceptance contract for the synthetic delegation lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    """Create a fresh, isolated case with separate receiver storage."""
    return TestClient(create_app(data_dir=tmp_path, testing=True))


def owner(client: TestClient) -> dict[str, str]:
    """Authenticate using fixture-provisioned owner credentials."""
    return {"Authorization": "Bearer " + client.app.state.runtime.credentials["owner"]}


def actor(client: TestClient, role: str) -> dict[str, str]:
    """Return role-specific credentials without allowing actor overrides."""
    return {"Authorization": "Bearer " + client.app.state.runtime.credentials[role]}


def root(client: TestClient, request_id: str = "root-1") -> dict:
    """Approve an immutable synthetic document."""
    response = client.post(
        "/api/roots",
        headers=owner(client),
        json={
            "request_id": request_id,
            "document_id": "doc-v1",
            "recipient_id": "Anna",
            "minutes": 5,
            "delegation_allowed": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def child(client: TestClient, grant: dict, executor: str = "B", **changes: object) -> dict:
    """Ask the authenticated orchestrator to delegate a narrower grant."""
    payload = {
        "root_id": grant["grant_id"],
        "executor_id": executor,
        "recipient_id": "Anna",
        "snapshot_hash": grant["snapshot_hash"],
        "action": "deliver_document",
        "audience": "synthetic-inbox",
        "expires_at": grant["expires_at"],
        "delegation_allowed": False,
    }
    payload.update(changes)
    response = client.post("/api/children", headers=actor(client, "A"), json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def execute(
    client: TestClient,
    delegation: dict,
    attempt: str = "attempt-1",
    role: str = "B",
    **changes: object,
):
    """Execute the exact delegated action."""
    payload = {
        "child_id": delegation["grant_id"],
        "attempt_id": attempt,
        "document_id": "doc-v1",
        "recipient_id": "Anna",
    }
    payload.update(changes)
    return client.post("/api/execute", headers=actor(client, role), json=payload)


def test_s01_s02_s05_s14_s28(client: TestClient) -> None:
    """Empty, approval, delegation, receipt, replay and restart remain durable."""
    assert client.get("/api/state", headers=owner(client)).json()["roots"] == []
    grant = root(client)
    delegation = child(client, grant)
    result = execute(client, delegation)
    assert result.status_code == 200, result.text
    assert result.json()["execution_status"] == "confirmed"
    assert execute(client, delegation).json() == result.json()
    assert execute(client, delegation, "another").status_code == 409
    restarted = TestClient(create_app(data_dir=client.app.state.runtime.directory, testing=True))
    state = restarted.get("/api/state", headers=owner(restarted)).json()
    assert len(state["inbox"]) == 1
    assert state["attempts"][0]["execution_status"] == "confirmed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("recipient_id", "Mallory"),
        ("action", "pay"),
        ("snapshot_hash", "bad"),
        ("audience", "elsewhere"),
        ("expires_at", 9999999999.0),
        ("delegation_allowed", True),
    ],
)
def test_s06_s07_scope(client: TestClient, field: str, value: object) -> None:
    """Delegation cannot broaden any approved dimension."""
    grant = root(client)
    with pytest.raises(AssertionError, match="SCOPE_ESCALATION"):
        child(client, grant, **{field: value})
    assert client.get("/api/state", headers=owner(client)).json()["children"] == []


def test_s09_s10_s12(client: TestClient) -> None:
    """Wrong executor, changed document and revoked root cannot dispatch."""
    grant = root(client)
    delegation = child(client, grant)
    assert execute(client, delegation, role="C").json()["reason"] == "WRONG_ACTOR"
    assert (
        execute(client, delegation, "changed", document_id="doc-v2").json()["reason"]
        == "DOCUMENT_CHANGED"
    )
    assert (
        client.post(f"/api/roots/{grant['grant_id']}/revoke", headers=owner(client)).status_code
        == 200
    )
    assert execute(client, delegation, "revoked").json()["reason"] == "REVOKED"
    assert client.get("/api/state", headers=owner(client)).json()["inbox"] == []


def test_s13_idempotent_approval(client: TestClient) -> None:
    """The same owner confirmation creates one durable grant."""
    assert root(client) == root(client)
    assert len(client.get("/api/state", headers=owner(client)).json()["roots"]) == 1


def test_s15_root_budget(client: TestClient) -> None:
    """Concurrent children share a single atomic root budget."""
    grant = root(client)
    b, c = child(client, grant), child(client, grant, "C")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(execute, client, b, "b", "B"),
            pool.submit(execute, client, c, "c", "C"),
        ]
        statuses = sorted(f.result().status_code for f in futures)
    assert statuses == [200, 409]
    assert len(client.get("/api/state", headers=owner(client)).json()["inbox"]) == 1


def test_s17_s18_uncertain(client: TestClient) -> None:
    """Lost responses reserve the slot; reconciliation never resends."""
    delegation = child(client, root(client))
    client.app.state.runtime.receiver.lose_response = True
    result = execute(client, delegation).json()
    assert result["execution_status"] == "uncertain"
    assert execute(client, delegation, "retry").status_code == 409
    response = client.post("/api/attempts/attempt-1/reconcile", headers=owner(client))
    assert response.json()["execution_status"] == "confirmed"
    assert len(client.get("/api/state", headers=owner(client)).json()["inbox"]) == 1


def test_s23_s24_s25_export(client: TestClient, tmp_path: Path) -> None:
    """Independent verifier trusts external fingerprints and rejects archive tampering."""
    from services.exporter import verify_pack

    delegation = child(client, root(client))
    execute(client, delegation)
    pack = client.get("/api/export", headers=owner(client)).content
    trust = client.app.state.runtime.keys.trust()
    assert verify_pack(pack, trust)["valid"] is True
    with pytest.raises(ValueError):
        verify_pack(pack, {})
    import io
    import zipfile

    original = zipfile.ZipFile(io.BytesIO(pack))
    altered = io.BytesIO()
    with zipfile.ZipFile(altered, "w") as archive:
        for name in original.namelist():
            content = original.read(name)
            archive.writestr(name, content + b" " if name == "grants.json" else content)
    with pytest.raises(ValueError):
        verify_pack(altered.getvalue(), trust)


def test_s04_s27_authentication(client: TestClient) -> None:
    """Every protected surface authenticates; unknown request fields fail closed."""
    for path in ("/", "/api/state", "/api/export"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=actor(client, "B")).status_code == 403
    assert client.post("/api/roots", headers=actor(client, "A"), json={}).status_code == 403
    grant = root(client)
    delegation = child(client, grant)
    assert execute(client, delegation, actor_id="B").status_code == 422


def test_named_report_preserves_legacy_snapshots(client: TestClient) -> None:
    """New demo documents coexist with earlier signed authorizations and evidence."""
    legacy = root(client)
    response = client.post(
        "/api/roots",
        headers=owner(client),
        json={
            "request_id": "harbor-demo",
            "document_id": "harbor-report-v1",
            "recipient_id": "Anna",
            "minutes": 5,
            "delegation_allowed": True,
        },
    )
    assert response.status_code == 200
    report = response.json()
    assert report["snapshot_hash"] != legacy["snapshot_hash"]
    assert (
        execute(client, child(client, legacy), "legacy-delivery").json()["execution_status"]
        == "confirmed"
    )
    delegation = child(client, report)
    assert (
        execute(client, delegation, "report-delivery", document_id="harbor-report-v1").json()[
            "execution_status"
        ]
        == "confirmed"
    )
    from services.exporter import verify_pack

    rt = client.app.state.runtime
    pack = client.get("/api/export", headers=owner(client)).content
    assert verify_pack(pack, rt.keys.trust())["receipts"] == 2
