# Scope

[← Documentation index](../README.md)

---

## In scope — built and verifiable

| Capability | Status | Evidence |
|---|---|---|
| Four-gate semantic contract evaluation | **VALIDATED** | `contracts/engine.py` |
| Weighted confidence score with partial credit | **IMPLEMENTED** | `GATE_WEIGHTS`, `_outcome()` |
| Five-class drift taxonomy with precedence ordering | **VALIDATED** | `drift/classifier.py` |
| Entity-resolved diffing (stable across reordering) | **VALIDATED** | `drift/differ.py` |
| Autonomous heal: diagnose → compose → heal → verify → decide | **VALIDATED (replay)** | `healing/` |
| Three-band approval policy | **VALIDATED** | `healing/orchestrator.py` |
| Version pinning as rollback | **IMPLEMENTED** | `scrapers.active_version` advances only after verified re-run |
| Quarantine — unvalidated data never served | **VALIDATED** | `_last_good()` filters `quarantined = 0` |
| Impact: literal call-site scanning | **IMPLEMENTED** | `impact/scanner.py` |
| Impact: cost delta for price and unit-flip changes | **VALIDATED** | `impact/cost.py` |
| Zero-noise alerting (classes 0–2 silent) | **VALIDATED** | `alerts.py` |
| In-app alerts; optional Slack | **IMPL / UNVALIDATED** | `alerts.py` |
| Append-only audit ledger | **IMPLEMENTED** | `db.py :: audit` |
| In-process scheduler | **IMPLEMENTED** | `scheduler.py` |
| 19-route JSON API + zero-build SPA | **IMPLEMENTED** | `api/app.py`, `frontend/` |
| Replay client with controlled mirror site | **VALIDATED** | `brightdata/replay.py`, `mirror/` |
| Live client wrapping the official CLI | **UNVALIDATED** | `brightdata/live.py` |

## Out of scope — deliberate non-goals

| Excluded | Reasoning |
|---|---|
| Proxy rotation, CAPTCHA solving, browser automation | Bright Data's platform responsibility; duplicating it would be the wrong seam |
| Generic scraping framework | DriftWatch orchestrates Scraper Studio; it is not a competitor to it |
| AST-level call-graph impact analysis | Stated v1 non-goal in `impact/scanner.py`; literal entity matching is the chosen depth |
| Multi-tenancy, billing, user management | Reference build, single deployment |
| Automatic contract generation from a page | Contracts encode human intent about meaning; auto-drafting them is a research problem. The `contracts.created_from` column reserves `"auto_draft"` for future use |
| Model training or fine-tuning | No models are trained; the LLM seam is optional and generates prose only |
| Historical backfill of pages | The ledger starts when a source is onboarded |

## Not implemented — gaps, not choices

These are absent and should be read as gaps rather than scoping decisions.

| Missing | Impact | Reference |
|---|---|---|
| Authentication and authorisation *(mandatory)* | Opt-in bearer-token gate added 2026-08-22 (`DW_API_TOKEN`); off by default, so anyone with network access can still approve heals, trigger runs, or mutate demo state unless it's configured | [Security Architecture](../06_Security/Security_Architecture.md) |
| Containerisation (Dockerfile / compose) | Deployment is manual; "reproducible by judges" rests on Python + pip | [Deployment](../08_Deployment/Deployment_Architecture.md) |
| Database migrations | Schema changes require manual intervention on an existing DB | [Database Design](../04_Data/Database_Design.md#migrations) |
| ~~Explicit indexes beyond primary keys~~ | **Resolved 2026-08-22** — 8 indexes now cover the hot-path lookups | [Database Design](../04_Data/Database_Design.md#indexing-analysis) |
| Frontend tests | 581 lines of `app.js` entirely untested | [Test Strategy](../07_Testing/Test_Strategy.md) |
| Rate limiting, CSRF, security headers | — | [Threat Model](../06_Security/Threat_Model.md) |
| Structured application logging | Only Flask's default request log plus the audit ledger | [Observability](../10_Operations/Observability.md) |
| Metrics endpoint / tracing | No Prometheus, no OpenTelemetry | [Observability](../10_Operations/Observability.md) |
| Health / readiness endpoints | No `/healthz`; liveness inferred from `/api/stats` | [Observability](../10_Operations/Observability.md) |
| Credit budget enforcement | `credit_budget` and `BudgetExceeded` exist but nothing reads or raises them | [Gap Report G-06](../11_Assessment/Engineering_Gap_Report.md) |

## Assumptions

| ID | Assumption | If false |
|---|---|---|
| A-1 | Target pages expose unit/scope text near each value | The semantic gate has nothing to anchor on; Class 4 becomes undetectable |
| A-2 | Watched entities carry a stable identifier across redesigns | Entity resolution degrades to index matching; diffs become noisy |
| A-3 | Scraper Studio's heal preview is representative of post-approval output | Verification could pass on a preview that differs from production output |
| A-4 | A human authors each contract | Onboarding is not self-service |
| A-5 | Single-writer database access | SQLite write contention under concurrency; see [ADR-002](../03_Architecture/ADRs/README.md#adr-002--sqlite-as-the-only-datastore) |
| A-6 | The deployment network is trusted, or `DW_API_TOKEN` is set | Unless the token is configured (opt-in as of 2026-08-22), any reachable client has full control |

A-3 and A-6 are the two that would most change the engineering if false.

## Constraints

| Constraint | Source | Consequence |
|---|---|---|
| Heal prompt ≤ 1000 characters | Bright Data API | `compose_heal_prompt()` truncates on a word boundary; enforced by test |
| Free tier 5,000 credits/month, 1 credit per page load | Bright Data | `credits_per_page_load` tracked per run; budget **not enforced** |
| Scraper Studio AI Flow concurrency cap | Bright Data | Handled inside the CLI, which is why `LiveClient` shells out rather than calling REST |
| Python ≥ 3.10 | `pyproject.toml` | No 3.11-only constructs: `RunState` is `(str, Enum)`, timestamps use `datetime.timezone.utc` |
| Public data only | Hackathon rules | Mirror site is self-hosted and clearly labelled |
| 7-day build window | Hackathon | Drove SQLite, no containers, no auth |

## Dependencies

**Runtime (5):** `flask>=3`, `pydantic>=2`, `jsonschema>=4`, `pyyaml>=6`, `httpx>=0.27`
**Dev:** `ruff` (CI only)
**Stdlib:** `sqlite3`, `unittest`, `threading`, `subprocess`, `hashlib`, `re`

**External services**

| Service | Required? | Failure behaviour |
|---|---|---|
| Bright Data Scraper Studio | Only in `DW_MODE=live` | Replay mode has zero external dependencies |
| Anthropic API | No | `make_provider(None)` returns `HeuristicProvider`; any error falls back |
| Slack webhook | No | Exception caught and audited |

The dependency footprint is genuinely small, and the offline default is a real engineering property rather than a demo convenience: the whole system runs, tests, and demos with no network.

---

**Next:** [Competitive Analysis](Competitive_Analysis.md) · [USP & Novelty](USP_Novelty.md)
