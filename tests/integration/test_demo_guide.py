"""The guide follows persisted authority and receiver evidence, not inbox counts."""

from fastapi.testclient import TestClient

from .test_contract import actor, child, client, owner


def test_guide_lifecycle_and_receipt_matching(client: TestClient) -> None:
    """Legacy history and blocked attempts cannot falsely complete the guide."""
    def page() -> str:
        return client.get("/", headers=owner(client)).text

    assert "Step 1 of 4" in page()
    root = client.post("/api/roots", headers=owner(client), json={
        "request_id": "guide-root", "document_id": "harbor-report-v1",
        "recipient_id": "Anna", "minutes": 5, "delegation_allowed": True,
    }).json()
    assert "Step 2 of 4" in page()
    delegation = child(client, root)
    assert "Step 3 of 4" in page()
    proposal = {"child_id": delegation["grant_id"], "attempt_id": "guide-change",
                "document_id": "harbor-report-v2", "recipient_id": "Anna"}
    assert client.post("/api/execute", headers=actor(client, "B"), json=proposal).status_code >= 400
    assert "Step 3 of 4" in page()
    proposal.update(attempt_id="guide-delivery", document_id="harbor-report-v1")
    response = client.post("/api/execute", headers=actor(client, "B"), json=proposal)
    assert response.status_code == 200, response.text
    assert "Step 4 of 4 · Delivery verified" in page()
    assert 'href="#receipt-guide-delivery"' in page()
    assert 'id="receipt-guide-delivery"' in page()
    assert "This demo · matching delivery" in page()
    # A new approval must start its own flow despite a previously confirmed inbox record.
    client.post("/api/roots", headers=owner(client), json={
        "request_id": "guide-next", "document_id": "harbor-report-v1",
        "recipient_id": "Anna", "minutes": 5, "delegation_allowed": True,
    })
    assert "Step 2 of 4" in page()
    assert "Step 4 of 4 · Delivery verified" not in page()


def test_guide_recovers_from_revocation_and_uncertain_delivery(client: TestClient) -> None:
    """Do not suggest a new dispatch when the existing outcome is unknown."""
    root = client.post("/api/roots", headers=owner(client), json={
        "request_id": "guide-uncertain", "document_id": "harbor-report-v1",
        "recipient_id": "Anna", "minutes": 5, "delegation_allowed": True,
    }).json()
    client.post(f'/api/roots/{root["grant_id"]}/revoke', headers=owner(client))
    assert "Step 1 of 4" in client.get("/", headers=owner(client)).text
    root = client.post("/api/roots", headers=owner(client), json={
        "request_id": "guide-fresh", "document_id": "harbor-report-v1",
        "recipient_id": "Anna", "minutes": 5, "delegation_allowed": True,
    }).json()
    delegation = child(client, root)
    client.app.state.runtime.receiver.lose_response = True
    response = client.post("/api/execute", headers=actor(client, "B"), json={
        "child_id": delegation["grant_id"], "attempt_id": "guide-unknown",
        "document_id": "harbor-report-v1", "recipient_id": "Anna",
    })
    assert response.json()["execution_status"] == "uncertain"
    html = client.get("/", headers=owner(client)).text
    assert "Check the existing delivery" in html
    assert 'href="#attempt-guide-unknown"' in html
    assert "Step 4 of 4 · Delivery verified" not in html


def test_latest_unapproved_revision_does_not_reuse_old_success(client: TestClient) -> None:
    """The guide starts fresh when the latest approval is outside its v1 scenario."""
    client.post("/api/roots", headers=owner(client), json={
        "request_id": "guide-v2", "document_id": "harbor-report-v2",
        "recipient_id": "Anna", "minutes": 5, "delegation_allowed": True,
    })
    assert "Step 1 of 4" in client.get("/", headers=owner(client)).text
