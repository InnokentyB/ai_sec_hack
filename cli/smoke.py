"""Exercise the running app and receiver containers with synthetic data only."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import cast
from uuid import uuid4

import httpx

from core.canonical import Json
from core.crypto import fingerprint


def main() -> int:
    """Check a real HTTP delivery, evidence CLI and restart persistence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    directory = Path(os.environ["LEDGER_DATA"])
    credentials = json.loads((directory / "credentials.json").read_text())
    receipt_path = directory / "smoke-result.json"
    with httpx.Client(base_url=args.url, timeout=15, trust_env=False) as client:
        # Only read-only readiness probes may retry. Never retry a mutation.
        for _ in range(200):
            try:
                ready = client.get(
                    "/api/state",
                    headers={"Authorization": "Bearer " + credentials["owner"]},
                )
                if ready.status_code == 200 and ready.json()["receiver_available"]:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("App/receiver readiness timed out; no mutation attempted")


        def request(method: str, path: str, role: str = "owner", payload: object = None) -> Json:
            response = client.request(
                method, path, headers={"Authorization": "Bearer " + credentials[role]}, json=payload
            )
            response.raise_for_status()
            return cast(Json, response.json())

        if not args.verify_only:
            grant = request(
                "POST",
                "/api/roots",
                payload={
                    "request_id": str(uuid4()),
                    "document_id": "doc-v1",
                    "recipient_id": "Anna",
                    "minutes": 5,
                    "delegation_allowed": True,
                },
            )
            child = request(
                "POST",
                "/api/children",
                "A",
                {
                    "root_id": cast(str, grant["grant_id"]),
                    "executor_id": "B",
                    "recipient_id": "Anna",
                    "snapshot_hash": cast(str, grant["snapshot_hash"]),
                    "action": "deliver_document",
                    "audience": "synthetic-inbox",
                    "expires_at": cast(float, grant["expires_at"]),
                    "delegation_allowed": False,
                },
            )
            attempt_id = str(uuid4())
            attempt = request(
                "POST",
                "/api/execute",
                "B",
                {
                    "child_id": cast(str, child["grant_id"]),
                    "attempt_id": attempt_id,
                    "document_id": "doc-v1",
                    "recipient_id": "Anna",
                },
            )
            assert attempt["execution_status"] == "confirmed", attempt
            receipt_path.write_text(
                json.dumps(
                    {
                        "attempt_id": attempt_id,
                        "root_id": cast(str, grant["grant_id"]),
                        "child_id": cast(str, child["grant_id"]),
                    }
                )
            )
        expected = json.loads(receipt_path.read_text())
        state = request("GET", "/api/state")
        attempt = next(
            (
                item
                for item in cast(list[Json], state["attempts"])
                if cast(str, item["attempt_id"]) == cast(str, expected["attempt_id"])
            )
        )
        assert attempt["execution_status"] == "confirmed"
        matches = [
            message
            for message in cast(list[Json], state["inbox"])
            if cast(str, cast(Json, cast(Json, message["receipt"])["payload"])["attempt_id"])
            == cast(str, expected["attempt_id"])
        ]
        assert len(matches) == 1
        replay = client.post(
            "/api/execute",
            headers={"Authorization": "Bearer " + credentials["B"]},
            json={
                "child_id": cast(str, expected["child_id"]),
                "attempt_id": str(uuid4()),
                "document_id": "doc-v1",
                "recipient_id": "Anna",
            },
        )
        assert replay.status_code in (403, 409)
        pack = client.get(
            "/api/export", headers={"Authorization": "Bearer " + credentials["owner"]}
        )
        pack.raise_for_status()
        (directory / "evidence.zip").write_bytes(pack.content)
    public = json.loads((directory / "public.json").read_text())
    public.update(json.loads((directory / "receiver-public.json").read_text()))
    (directory / "trust.json").write_text(
        json.dumps({role: fingerprint(key) for role, key in public.items()})
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.verify",
            str(directory / "evidence.zip"),
            "--trust",
            str(directory / "trust.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    print(
        json.dumps(
            {
                "http_delivery": "confirmed",
                "receiver_messages_for_attempt": len(matches),
                "replay": "blocked",
                "offline_verifier": json.loads(result.stdout),
                "restart_check": args.verify_only,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
