"""Deterministic orchestrator proposals; never impersonate owner approval."""

from typing import cast

from core.canonical import Json
from core.models import ChildProposal


def propose(root: Json, executor: str = "B", recipient: str = "Anna") -> ChildProposal:
    """Propose delegation while preserving the root's exact scope."""
    return ChildProposal(
        root_id=cast(str, root["grant_id"]),
        executor_id=executor,
        recipient_id=recipient,
        action=cast(str, root["action"]),
        snapshot_hash=cast(str, root["snapshot_hash"]),
        audience=cast(str, root["audience"]),
        expires_at=cast(float, root["expires_at"]),
        delegation_allowed=False,
    )
