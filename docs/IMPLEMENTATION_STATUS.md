> Проверка после аудита 22.10.2026: приведённые ниже результаты относятся к
> предыдущей версии с кастомным seccomp, а не к исправленному рабочему дереву.
> Сейчас: 38 integration PASS, mypy PASS; 2 browser FAIL при запуске Chromium
> (`No usable sandbox`) со стандартной изоляцией Docker. Чистая пересборка
> ещё не подтверждена. Русские документы восстановлены, DESIGN/PRODUCT удалены.
> Полный зелёный прогон и UAT не заявляются. Актуальные команды — в README.

# Implementation status · 2026-10-22

Implemented synthetic prototype according to the approved architecture; owner UAT is pending.

- Three-panel owner UI, separate authenticated owner/A/B/C credentials, cookie CSRF/origin checks.
- Immutable snapshots, signed root/child grants, signed executor actions and receiver receipts.
- SQLite WAL transactions serialize revoke/reserve and enforce one root-wide slot across children.
- Separate receiver container, database and private signing key. Shared volume contains public keys only.
- Stable receiver idempotency; uncertain results retain budget. Read-only reconciliation; no send retry.
- Startup recovery for unfinished reservations; signed ledger and independent ZIP/CLI verifier.
- Non-root Tower Docker runtime, resource limits, loopback access and sandboxed browser tests.

## Executed evidence

39 tests passed in the final application image: 37 integration cases and 2 real Chromium browser flows.
Production/CLI Ruff checks and strict mypy passed (22 modules); no explicit Any in those modules.
Pinned cryptography 50.0.2 replaced the initially vulnerable 48.0.1. The lock-file audit reports
no known vulnerabilities. This is a point-in-time audit, not a guarantee against future findings.

Real HTTP app → receiver delivery confirmed one inbox item; a second dispatch was blocked.
A separate CLI process verified the evidence pack using independently provisioned fingerprints.
Test fixtures verify restart/recovery, exact expiry, concurrency, unavailable storage, lost responses,
fake signatures/receipts, missing trust pins, modified/deleted archive content and CSRF denial.

Browser captures at 1280, 768 and 390px showed no horizontal overflow. Fresh screenshot/source
review disposition: ship, no required material UI fixes. Detector was degraded to regex because
parser dependencies were unavailable; this does not establish computed accessibility compliance.
The reviewer did not independently exercise keyboard behavior or every visual state.

## Limits and acceptance

S01–S32 remain the acceptance catalogue. The automated checks cover their main invariants,
not every browser variant or adversarial permutation. Keyboard test is a basic focus check;
full keyboard traversal and U01–U05 still need owner acceptance. No claim of completed TDPD,
legal signatures, production authorization, live LLM evaluation or contest submission.

Initial RED collection failed on absent app.main. The runnable acceptance suite then exposed
actual WAL restart and login Origin defects; those were fixed and rechecked. Do not interpret
that initial collection error as proof that every planned scenario had a behavioral RED run.

Running services use only project-scoped synthetic volumes. No production credentials or
other project runtimes were used.

The final app and receiver were recreated and then explicitly restarted together.
Both post-recreation and post-restart read-only smoke checks retained exactly one
message for the tested attempt, blocked another dispatch and passed offline verification.
The live smoke waits for app/receiver readiness using GET requests only; mutations
are never retried. Local access uses an SSH tunnel at port 18080.

English-language update: application templates, feedback, date formatting, browser
acceptance locators, README, active architecture/specification/scenario documents and
design references are in English. The 39-test suite, Ruff and strict mypy passed again
for this version. Historical research and chat evidence retain their original language.

Named synthetic case update: Harbor Robotics → Northstar Logistics, HAR-SEC-042,
Maya/Atlas/Courier/Relay/Anna. Human-readable event labels preserve signed machine codes.
New report IDs coexist with unchanged legacy document bytes. The combined refactor and
scenario passed 38 integration tests and strict mypy (25 modules) in an isolated Docker
container. Browser e2e tests were not rerun successfully after removal of the browser
seccomp profile: standard Docker on this Tower does not currently permit Chromium's
sandbox. No sandbox protection was disabled. Live rendering requires separate inspection.
