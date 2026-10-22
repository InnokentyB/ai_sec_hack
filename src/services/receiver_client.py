"""Bounded HTTP transport for the independent receiver."""

import time
from typing import cast

import httpx

from core.canonical import Json
from core.crypto import Keys


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


