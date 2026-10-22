# Agent Delegation Ledger — scenarios and acceptance plan v0.1

22 October 2026. English working catalogue for the approved bounded MVP.
Rules: AGENT_DELEGATION_TDPD_SPEC_v0.1.md. Architecture: ARCHITECTURE_CONTRACT.md.
Executable coverage and limits: IMPLEMENTATION_STATUS.md. Human UAT remains pending.

## Fixtures and oracles

Owner O; orchestrator A; executors B/C; recipient Anna; unrelated recipient Mallory.
Documents D:v1, changed D:v2 and unrelated X are synthetic. Clock control, barriers
and fault injection exist only in fixtures, never demo HTTP endpoints. Principals come
from separate authenticated credentials, never editable actor_id fields. Scripted agents
create proposals; they never simulate owner consent.

Unless stated otherwise, each scenario starts with valid root/child grants in a fresh
case. A denial requires a visible reason, durable attempt/event, no dispatch and inbox
delta zero. Success requires UI confirmation, actual inbox data, a valid receiver signature
and root/child/snapshot linkage. Automated checks do not establish exhaustive attack coverage.

## Scenario catalogue

| ID / priority / level | Initial state and action | Observable result and persistence | Rules |
|---|---|---|---|
| S01 P0 browser | O opens an empty case | Honest empty state; no invented grants/deliveries; approval form available | R01,R11 |
| S02 P0 browser | O previews D:v1 → Anna and approves | Version/hash/expiry/one use/delegation visible; one durable root; same ID after reload | R01,R16 |
| S03 P0 browser | O cancels an unconfirmed form | No root, authorizing event or inbox message | R01 |
| S04 P0 browser/API | Submit empty/invalid fields; repeat as direct request | Field error/INVALID_INPUT; unknown fields and invalid types rejected; no root | R01,R03 |
| S05 P0 browser | A delegates an active root to B; B delivers D:v1 to Anna | One child, one inbox item, confirmed attempt, valid receipt; persistence after reload | R02–R07,R10–R11,R16 |
| S06 P0 browser | A tries to delegate a root for Anna to Mallory | SCOPE_ESCALATION; durable denial; no child or dispatch | R03,R15 |
| S07 P0 integration | A changes action, hash, audience or extends expiry | Each variant denied with SCOPE_ESCALATION; zero children/dispatch | R03 |
| S08 P0 integration | B tries to issue another child to C | REDELEGATION_DENIED; no third-level grant | R03 |
| S09 P0 integration | C presents B's child and claims actor_id=B | Authenticated actor wins; WRONG_ACTOR or rejected override; no receiver call/delivery | R04,R17 |
| S10 P0 browser | B proposes D:v2 or another recipient under a D:v1 child | DOCUMENT_CHANGED/scope denial; exact reason persisted; inbox unchanged | R04,R11 |
| S11 P0 integration | Execute at expires_at−1ms and separately exactly expires_at | First allowed; boundary EXPIRED; fresh case per branch | R05 |
| S12 P0 browser | O revokes root; B executes afterward | REVOKED; child cannot execute; empty inbox; revocation persists on reload | R05,R09,R16 |
| S13 P0 browser | Double-click approval, including while pending | Pending control disabled; one root; same request ID returns same root | R01,R16 |
| S14 P0 browser | Execute after confirmed delivery | LIMIT_RESERVED_OR_USED, or same outcome for an exact same attempt; inbox count one | R06–R07 |
| S15 P0 integration | B/C hold children of one root; race distinct attempts with a barrier | Exactly one reservation/dispatch; other denied; inbox count one | R06 |
| S16 P0 receiver | Replay accepted key K exactly, then with changed parameters | Same receipt without another row; changed payload conflicts | R07 |
| S17 P0 browser | Receiver persists but response is lost | UI uncertain; inbox count one; occupied slot; reload does not retry | R08,R16 |
| S18 P0 browser | O reconciles S17 | Read-only lookup finds matching signed receipt; confirmed; inbox still one | R08,R10 |
| S19 P0 integration | Dispatch times out with no receipt; reconcile returns not found | Remains uncertain; occupied slot; no new attempt is sent | R08 |
| S20 P0 integration | Force both revoke/reserve serialization orders | Revoke first: no dispatch. Reserve first: cancellation not promised; outcome tracked | R09 |
| S21 P0 integration | Authorization storage fails before reserve | STORAGE_UNAVAILABLE; zero receiver calls; visible error | R16 |
| S22 P0 integration | Receiver accepts; local result write fails; restart | No success without persisted evidence; budget retained; reconciliation confirms without redispatch | R08,R16 |
| S23 P0 browser/CLI | Export completed S05; verify with external trusted fingerprints | All member hashes/signatures/linkage/manifest valid; evidence agrees with receipt/inbox | R12–R14 |
| S24 P0 verifier | Change recipient/document/event or remove a middle/final event without changing manifest | Nonzero verifier exit: invalid signature/hash/chain/manifest; never valid | R12–R13 |
| S25 P0 verifier | Archive signed by unrelated keys embeds its own public keys | UNKNOWN_KEY; embedded key does not establish trust | R13 |
| S26 P0 integration | Tamper runtime signatures, key IDs, parent/case linkage or receipt | Execution denied before effect; fake receipt never confirms delivery | R04,R10 |
| S27 P0 browser/API | No session, agent instead of owner, or cross-site owner mutation | 401/403; no snapshot/credential leak, public export/inbox or unauthorized mutation | R17 |
| S28 P0 integration | Restart app and receiver after delivery/revocation | Grants, budget, events, receipt and inbox persist; replay creates no delivery | R16 |
| S29 P0 integration | Inspect allowed/blocked/uncertain logs and exports using a synthetic canary | No credentials; document bytes only in authorized snapshot/inbox/export, not technical logs | R15 |
| S30 P1 browser | Choose 1/10 minutes, then 0/11 | Bounds accepted; out-of-range rejected; child expiry no later than root | R03,R05 |
| S31 P0 browser | Traverse the demonstration by keyboard | Every action available; labels/focus/text reasons; no color-only verdict | Surface |
| S32 P1 browser | Slow/unavailable receiver; execute and reload | Loading resolves to honest uncertain/error; no frozen UI or false success | R08,R10,R16 |

