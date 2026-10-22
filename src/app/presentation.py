"""English presentation names for the explicitly fictional delivery scenario."""

ACTOR_LABELS = {
    "owner": "Maya · Security lead",
    "A": "Atlas · Coordinator",
    "B": "Courier · Delivery agent",
    "C": "Relay · Backup agent",
    "authorization": "Authorization service",
    "ledger": "Evidence ledger",
    "receiver": "Northstar receiving service",
}

EVENT_LABELS = {
    "ROOT_GRANT_ISSUED": "Maya approved report delivery",
    "CHILD_GRANT_DELEGATED": "Atlas delegated a delivery capability",
    "DELEGATION_BLOCKED": "An attempted change of authority was blocked",
    "ATTEMPT_RESERVED": "The shared delivery slot was reserved",
    "ATTEMPT_BLOCKED": "A delivery attempt was blocked",
    "DISPATCH_STARTED": "Report dispatch started",
    "DISPATCH_CONFIRMED": "The receiving service confirmed delivery",
    "DISPATCH_UNCERTAIN": "Delivery could not be confirmed",
    "RECOVERY_UNCERTAIN": "An interrupted delivery requires reconciliation",
    "ROOT_REVOKED": "Maya revoked the authorization",
}
