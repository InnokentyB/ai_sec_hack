# Operational and Architecture Guardrails for AI Agents v1.0

Workspace rules for the bounded Agent Delegation Ledger MVP.
The approved architecture contract resolves platform-specific implementation details.

## 1. YAGNI and scope

BLOCK work outside the current approved MVP. No custom hypervisors, cgroup/namespace
emulators, socket parsers or speculative infrastructure. Build one delegation depth
(owner → orchestrator → executor) and one synthetic document-delivery action.
Do not generate bureaucratic specifications or fabricated verification reports.
Documentation must describe actual behavior or explicitly labeled requirements.
Use standard platform tools and maintained libraries.

## 2. Deadlock and crash recovery

Every lock, lease or atomic budget needs a recovery strategy if its owning process dies.
For process-owned locks, check whether the owner still exists and recover stale ownership.
Never leave an unbounded orphan lock. The approved SQLite strategy uses bounded
transactions and startup recovery of unfinished reservations as uncertain. Preserve the
slot and allow read-only receipt reconciliation; do not automatically resend an effect.

## 3. Clean-build test contract

Tests must not depend on pre-existing dist/build artifacts. Use a direct runtime or an
explicit clean build-and-test command. Before changing installation scripts, service
configuration or Dockerfiles, inspect relevant existing source-contract tests.
Infrastructure errors are not evidence of a behavioral RED phase.

## 4. Resource hygiene

Release or cancel stream readers, handles and sockets in guaranteed finally/cleanup
blocks. Do not copy unused imports. The unused-import lint result must be clean.

## 5. Readability

No minified one-line code to bypass line limits. Use standard formatting, one statement
per line, clear names and explicit type annotations; no Any escape hatches.
Document public functions and classes with docstrings. Prefer project-native Python
formatting rather than applying TypeScript indentation conventions to Python.

## 6. Environment and infrastructure safety

Never hardcode external endpoints, secrets or host addresses in executable code.
Parameterize endpoints with arguments/environment variables, document new settings in
.env.example, and preserve the Tower container-only execution policy in AGENTS.md.
Never copy production credentials into synthetic fixtures, source or container images.
