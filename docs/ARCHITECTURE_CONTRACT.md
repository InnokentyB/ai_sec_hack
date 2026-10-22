# Architecture Contract · Agent Delegation Ledger

Approved 22 October 2026. Input and Surface Gates: APPROVED.
Implementation is authorized by the owner's current request. Human UAT remains pending.

## Stack

| Component | Decision |
|---|---|
| Language | Python 3.12, explicit type annotations, strict mypy |
| HTTP | FastAPI, Uvicorn, strict Pydantic v2 proposal validation |
| UI | Server-rendered Jinja2 HTML, vanilla CSS and JavaScript; English |
| Persistence | SQLite WAL; BEGIN IMMEDIATE serializes root-wide reservations and revocation |
| Cryptography | Ed25519 through cryptography, separate role keys |
| Canonicalization | RFC 8785 JSON Canonicalization Scheme |
| Evidence | Signed ZIP manifest, independently trusted fingerprints, standalone CLI |
| Verification | pytest, integration tests, sandboxed Playwright Chromium browser tests |
| Runtime | Tower Docker, Linux amd64, non-root, loopback access |

## Repository layout

```text
src/app/                FastAPI factory, protected routes, templates and static assets
src/core/               Strict proposal models, canonicalization and role-separated signing
src/services/           Authorization, storage, ledger, dispatch and evidence export
src/receiver/           Independent synthetic inbox service, storage and signing key
src/simulated_agents/   Deterministic orchestrator and executor proposals
cli/verify.py           Offline archive verifier
cli/smoke.py            Running-container synthetic delivery and restart checks
tests/integration/      Authorization, races, failures, recovery and tampering
tests/e2e/              Real browser acceptance flows
docker/                 Reviewed Dockerfile, Compose and browser seccomp profile
```

The root layout replaces the earlier proposed nested `work/...` directory.

## ADR-01: Roles and service isolation

Roles: owner O, orchestrator A, executors B/C, Receiver/Anna and Ledger.
Authorization Service, A, B, C, Receiver and Ledger have separate Ed25519 keys.
The authorization service attests to owner confirmation; this is not the owner's personal signature.
Principal identity comes from authenticated credentials, never editable `actor_id` input.
Owner access uses a local demo session, with CSRF and exact-origin checks on cookie mutations.

Receiver has its own container, SQLite file and private receipt key. App and receiver
share only public-key provisioning data. Neither service receives the other's private
key directory. No production credentials or external document delivery are involved.
The first receiver public key is pinned through the trusted private Compose network.
Unexpected key rotation fails verification rather than silently replacing trust.

## ADR-02: Atomic shared budget and crash recovery

B and C may each hold a valid child of one root with max_uses=1. They share one slot.
Inside BEGIN IMMEDIATE: validate signatures, scope, expiry and revocation; reject an
already occupied slot; persist the attempt, reservation and signed event; commit.
Only then contact the receiver. Revocation uses the same serialization boundary.

No OS lock files or indefinite mutexes. A crash rolls back open SQLite transactions.
On restart, unfinished reserved/dispatching attempts become uncertain. Their slots remain
occupied; only read-only receipt reconciliation is allowed. This conservative treatment
is the explicitly approved recovery strategy, not permission for an automatic resend.

## ADR-03: Signed canonical evidence

Events include case ID, sequence, previous hash, actor, server time, payload and its digest.

```text
payload_digest = SHA256(RFC8785(payload))
current_hash = SHA256(previous_hash || payload_digest || decimal(sequence))
```

The signed event covers the complete canonical event, including linkage and hashes.
Root grants are signed by Authorization Service, children by A, actions by B/C,
receipts by Receiver and events by Ledger.

`evidence.zip` contains:

- `manifest.json`: schema, member hashes, event count, final hash; Authorization signature.
- `snapshot.json`: immutable synthetic document snapshots.
- `grants.json`: signed root and child grants.
- `events.jsonl`: ordered signed evidence chain.
- `receipt.json`: signed receiver receipts.
- `attempts.json`: execution states and signed executor actions.
- `public.json`: public keys only; these never establish their own trust.

`cli/verify.py` accepts trusted role fingerprints independently of the archive and checks
member hashes, signatures, chain continuity, checkpoint, grant scope and receipt linkage.
It runs without the web or receiver service. It does not establish legal authority or
history completeness without an independent checkpoint.

## ADR-04: Deterministic agents

ScriptedDelegationAgent behavior is implemented by local, reproducible proposals.
No external LLM API, provider credentials or model-evaluation claim. Scripted agents
never simulate owner consent. The UI labels the simulation explicitly.

## ADR-05: Docker execution boundary

All project installation, builds, tests and browser automation on Tower run in Docker.
Linux amd64; app UID 10001; no privileged mode, host networking, Docker socket mount,
host-root mount or added host capabilities. Preserve Chromium sandbox protections.
Default app port: 127.0.0.1:8080. Reach it through SSH forwarding.

App/receiver limits: 1 CPU, 512 MiB, 100 PIDs, bounded JSON logs. Browser test limits are
larger (2 GiB, 256 PIDs, 512 MiB shared memory). Temporary jobs use `run --rm`.
Use project-specific networks/volumes; stop services without deleting volumes.
See README and .env.example for reviewed commands and environment settings.

## ADR-06: Uncertain outcomes

If dispatch was reserved and its result cannot be established, the attempt becomes
uncertain and the root slot stays occupied. A missing receipt is not proof of no delivery.
Reconciliation is a read-only lookup by stable idempotency key. Only a valid matching
receipt changes the attempt to confirmed. No automatic retry, budget reset or replacement root.

## Surface contract

A three-panel owner interface:

1. Permissions: document/version/hash preview, recipient, delegation toggle, 1–10 minute
   expiry (default 5), explicit approval, revocation and scripted agent actions.
2. Event chain: signed ordered history, allowed/blocked/uncertain outcomes, reconciliation
   and evidence download.
3. Synthetic inbox: actual independent receiver records, document hash and signed receipt.

Show DEMO / SYNTHETIC, distinguish authorization from delivery, and explain uncertainty
and signature limitations. Disable the submitted control while pending. Preserve state
after reload. Use English labels, visible keyboard focus and textual verdicts.
Desktop target: 1280×800. No horizontal overflow at 768px; mobile stacks the panels.

## Gates

Input and Surface: approved. Implementation and automated checks: see
[implementation status](IMPLEMENTATION_STATUS.md). Human U01–U05 acceptance is separate
and remains pending until the owner explicitly accepts the working result.
