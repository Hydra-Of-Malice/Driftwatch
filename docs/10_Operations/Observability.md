# Observability

[← Documentation index](../README.md) · [← Database Design § audit_events](../04_Data/Database_Design.md)

---

> **Summary.** The system has one genuinely good observability primitive — an append-only audit ledger that records every machine and human decision — and almost nothing else. No metrics, no tracing, no structured logs, no health endpoint. What follows is what an operator can and cannot actually see, not an aspirational monitoring stack.

## 1. What exists: the audit ledger

Evidence: `db.py :: audit`, table `audit_events`

Every state transition, decision, and side effect of consequence writes one row via `db.audit(actor, action, refs, payload)`:

```python
def audit(actor, action, refs=None, payload=None) -> int:
    """Append-only ledger write. Everything of consequence goes through here."""
```

| Column | Meaning |
|---|---|
| `actor` | `"machine"` \| `"human"` \| `"scheduler"` |
| `action` | Dotted event name, e.g. `heal.auto_approved`, `run.published`, `alert.slack_failed` |
| `refs` | JSON — the entity IDs involved (`{"source": ..., "heal_event": ...}`) |
| `payload` | JSON — event-specific detail (confidence, version transition, error text) |
| `created_at` | ISO-8601 UTC timestamp |

Exposed via `GET /api/ledger` (default `LIMIT 200`, newest first) and rendered in the SPA's Ledger view. Actions observed in the codebase span the full pipeline: `run.started`, `run.<state>` for every `RunState` transition, `heal.requested`, `heal.preview_verified`, `heal.auto_approved`, `heal.auto_rejected`, `heal.escalated_to_review`, `heal.human_approved`, `heal.human_rejected`, `heal.rerun_verified`, `heal.rerun_failed`, `alert.slack_failed`, `scheduler.tick.run_due`, `scheduler.tick.error`, `source.onboarded`, `demo.variant_set`.

**This is a real strength.** The ledger is the system's actual audit trail — not a log file that could be rotated away, but application data queryable through the same API as everything else, and it is what makes claims like "every machine decision is traceable" checkable rather than asserted. See [Database Design § audit_events](../04_Data/Database_Design.md).

