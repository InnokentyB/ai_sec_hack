"""RFC 8785 serialization and SHA-256 digests."""

import hashlib
from typing import cast

import rfc8785
from pydantic import JsonValue

Json = dict[str, object]


def canonical(value: object) -> bytes:
    """Serialize JSON-compatible data using the JSON Canonicalization Scheme."""
    return rfc8785.dumps(cast(JsonValue, value))


def digest(value: object) -> str:
    """Hash a canonical JSON value."""
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_hash(value: bytes) -> str:
    """Hash exact document or archive-member bytes."""
    return hashlib.sha256(value).hexdigest()
