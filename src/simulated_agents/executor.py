"""Deterministic executor action proposals, authenticated separately by the runtime."""

from typing import cast
from uuid import uuid4

from core.canonical import Json
from core.models import ExecutionProposal


def propose(child: Json, document_id: str = "doc-v1") -> ExecutionProposal:
    """Create a fresh attempt against one exact immutable synthetic document."""
    return ExecutionProposal(
        child_id=cast(str, child["grant_id"]),
        attempt_id=str(uuid4()),
        document_id=document_id,
        recipient_id=cast(str, child["recipient_id"]),
    )