**Its limits are structural, not incidental:**
- **It is not authenticated as a source of truth about who acted.** `decided_by: "human"` is written for any caller of `POST /api/review/<id>`, and that endpoint requires no authentication — the ledger can record a claim about a human decision-maker it has no way to verify. See [Security Architecture](../06_Security/Security_Architecture.md) and [GAP-01](../02_Requirements/Requirements_Gap_Analysis.md#gap-01--no-authentication-on-any-endpoint).
- **State transitions and their audit rows are written in separate statements, not one transaction.** `pipeline/runner.py :: _set_state` calls `db.update(...)` then `db.audit(...)` as two sequential calls. A crash between them leaves a run's `state` column ahead of what the ledger shows — a small window, never observed to matter, but real ([Threat Model T-11](../06_Security/Threat_Model.md)).
- **Nothing prevents mutation at the database level.** "Append-only" is a convention followed by application code (`insert`, never `update`/`delete` against `audit_events`), not a database constraint, trigger, or permission. Anyone with file access to `driftwatch.db` can edit history. **NOT IMPLEMENTED** at the storage layer.
- **Unbounded growth, no retention policy** — see [Database Design § Data volume and retention](../04_Data/Database_Design.md).

## 2. What operators can see today

| Surface | Route | Shows |
|---|---|---|
| Ledger | `GET /api/ledger` | Last 200 audit events, raw |
| Stats | `GET /api/stats` | Source count, run count, credits spent, event counts by class, heal MTTR mean, heal verification pass rate, quarantined-snapshot count |
| Alerts feed | `GET /api/alerts` | Last 50 alerts (in-app + Slack payloads) |
| Timeline | `GET /api/sources/<id>/timeline` | Per-source runs, events, heals |
| Review queue | `GET /api/review` | Heals awaiting a human decision |

Everything above is a database read through the same JSON API the SPA uses — there is no separate operator surface, no admin panel, and no CLI inspection tool beyond direct SQLite access.

## 3. What does not exist

Stated plainly:

| Capability | Status |
|---|---|
| Structured application logging (JSON logs, log levels, correlation IDs) | **NOT IMPLEMENTED** — only Flask's default per-request access log to stdout |
| Metrics endpoint (Prometheus `/metrics` or equivalent) | **NOT IMPLEMENTED** |
| Distributed tracing (OpenTelemetry spans across a run's diagnose→heal→verify chain) | **NOT IMPLEMENTED** |
| Health / readiness endpoint (`/healthz`, `/readyz`) | **NOT IMPLEMENTED** — liveness can only be inferred by whether `GET /api/stats` responds |
| Alerting on the *system itself* (process down, scheduler stalled, DB unreachable) | **NOT IMPLEMENTED** — the product alerts on *drift*, never on its own health |
| Dashboards (Grafana or similar) | **NOT IMPLEMENTED** — the SPA's own charts are the only visualisation, and they read live from the API, not from a metrics backend |
| Log aggregation / shipping | **NOT IMPLEMENTED** — nothing leaves the single process |
| Request correlation across the pipeline's multiple internal calls | **NOT IMPLEMENTED** — a run's audit rows share `refs.run`, which serves the same purpose informally, but there is no formal trace/span ID |

## 4. Blind spots this creates

- **A stalled or crashed scheduler is invisible.** The daemon thread's per-tick `try/except` ([`scheduler.py`](../03_Architecture/ADRs/README.md#adr-010--in-process-thread-scheduler-the-runs-table-is-the-queue)) writes `scheduler.tick.error` to the ledger on failure, but nothing pages anyone, and if the *thread itself* dies (rather than one tick's body raising), there is no heartbeat to notice — a source can silently stop being watched, discoverable only by an operator manually noticing stale `runs.started_at` timestamps.
- **Anthropic degradation is silent** — see [Model Limitations § 5](../09_AI_ML/Model_Limitations.md#5-anthropic-degradation-is-invisible-in-the-audit-ledger).
- **No process-level resource visibility** — CPU, memory, open file descriptors (relevant given SQLite's WAL-mode file handles — see [ADR-002](../03_Architecture/ADRs/README.md#adr-002--sqlite-as-the-only-datastore)) are not surfaced anywhere.
- ~~**The `heal_mttr_seconds` stat mixes seeded and measured values with no visible marker**~~ **RESOLVED 2026-08-22.** `heal_events` gained a real `seeded` column; `/api/stats` now excludes `seeded = 1` from `heal_mttr_seconds` and reports `heal_mttr_measured_count` alongside it, so `0` is now visible and distinguishable from "no real heal has run yet." The UI shows "no measured heal yet" instead of a number until that happens. See [GAP-18](../02_Requirements/Requirements_Gap_Analysis.md) and [Performance Validation](../07_Testing/Performance_Validation.md#what-is-not-measured).

## 5. RECOMMENDED

Ranked by value against effort:

1. **`GET /healthz`** returning process-up + DB-reachable — 15 min. Closes the biggest remaining gap for basically free. **Still open.**
2. ~~**A `"seeded"` flag surfaced from `/api/stats`**, or a separate `heal_mttr_seconds_measured` computed with seeded rows excluded~~ — **Done 2026-08-22**, see above.
3. **A scheduler heartbeat row** (`audit("scheduler", "tick.alive", ...)` on every tick, or a last-tick timestamp exposed via `/api/stats`) — 30 min. Turns "the scheduler silently stopped" into an observable condition. **Still open.**
4. **Structured logging** (`structlog` or stdlib `logging` with a JSON formatter) alongside the ledger, for operational events the ledger doesn't cover (startup, config load, request-level errors) — 2 h.
5. **A `/metrics` endpoint** once there is an actual operator (today, the ledger and stats endpoints cover the product's own needs; Prometheus-style metrics matter once something external is scraping this system) — deferred until [Deployment Architecture § Recommended production shape](../08_Deployment/Deployment_Architecture.md#9-recommended--production-deployment-shape) exists.

---

**Next:** [Reliability & Failure Design](Reliability_and_Failure_Design.md) · [Judge Evaluation](../11_Assessment/Judge_Evaluation.md)
