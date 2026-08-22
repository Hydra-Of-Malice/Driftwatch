# Reliability & Failure Design

[← Documentation index](../README.md) · [← HLD § Communication](../03_Architecture/HLD.md#9-communication)

---

> **Summary.** Three failure-isolation mechanisms exist and are real (try/except boundaries that keep one failure from taking down the process). None of the three has ever been exercised by inducing the failure it claims to survive. No retry, backoff, circuit breaker, or timeout tuning exists anywhere in the system, and there is no disaster-recovery capability at all. This document states failure behaviour per dependency, not aspiration.

## 1. Per-dependency failure behaviour

| Dependency | What happens if it fails | Mechanism | Status |
|---|---|---|---|
| SQLite (the only datastore) | A query hitting write contention retries for up to 5s (`busy_timeout=5000`, added 2026-08-22) before raising `database is locked`; no connection pool exhaustion handling beyond that | `db.py :: _connect` sets `journal_mode=WAL`, `busy_timeout=5000`, and `foreign_keys=ON` | **IMPLEMENTED** (2026-08-22) — see [ADR-002](../03_Architecture/ADRs/README.md#adr-002--sqlite-as-the-only-datastore) |
| Bright Data (replay) | N/A — no network call, fixtures either exist or `ReplayClient._truth` raises `BrightDataError` for a missing fixture | Deterministic; a missing fixture is a build error, not a runtime failure mode | — |
| Bright Data (live) | `LiveClient._cli` raises `BrightDataError` on any non-zero CLI exit code or non-JSON stdout | `subprocess.run` with a 900 s timeout; **no retry on any failure**, including a transient 503 | **NOT IMPLEMENTED** — `REL-005` in the [SRS](../02_Requirements/SRS.md); the pre-kickoff CLI spike documented in `SCRAPER_STUDIO.md` observed repeated 503s in practice |
| Anthropic | Any exception (network, auth, timeout, response-shape) is caught inside `_complete`; caller falls back to `HeuristicProvider` | Blanket `except Exception: return None` → `super()` call | **IMPLEMENTED** (the fallback exists) / **UNVALIDATED** (never tested by inducing failure) — `REL-003` |
| Slack webhook | `httpx.post` exception is caught; the in-app alert (already written) is unaffected | `except Exception as exc: db.audit(...)` | **IMPLEMENTED** / **UNVALIDATED** — `REL-001` |
| A single source's run | An unhandled exception inside `run_source` propagates to the scheduler's per-tick `try/except`, which logs it to the ledger and continues to the next tick; other sources in the same tick that already ran are unaffected, but if the failure occurs while iterating `_due_sources()`, sources later in that same tick's list are skipped until the next tick (30 s later) | `scheduler.py :: start` wraps the whole tick body, not each source individually | **IMPLEMENTED** / **UNVALIDATED** — `REL-002`. Note the granularity: the try/except is around the *tick*, not around each `run_source` call, so one source's exception does skip its tick-mates rather than being fully isolated per-source |
| Flask process crash | Everything stops — the HTTP server and the scheduler share one process | None — no supervisor, no restart | **NOT IMPLEMENTED**, see [Deployment Architecture § Process model](../08_Deployment/Deployment_Architecture.md#6-process-model) |
| Filesystem (contracts, fixtures) | A missing contract YAML raises on `load_spec`; there is no default/fallback contract | None | Missing-file is effectively a configuration error, not a handled runtime case — see [Model Limitations § 8](../09_AI_ML/Model_Limitations.md#8-onboarding-a-genuinely-new-source-does-not-currently-produce-a-runnable-pipeline) |
| A rejected/failed heal | The affected source is quarantined on its last good version; new extractions for that source stop publishing until the contract or template is fixed out-of-band | Version pinning ([ADR-008](../03_Architecture/ADRs/README.md#adr-008--version-pinning-as-the-rollback-mechanism)) | **VALIDATED** — `REL-004`, `test_healing.py` |

## 2. Retry, backoff, timeout, circuit breaker inventory

| Pattern | Present anywhere? |
|---|---|
| Retry with backoff on transient external failure | **NOT IMPLEMENTED** anywhere — not for Bright Data, not for Anthropic, not for Slack |
| The heal loop's "retry once with a refined prompt" | This is a **quality** retry (a different prompt after a rejected verification), not a **failure** retry (the same call after a transient error). It does not apply if the *call itself* fails — only if the call succeeds and the result fails verification |
| Circuit breaker | **NOT IMPLEMENTED** |
| Configurable per-call timeout | Present but fixed, not tunable at runtime: Bright Data CLI 900 s, Anthropic 30 s, Slack 10 s — all hardcoded constants, not `Settings` fields |
| Bulkheading (isolating one source's failure from another's) | **Partial** — see the scheduler tick granularity note in §1 |
| Graceful degradation | **The one place this is done well**: Anthropic and Slack are both fully optional, and their absence or failure degrades the *feature* (prose quality, one alert channel) without degrading the *pipeline*. This is a real, structural property — see [ADR-006](../03_Architecture/ADRs/README.md#adr-006--llm-confined-to-prose-behind-a-protocol-defaulting-off) |
| Dead-letter queue | **N/A** — there is no queue; the `runs` table itself is the closest analogue ([ADR-010](../03_Architecture/ADRs/README.md#adr-010--in-process-thread-scheduler-the-runs-table-is-the-queue)), and a failed run simply has `state` stuck at a non-terminal value with no retry sweep to pick it back up |

## 3. The untested-reliability finding

`REL-001`, `REL-002`, and `REL-003` are all implemented as `try`/`except` blocks that are never triggered by any test in the 23-test suite — confirmed in the [Requirements Traceability Matrix](../02_Requirements/Requirements_Traceability_Matrix.md#untested-implemented-requirements--ranked) and flagged as [Risk R-09](../06_Security/Risk_Register.md) (**HIGH**, because "the handler itself can be wrong" is a classic failure mode — an `except` clause with a typo in the exception type, or one that swallows a differently-shaped error than intended, looks identical to a correct one until the failure it's meant to catch actually occurs). This is the single most concrete, cheap-to-close reliability gap in the system: three targeted tests (mock a Slack POST to raise, mock `run_source` to raise inside a tick, mock `AnthropicProvider._complete` to raise) would validate all three claims directly. See [Gap Report](../11_Assessment/Engineering_Gap_Report.md).

## 4. Concurrency and single points of failure

- **SQLite is a single-writer store** — the Flask request thread and the scheduler's daemon thread can still contend under simultaneous writes; `PRAGMA busy_timeout=5000` (added 2026-08-22) now makes a collision wait and retry for up to 5s instead of raising `database is locked` immediately, which meaningfully reduces but does not eliminate the risk under real concurrent load. It remains a single point of failure at higher write volumes than this build has ever been tested at. See [ADR-002](../03_Architecture/ADRs/README.md#adr-002--sqlite-as-the-only-datastore).
- **The scheduler is a single point of failure for "sources are being watched" as a property** — it is one daemon thread in one process with no leader election, no supervision, and no catch-up policy if the process is down when a source's interval elapses (the interval is simply skipped; there is no missed-run backfill).
- **No horizontal redundancy anywhere** — running two instances of the process would double-schedule every source rather than provide failover, because there is no coordination between instances. See [Deployment Architecture § Process model](../08_Deployment/Deployment_Architecture.md#6-process-model).

## Disaster recovery

**NOT IMPLEMENTED.** Restated from [Database Design § Backup and recovery](../04_Data/Database_Design.md#backup-and-recovery), which is the authoritative source for this claim:

- No backup script, no scheduled `VACUUM INTO`, no snapshot mechanism.
- No documented restore procedure. The database is a single file (`driftwatch.db`, plus its `-wal`/`-shm` companions in WAL mode); recovery in practice means a file-system-level copy of a stopped process's data directory.
- No off-machine replication of any kind.
- Configuration (`.env`) and contracts (`fixtures/contracts/*.yaml`) are recoverable only insofar as they live in git or on the operator's disk — they are not part of any backup procedure either, formal or informal.
- **RPO (Recovery Point Objective) and RTO (Recovery Time Objective) are not established.** No target exists to measure against.

**RECOMMENDED**, none implemented:

| # | Recommendation | Effort |
|---|---|---|
| 1 | A `sqlite3 driftwatch.db "VACUUM INTO 'backup.db'"` cron/scheduled task, run outside the application process | 30 min |
| 2 | Define an RPO target (e.g. 24 h, given the append-only ledger's importance) and an RTO target (e.g. "restart from last backup + reseed contracts from git," which for this system's data volume is minutes) | 1 h to write down, near-zero to implement given #1 |
| 3 | Once Postgres replaces SQLite ([Deployment Architecture § 9](../08_Deployment/Deployment_Architecture.md#9-recommended--production-deployment-shape)), standard point-in-time recovery (WAL archiving) becomes available for free | Depends on the Postgres migration |
| 4 | Contracts and `.env` should be backed up alongside the database — they are currently a separate, undocumented recovery dependency | 30 min to document, more to automate |

---

**Next:** [Judge Evaluation](../11_Assessment/Judge_Evaluation.md) · [Production Readiness](../11_Assessment/Production_Readiness.md)
