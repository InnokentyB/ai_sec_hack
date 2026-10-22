# AI Security — readiness, 14 October 2026

Owning ACK: this profile chat owns Agent Permission Firewall preparation. Owner of local preparation: Codex in this chat. Participant and external decisions: Innokenty. Status: preparation only; no runnable project or final submission.

## Evidence and constraints

- Participation: Gmail message `1a1015e0e146f55a`, subject “Registration confirmed for AI Security Hackathon — Build, Break, Defend”, from AI Security Engineers, dated 2026-10-03 10:45 UTC. Verified through Gmail search on 14 October. The email lists 18:00–21:00 GMT+1.
- Official page checked 14 October: https://luma.com/aiseceng-nyni . Description lists 22 October, 18:00–21:30 Lisbon, submissions close 20:30; top three projects receive gift cards, amounts unspecified. Venue still Lisbon Central — TBC.
- Published description invites an idea and teammates, but does not establish rules for prebuilt code, AI coding assistants, team size, starter templates, judging criteria or submission mechanism. No official answer found; absence of a prohibition is not permission.
- No duplicate registration, payment, organizer contact, external submission or deployment authorized by this preparation task. No such action performed.
- Until rules are clarified, prepare specification, scenarios and tools; do not represent a prebuilt application as eligible contest work. Any later pre-event code must have disclosed provenance and cannot be assumed eligible.

## Scope and requirements

Project: Agent Permission Firewall. Theme: agent security; no formal track verified.

Intercept each proposed tool action before execution. The agent supplies action parameters, never permission or confirmation. Policy and confirmations belong to a trusted host. Use a simulated agent and harmless local mock tools for the first demo; live model integration is optional and must be disclosed if absent.

Actions: read_file, http_request, send_message. Decisions: allow, block, confirmation_required. Deny unknown tools and malformed inputs. Allow reads only under a designated synthetic-data directory, after resolving path traversal and symlinks. Allow HTTP only to exact approved HTTPS origins; block other schemes, credentials in URLs and redirects to unapproved origins. For the hackathon MVP, mock HTTP to avoid network/SSRF complexity. Messages to an approved recipient require human confirmation of the exact recipient and payload. Confirmation is bound to the exact action, expires, is single use, and cannot be supplied by the model. Cancellation means no execution. A block cannot be overridden through confirmation.

Execute only after authorization. Record action type, decision, rule, confirmation and execution outcome; redact payloads and secrets. Demo uses synthetic data exclusively. Claim limited scope: parameter-based enforcement for wrapped tools, not universal prompt-injection detection or protection against bypassing the wrapper.

## Acceptance and test plan

| Scenario | Expected decision and observable result |
|---|---|
| Read a synthetic file inside allowed directory | allow; mock read happens once |
| Read ../private.txt, absolute external path, or escaping symlink | block; no tool execution |
| Mock HTTPS request to exact approved origin | allow; mock request happens once |
| External destination, lookalike hostname, URL credentials, non-HTTPS scheme | block; no request |
| Unknown tool, missing arguments, invalid types | block; no execution |
| Document instructs agent to send synthetic secret externally | proposed action blocked by destination policy; no request |
| Message to approved recipient | confirmation_required; zero executions before approval |
| Approve exact message | one execution; audit outcome recorded |
| Change payload/recipient after approval, replay or expired approval | no execution; new confirmation required or block per policy |
| Cancel confirmation | zero executions |
| Tool fails after approval | error recorded, no automatic duplicate send |
| Audit contains synthetic secret marker | marker absent from logs |

Tests are specified, not implemented or passed. Security scans of project code and dependencies are required by event description and remain pending until code exists.

## Local environment evidence

Checked 14 October: Python 3.11.13, Node 24.6.0, Git 2.39.5 available. Suggested MVP: Python standard library policy core and local demo; no external model needed for deterministic demo. Package availability, model credentials, browser demo, security scanner availability and internet at venue have not been checked. No credential values read or persisted.

## Demo and event build plan

90-second demo: explain the synthetic secret and agent tools; show a normal allowed read; show a malicious document causing a proposed external send and its block; show a legitimate message paused for human approval and executed once; finish with redacted audit and security scan results. Say explicitly whether the agent and tools are simulated.

Proposed event allocation, not organizer-approved: 18:00–18:20 policy and mocks; 18:20–19:10 interception and confirmation; 19:10–19:40 acceptance tests; 19:40–20:00 code/dependency scans and fixes; 20:00–20:15 rehearse and package; 20:15–20:30 submit using organizer instructions and preserve receipt. Cut live-model integration first if time is short.

Draft description: “Agent Permission Firewall checks tool actions before execution, blocks destinations outside policy, and requires action-bound human approval for messages. The demo shows a prompt-injected document causing an attempted data leak, its prevention, and a legitimate action completing with an auditable decision.” Use only after behavior is implemented and verified.

## Readiness ledger

| Item | Evidence / status |
|---|---|
| Registration | Verified historical confirmation, 3 October; not final project submission |
| Specification/scenarios/test plan | This document, prepared 14 October |
| Runnable artifact / commit | None; no project code written in this pass |
| Demo URL / public repository | None |
| License | Not selected; proposed MIT subject to owner decision and dependency review |
| Video | Not recorded; requirement not published |
| Description | Draft above; not a verified product claim |
| Security scan | Pending code and tooling |
| Submission receipt | None; submission not performed |
| Next verifiable milestone | Implement and pass the acceptance cases during the event, or earlier only after prebuilt-code rules are confirmed; retain test and scan evidence |

Blockers: prebuilt-code eligibility and final venue are owned by organizers; Innokenty owns approval for any outreach. Public-page recheck is available without outreach. Submission format and judging details remain unpublished. Proposed preparation checkpoint: 20 October; no agreed internal deadline established.