## Coverage and dangerous transitions

Root creation/cancellation/input: S01–S04,S13. Delegation/isolation: S05–S10,S25–S27.
Time/revocation: S11–S12,S20,S30. Shared budget/replay: S14–S16.
Uncertainty/recovery/durability: S17–S22,S28,S32. Evidence: S23–S26,S29.
Surface: S01–S05,S10,S12–S14,S17–S18,S23,S31–S32.

Two children do not imply two budgets. Revocation does not undo past effects. Expiry
does not prohibit read-only reconciliation of an already started attempt. A verifier
does not prove archive freshness without an independent checkpoint.

## RED → GREEN protocol

First establish working container/browser infrastructure; an infrastructure failure is
not a behavioral RED result. Write executable acceptance checks before implementing
new behavior. Prioritize S02/S05/S06/S10/S14 and S09/S15/S26, then expiry/revocation,
idempotency/recovery and durability, then evidence/trust tampering. Cover remaining P0
states, lint/types/dependency checks, cleanup and owner UAT. Live LLM, blockchain or
extra integrations must not displace mandatory acceptance.

See IMPLEMENTATION_STATUS.md for checks actually executed and their limitations.
Never infer completed TDPD or exhaustive scenario coverage from a green subset.

## Live demonstration

O approves D:v1 → Anna → A delegates to B → attempt to change recipient is blocked →
normal delivery is confirmed → another child cannot bypass the shared limit → exported
archive verifies → a tampered copy fails. Show actual inbox and receipt, not only a status
card. Explicitly identify scripted agents and limits of service signatures.

## Owner UAT

| ID | Owner action | Acceptance condition |
|---|---|---|
| U01 | Review the grant before approving | Document, recipient, expiry and delegation are understandable without reading JSON |
| U02 | Run allowed and blocked flows | It is clear who acted and why the action was allowed or denied |
| U03 | Revoke a grant and inspect uncertainty | No promise to undo the past; no unknown result presented as success |
| U04 | Verify the export and a modified copy | Integrity guarantees and the trusted-operator boundary are understandable |
| U05 | Evaluate the whole task | Owner explicitly confirms the chain solves the original problem |

UAT verdict: NOT ACCEPTED YET. Record date, owner and comments after explicit human
acceptance. Automation or an agent-led demonstration cannot substitute for that decision.
