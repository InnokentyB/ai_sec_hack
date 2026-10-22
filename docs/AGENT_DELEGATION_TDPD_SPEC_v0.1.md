# Agent Delegation Ledger — TDPD specification v0.1

22 October 2026, Europe/Lisbon. Input and Surface Gates: APPROVED through the
[architecture contract](ARCHITECTURE_CONTRACT.md). Implementation is authorized by
the owner's current request. Automated evidence is in IMPLEMENTATION_STATUS.md;
human acceptance remains separate.

TDPD / Test-Driven Product Development is Innokenty Bodrov's method.

## 1. Problem and observable value

BP-01. An owner assigns work to an orchestrator, which recruits an executor. The owner
must constrain each participant's authority and later verify who authorized a specific
action, who executed it and what result the receiving service confirmed. A shared user
session and an unsubstantiated success message do not provide that chain.

MVP success: the owner approves a grant, sees a child grant and one confirmed delivery;
scope escalation, substitution and replay create no additional delivery; exported evidence
passes independent verification. The owner evaluates understanding and usefulness in UAT.
Target outcomes: one authorized delivery, zero unauthorized deliveries, zero automatic
retries of uncertain effects. These are acceptance criteria, not universal security claims.

## 2. Sources and decision authority

Evidence baseline EB-01, 2026-10-22. Owner decisions establish delegation and evidence
without blockchain. AGENTS.md establishes execution and safety rules. Historical
readiness/runbook files describe the superseded Permission Firewall concept and are
source evidence only. RFC 8693 and RFC 9396 informed delegation and fine-grained
permission terminology; this prototype does not claim OAuth protocol compliance.

The owner clarified that “PDF” meant TDPD; no separate PDF source exists. The current
bounded document-delivery workflow supersedes the older three-tool firewall idea.
Changing action, delegation depth or trusted party requires revising this specification
and its affected scenarios before implementation. Contest eligibility and prebuilt-code
rules remain outside this specification. Preserve historical chat exports as evidence.

## 3. Scope

One action: `deliver_document` to a local synthetic inbox. One delegation depth:
owner → orchestrator → executor; a third level is prohibited. Two executors demonstrate
that children share one root-wide limit. No real contracts, personal data, legally binding
signatures, payments, public publication, live LLM, OAuth, MCP or blockchain dependency.
Scripted agents are explicitly labeled deterministic adapters; they do not establish
real-model quality or availability.

## 4. Surface

Local web UI with Permissions, Event chain and Synthetic inbox. Flow: select document
and recipient → inspect constraints → approve → delegate → execute or show a denial →
export evidence. A standalone CLI verifies the export; it does not replace browser tests.

States: empty, document preview, form, pending, active/revoked/expired, blocked with
reason, dispatching, confirmed, uncertain, storage/service error, verification result
and persisted state after reload. Double submission must not create another grant or
dispatch. Disable pending controls. Cancelling a form authorizes nothing. Reject missing
or invalid fields and unknown input fields. Expiry is 1–10 minutes, default 5;
validity requires server now < expires_at. Exact expiry is invalid.

Desktop target 1280×800; no horizontal scroll at 768px. English labels, keyboard controls,
visible focus and reasons expressed in text. Human usability acceptance remains required.
Approved code location is the repository root; stack and commands are in the architecture
contract and README. Never reuse other projects' runtimes, keys or data.

## 5. Trust and canonical data

Canonical durable aggregate: DelegationCase, identified by case_id. It contains immutable
document snapshots, root/child grants, attempts and receipts. UI, ledger and export are
projections of this aggregate. No importer, background synchronizer or scheduler.
Mutations pass through authorization/dispatch boundaries; export is read-only.

The owner has a separate local demo session, not verified real-world identity. A/B/C
have different credentials. Derive principals from credentials, never an editable actor
field. Authorization, dispatcher, storage and key provisioning are trusted. Agent proposals,
documents, HTTP input and imported evidence are untrusted. Compromise of the host owner
or all trusted keys is outside the MVP's guarantee.

| Entity | Required fields |
|---|---|
| DocumentSnapshot | document_id, version_id, bytes, SHA-256, immutable=true |
| RootGrant | grant_id, case_id, owner_id, orchestrator_id, action, snapshot_hash, recipient_id, audience, issued_at, expires_at, max_uses=1, delegation_allowed |
| ChildGrant | grant_id, parent_id, authenticated_issuer, executor_id, action, snapshot_hash, recipient_id, audience, issued_at, expires_at, max_uses=1, delegation_allowed=false |
| Attempt | attempt_id, case_id, root_id, child_id, authenticated_actor, actual_action_digest, idempotency_key, decision, reason, execution_status |
| Receipt | receipt_id, attempt_id, root_id, child_id, receiver_id, snapshot_hash, recipient_id, received_at, signature |
| EvidenceEvent | event_id, case_id, sequence, previous_hash, kind, actor_id, server_time, payload_digest, payload, signer_key_id, signature |

Authorization Service signs the root after explicit owner confirmation; this is a
service attestation, not the owner's personal signature. A signs children, B/C sign
actions, Receiver signs receipts and Ledger signs events. Roles have separate keys.
Never put private keys in source, images or exports. Bind trusted keys to roles outside
the evidence archive. Implementation envelopes represent signer_key_id as key_id.

## 6. Deterministic rules

