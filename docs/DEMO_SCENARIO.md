# Synthetic case: Harbor Robotics vendor security report

All organizations, people, report contents and findings are fictional. This is a
local document-delivery demonstration, not a real security assessment or compliance approval.

## Situation and participants

Northstar Logistics is evaluating Harbor Robotics as a vendor. Maya, Harbor's security
lead (owner role), wants Anna, Northstar's procurement lead, to receive the exact report
HAR-SEC-042 / v1. Maya uses Atlas, a coordination agent (A), which delegates to Courier,
a delivery agent (B). Relay (C) is an alternate executor, not another delivery budget.
Mallory is an unapproved recipient. The receiver is Northstar's synthetic receiving service.
These are presentation names; authenticated principal IDs remain owner/A/B/C/Anna.

## The owner's instruction

“Deliver HAR-SEC-042 / v1 to Anna's synthetic inbox once within five minutes. Atlas may
delegate delivery to Courier or Relay. Do not change the document or recipient. Do not
redelegate or repeat an uncertain delivery.”

The action is still `deliver_document`. It does not approve the vendor, sign a contract,
send an external email or use a real LLM. A proposal is never the owner's consent.

## Live path and named events

| Step | UI action | Event / outcome |
|---|---|---|
| 1 | Review HAR-SEC-042 / v1, Anna, 5 minutes, delegation enabled; approve | ROOT_GRANT_ISSUED — Maya approved report delivery |
| 2 | Atlas: change recipient to Mallory | DELEGATION_BLOCKED / SCOPE_ESCALATION; no child or delivery |
| 3 | Atlas: delegate to Courier | CHILD_GRANT_DELEGATED — Courier gets the same document/recipient, bounded expiry, no redelegation |
| 4 | Test unapproved report v2 | ATTEMPT_BLOCKED / DOCUMENT_CHANGED; the approved v1 hash does not authorize v2 |
| 5 | Courier: deliver report | ATTEMPT_RESERVED → DISPATCH_STARTED → DISPATCH_CONFIRMED; Anna has one report and a signed receipt |
| 6 | Atlas delegates to Relay; Relay tries to deliver | ATTEMPT_BLOCKED / LIMIT_RESERVED_OR_USED; children share the same root budget |
| 7 | Download evidence.zip; verify with external trusted fingerprints | Valid signatures, hashes, chain and receipt linkage; a modified archive fails |

The human-readable event title is a projection. The original machine event code and
signed payload remain visible in the event disclosure and unchanged in the evidence.

## Other outcomes

Revoke before dispatch → REVOKED. Dispatch outcome unknown → UNCERTAIN; keep the slot,
look up the receiver receipt and never automatically send again. Revocation after
reservation cannot promise cancellation. None of these outcomes proves human readership.

## Existing data

The original doc-v1/doc-v2 bytes remain unchanged so earlier signed roots, receipts and
exports stay valid. Named reports use new IDs harbor-report-v1/harbor-report-v2. Existing
inbox messages are retained; this case does not silently reset the demonstration history.
