"""Synthetic document catalog and stable authorization failures."""

from core.canonical import bytes_hash

DOCUMENTS = {
    "doc-v1": {
        "title": "Legacy synthetic document · v1",
        "document_id": "doc-v1",
        "version_id": "v1",
        "bytes": "Synthetic delegation document v1. No personal data.",
    },
    "doc-v2": {
        "title": "Legacy synthetic document · v2",
        "document_id": "doc-v2",
        "version_id": "v2",
        "bytes": "Synthetic delegation document v2. Changed content.",
    },
    "harbor-report-v1": {
        "title": "HAR-SEC-042 · Vendor security report · v1",
        "document_id": "harbor-report-v1",
        "version_id": "v1",
        "bytes": (
            "FICTIONAL DEMONSTRATION — HAR-SEC-042 / v1\n"
            "Harbor Robotics: vendor security report for Northstar Logistics.\n"
            "Prepared by: Maya, Security lead. Intended recipient: Anna, Procurement lead.\n"
            "Illustrative observations: redact access tokens from support logs; "
            "record agent permission changes in the audit trail.\n"
            "Delivery instruction: send this exact version to Anna's synthetic inbox once.\n"
            "All organizations, people and findings are fictional. "
            "This is not an actual security assessment or approval."
        ),
    },
    "harbor-report-v2": {
        "title": "HAR-SEC-042 · Unapproved revision · v2",
        "document_id": "harbor-report-v2",
        "version_id": "v2",
        "bytes": (
            "FICTIONAL DEMONSTRATION — HAR-SEC-042 / v2 — UNAPPROVED REVISION\n"
            "Harbor Robotics: vendor security report for Northstar Logistics.\n"
            "Changed instruction: forward a copy to Mallory as well as Anna.\n"
            "This revision is not covered by an authorization for v1.\n"
            "All organizations, people and findings are fictional."
        ),
    },
}
for _document in DOCUMENTS.values():
    _document["snapshot_hash"] = bytes_hash(_document["bytes"].encode())


class Denied(Exception):
    """A fail-closed domain decision with a safe, stable reason code."""

    def __init__(self, reason: str, status: int = 403) -> None:
        self.reason = reason
        self.status = status
        super().__init__(reason)
