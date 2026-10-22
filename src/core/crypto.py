"""Persistent role-separated Ed25519 keys and signed canonical envelopes."""

import base64
import json
import os
from pathlib import Path
from typing import cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from core.canonical import Json, bytes_hash, canonical

ROLES = ("authorization", "A", "B", "C", "ledger")


def public_text(key: Ed25519PublicKey) -> str:
    """Encode a raw public key for transport."""
    return base64.b64encode(key.public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def fingerprint(public: str) -> str:
    """Compute the independently provisioned public-key fingerprint."""
    return bytes_hash(base64.b64decode(public, validate=True))


def sign(payload: Json, role: str, key: Ed25519PrivateKey) -> Json:
    """Sign role and complete payload; never include the private key."""
    body = {"key_id": role, "payload": payload}
    return {**body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}


def verify(envelope: Json, public: dict[str, str], expected_role: str) -> Json:
    """Verify an envelope using a caller-supplied trusted role binding."""
    try:
        if set(envelope) != {"key_id", "payload", "signature"}:
            raise ValueError("INVALID_SIGNATURE")
        if cast(str, envelope["key_id"]) != expected_role or expected_role not in public:
            raise ValueError("UNKNOWN_KEY")
        key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(public[expected_role], validate=True)
        )
        key.verify(
            base64.b64decode(cast(str, envelope["signature"]), validate=True),
            canonical({"key_id": expected_role, "payload": cast(Json, envelope["payload"])}),
        )
        if not isinstance(cast(Json, envelope["payload"]), dict):
            raise ValueError("INVALID_SIGNATURE")
        return cast(Json, envelope["payload"])
    except (InvalidSignature, KeyError, TypeError, ValueError) as error:
        raise ValueError("INVALID_SIGNATURE") from error


class Keys:
    """Load private role keys from a restricted runtime directory."""

    def __init__(self, directory: Path, roles: tuple[str, ...] = ROLES) -> None:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.private: dict[str, Ed25519PrivateKey] = {}
        for role in roles:
            path = directory / f"{role}.key"
            if not path.exists():
                raw = Ed25519PrivateKey.generate().private_bytes(
                    Encoding.Raw, PrivateFormat.Raw, NoEncryption()
                )
                try:
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    pass
                else:
                    with os.fdopen(fd, "wb") as output:
                        output.write(raw)
            self.private[role] = Ed25519PrivateKey.from_private_bytes(path.read_bytes())
        self.public = {role: public_text(key.public_key()) for role, key in self.private.items()}

    def signed(self, role: str, payload: Json) -> Json:
        """Create a signature for one provisioned role."""
        return sign(payload, role, self.private[role])

    def trust(self) -> dict[str, str]:
        """Return public fingerprints, to be distributed out of band."""
        return {role: fingerprint(public) for role, public in self.public.items()}

    def publish(self, path: Path) -> None:
        """Publish only public role bindings to the receiver's read-only volume."""
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.public))
        temporary.chmod(0o644)
        temporary.replace(path)
