"""Strict HTTP proposals: principals and server time are never client fields."""

from pydantic import BaseModel, ConfigDict, Field


class Proposal(BaseModel):
    """Reject unknown fields and type coercions at untrusted boundaries."""

    model_config = ConfigDict(extra="forbid", strict=True)


class RootProposal(Proposal):
    """Explicit owner approval of the previewed synthetic snapshot."""

    request_id: str = Field(min_length=1, max_length=100)
    document_id: str
    recipient_id: str
    minutes: int = Field(ge=1, le=10)
    delegation_allowed: bool


class ChildProposal(Proposal):
    """A single non-redelegable executor capability."""

    root_id: str
    executor_id: str
    recipient_id: str
    snapshot_hash: str
    action: str
    audience: str
    expires_at: float
    delegation_allowed: bool = False


class ExecutionProposal(Proposal):
    """Actual document and recipient requested by an authenticated executor."""

    child_id: str
    attempt_id: str = Field(min_length=1, max_length=100)
    document_id: str
    recipient_id: str
