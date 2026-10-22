# Agent Delegation Ledger · AI Security Hackathon

An owner authorizes orchestrator A to deliver an exact synthetic document. A delegates
narrower authority to B or C. Both executors share **one root-wide dispatch slot**.
An independent receiver stores the document in Anna's inbox and signs a receipt.
The ledger links authorizations, attempts and outcomes; a standalone CLI verifies exports.

Python 3.12 / FastAPI / Jinja2 / SQLite WAL / Ed25519 / RFC 8785.
See the [architecture contract](docs/ARCHITECTURE_CONTRACT.md),
[rules R01–R17](docs/AGENT_DELEGATION_TDPD_SPEC_v0.1.md), and
[scenarios S01–S32 and UAT](docs/AGENT_DELEGATION_SCENARIOS_v0.1.md).

## Demonstration boundary

Synthetic data and deterministic scripted agents only. No live LLM, real external
messages, payments, blockchain or legally binding personal signature.
Delivery is confirmed only by a valid receiver signature. Unknown outcomes remain
uncertain; there is no automatic redispatch or release of a reserved slot.
Revocation blocks new reservations without promising cancellation of a started dispatch.

Archive verification establishes integrity relative to independently obtained trusted
fingerprints. It does not establish human readership, truth of every assertion, or
history completeness without an independent checkpoint. Compromise of the trusted
operator or keys is outside this MVP's guarantee. The first receiver key is pinned
over the trusted private Compose network; unexpected key rotation is not accepted.

## Run on Tower

All project installation, builds, tests and browser automation run **inside Docker on
tower-linux**. Mac Docker is not required. Run these commands in the project directory
on Tower. Copy `.env.example` to `.env`, confirm `LEDGER_SUBNET` is unused, and set
`LEDGER_ORIGIN` to the exact browser origin. For an SSH forward to Mac port 18080 use
`LEDGER_ORIGIN=http://127.0.0.1:18080`. The remote port defaults to 8080, loopback only.

```sh
docker compose --env-file .env -f docker/docker-compose.yml build tests
docker compose --env-file .env -f docker/docker-compose.yml run --rm tests
docker compose --env-file .env -f docker/docker-compose.yml up -d --no-build app receiver
docker compose --env-file .env -f docker/docker-compose.yml ps
docker compose --env-file .env -f docker/docker-compose.yml logs --tail=80 app receiver
```

On the Mac, open the SSH forward:

```sh
ssh -N -L 18080:127.0.0.1:8080 tower-linux
```

Open `http://127.0.0.1:18080/login`. Credentials are provisioned on first start in
`/data/credentials.json` (mode 0600), never in source or the image. The owner can read
their credential privately with this command; do not copy its output into shared logs:

```sh
docker compose --env-file .env -f docker/docker-compose.yml exec -T app python -c \
  'import json; print(json.load(open("/data/credentials.json"))["owner"])'
```

Run one app worker. Do not run independent app processes against the same app-data.
Unfinished reservations recover as uncertain on startup. Keys, SQLite state and
receipts persist in separate app-data / receiver-data volumes. The receiver sees
public-data only, never app-data; the app cannot access the receiver's signing key.

Containers use non-root UID 10001, amd64, cap_drop ALL, no-new-privileges, CPU/RAM/PID/log
limits and a project-specific network. Browser tests retain Chromium's sandbox.
`docker/browser-seccomp.json` derives from the
[official Playwright profile](https://github.com/microsoft/playwright/blob/main/utils/docker/seccomp_profile.json):
namespace syscalls and chroot inside a user namespace; clone3 returns ENOSYS for glibc
fallback. No host capabilities are added; host AppArmor and sysctl settings are unchanged.

## Verification

```sh
docker compose --env-file .env -f docker/docker-compose.yml run --rm tests pytest -q -p no:cacheprovider
docker compose --env-file .env -f docker/docker-compose.yml run --rm tests ruff check --no-cache src cli
docker compose --env-file .env -f docker/docker-compose.yml run --rm tests mypy --cache-dir /tmp/mypy src cli
docker compose --env-file .env -f docker/docker-compose.yml run --rm tests pip-audit --disable-pip --no-deps -r requirements.lock --cache-dir /tmp/audit
```

Dependencies are pinned in `requirements.lock`; the image installs them from scratch.
Two browser e2e flows exercise real HTTP/UI with separate app and receiver SQLite
fixtures. Integration checks cover adversarial input, concurrency, expiry, revocation,
replay, lost responses, storage failures, restart, forged signatures and export tampering.
Fault injection and a controlled clock exist only in Python fixtures, never HTTP APIs.
Automated coverage does not replace manual acceptance of every S01–S32 variant.

For a real synthetic inter-container smoke run (creates one authorization and delivery):

```sh
docker compose --env-file .env -f docker/docker-compose.yml exec -T app python -m cli.smoke --url http://127.0.0.1:8080
docker compose --env-file .env -f docker/docker-compose.yml restart app receiver
docker compose --env-file .env -f docker/docker-compose.yml exec -T app python -m cli.smoke --url http://127.0.0.1:8080 --verify-only
```

The smoke run waits using read-only readiness probes; mutations are never retried.
It saves `/data/evidence.zip` and independently provisioned `/data/trust.json`.
For manual verification, download evidence.zip in the UI and obtain trusted fingerprints
separately from the operator. Never derive trust from the archive being checked.
The CLI requires installed dependencies and supplied files, but no running web/receiver:

```sh
python -m cli.verify evidence.zip --trust trust.json
```

On Tower, use `docker compose run --rm` with a read-only mount containing the archive
and trust file. Valid evidence returns exit 0; invalid evidence returns exit 1.

## Stop and recover

```sh
docker compose --env-file .env -f docker/docker-compose.yml stop app receiver
```

Never use `down -v` or prune. Before replacing an existing runtime, stop writes and
preserve app-data, receiver-data, public-data and the previous image ID. Roll back the
image and a **consistent set** of volumes. Never reset the budget or receiver inbox
independently. Data deletion is not a normal UI operation.

## Manual acceptance and source materials

U01–U05 still require owner acceptance: clarity of approval, allowed/blocked flows,
revocation and uncertainty, evidence verification, and the value of the overall task.
TDPD / Test-Driven Product Development is Innokenty Bodrov's method. No license has
been selected and no competition submission has been made.

The application, tests and current implementation documentation are in English.
Original research notes and chat exports remain historical source evidence in their
original language; they do not authorize new actions or supersede the approved contract.