**R01 — Explicit owner authority.** Only the owner creates/revokes a root after viewing
the exact snapshot, recipient, action, expiry and delegation permission. Store the
snapshot immutably.

**R02 — Authorized delegation.** Only the root's orchestrator may delegate, under an
active root.

**R03 — Scope narrowing.** Child action, document hash, recipient and audience must
exactly match the root. Child expiry cannot exceed root expiry. Identify the executor
explicitly and prohibit further delegation. Reject unknown fields and type coercion.

**R04 — Authenticated execution.** Only the authenticated child executor may execute.
Check both signatures, trusted keys, parent/case linkage and actual action parameters.

**R05 — Current validity.** Grants must not be revoked and server now must be strictly
before expires_at. Recheck during atomic reservation. Test clock control is fixture-only.

**R06 — Root-wide budget.** A root permits at most one dispatch across all children.
Reserve atomically before contacting Receiver.

**R07 — Receiver idempotency.** Every attempt has one stable idempotency key. Receiver
stores at most one message per key, returns the original receipt for an exact repeat,
and rejects changed payload under that key without another message.

**R08 — Conservative uncertainty.** Unknown post-dispatch outcomes keep the slot occupied.
No automatic resend. Only read-only receipt lookup is allowed. Missing evidence does
not prove non-delivery. Never automatically create a replacement root.

**R09 — Serialized revocation.** Revoke and reserve share a serialization boundary.
Revocation first blocks dispatch. Reservation first may already have started dispatch;
the UI must not promise cancellation. Confirmed delivery never disappears on revocation.

**R10 — Evidence-based success.** Confirm only a valid Receiver receipt bound to the
actual snapshot, recipient and attempt. HTTP 200 alone is insufficient.

**R11 — Observable effects.** Confirmed UI shows the actual inbox record and receipt.
A blocked attempt invokes Receiver zero times and creates zero new messages.

**R12 — Signed append-only ledger.** Events are ordered by case sequence. Sign the complete
canonical event, including previous_hash. RFC 8785 and Ed25519 provide deterministic
serialization and signatures. Payload changes and linkage breaks fail verification.

**R13 — Independent export verification.** Export snapshot, grants, events, receipts,
schema and signed manifest with count/final hash. Require external trusted fingerprints;
keys included by an archive do not establish trust.

**R14 — Honest verification meaning.** Verification establishes integrity relative to
trusted keys and the manifest. It does not establish human readership, every assertion's
truth, or history completeness without an independent checkpoint. A complete rewrite
by the trusted operator is outside the guarantee.

**R15 — Audit denials without secrets.** Persist forbidden actions and reasons, never
credentials. Full synthetic document bytes belong in snapshot/inbox/authorized export,
not technical logs or repeated evidence-event payloads.

**R16 — Durable fail-closed transitions.** Failure to persist pre-dispatch authorization,
reservation or evidence prevents sending. Failure to persist a post-dispatch result
leaves uncertain/recovery-needed, never unsubstantiated success. Restart preserves
budget, grants, revocation, attempts and inbox.

**R17 — Protected boundaries.** Authenticate and authorize every case/inbox/export read
and mutation. No public case data, wildcard CORS or actor override. Owner cookie mutations
require CSRF protection and exact origin checks.

Reason codes: INVALID_INPUT, UNAUTHENTICATED, WRONG_ACTOR, WRONG_AUDIENCE,
INVALID_SIGNATURE, UNKNOWN_KEY, SCOPE_ESCALATION, REDELEGATION_DENIED,
DOCUMENT_CHANGED, REVOKED, EXPIRED, LIMIT_RESERVED_OR_USED, STORAGE_UNAVAILABLE.
Priority: parse/auth → signatures/linkage → scope → revoked/expired → atomic budget.
No denial may dispatch.

## 7. Lifecycle

Root: active → revoked; expiry is computed from server time. Reserved/used budget is
independent of validity. Expired grants remain in history.

Attempt: blocked, or reserved → dispatching → confirmed | uncertain. A crash after
reservation recovers as uncertain. A conservative false block is acceptable; an automatic
retry is not. Reconciliation changes uncertain to confirmed only with trustworthy evidence.
Unknown outcomes never automatically return the slot to available.

## 8. Approved architecture decisions

ADR-01: local browser surface, distinct logical roles/credentials and independent Receiver.
ADR-02: SQLite durable state, atomic root-wide reservation, separate receiver idempotency store.
ADR-03: canonical Ed25519 envelopes, role-bound trust and independently supplied fingerprints.
ADR-04: scripted deterministic agents; no legal/personal-signature or full OAuth claim.
ADR-05: Tower Docker amd64, non-root, loopback, limits and browser sandbox; temporary jobs --rm.
ADR-06: conservative uncertainty and no automatic resend; safety takes priority over availability.

See ARCHITECTURE_CONTRACT.md for implementation placement and runtime details.

## 9. Reliance and acceptance

All effects and data are synthetic. The main risk is presenting a demonstration as
production authorization or legally meaningful proof. The UI explicitly labels DEMO
and the limits of service signatures. Real documents or consent would require separate
identity, authority, receiver-terms, key protection, retention, recovery and legal review;
that expansion is not authorized by this bounded prototype request.

The scenario catalogue and U01–U05 are in AGENT_DELEGATION_SCENARIOS_v0.1.md.
Input/Surface: approved. Automated implementation evidence: IMPLEMENTATION_STATUS.md.
UAT: pending. Specification approval and passing tests do not establish owner acceptance.
