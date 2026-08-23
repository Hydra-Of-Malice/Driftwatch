# Requirements Gap Analysis

[← Documentation index](../README.md) · [← RTM](Requirements_Traceability_Matrix.md)

---

Gaps found by comparing documented intent, implemented code, and passing tests. Prioritised **CRITICAL / HIGH / MEDIUM / LOW** by consequence if left unaddressed.

---

## CRITICAL

### GAP-01 — No authentication on any endpoint
**State: PARTIALLY RESOLVED (2026-08-22).** A bearer-token gate now exists (`api/app.py :: _require_auth`, a `before_request` hook allowlisting `/`, `/assets/*`, `/mirror/*`) and the server now binds `127.0.0.1` by default (`Settings.host`, was hardcoded `0.0.0.0`). **Both are opt-in / default-changed, not force-enabled:** auth activates only when `DW_API_TOKEN` is set; an operator who never sets it gets today's open-demo behaviour unchanged. The original state below is preserved for the record.
**Original state:** All 19 routes were unauthenticated, including `POST /api/review/<id>` (approves a template into production), `POST /api/run-all`, and `POST /api/onboard`. The server bound `0.0.0.0` unconditionally.
**Why it matters:** The system's entire value proposition is *trustworthy* automated decisions with an audit trail. Anyone who can reach the port can approve a heal, and it will be recorded as `decided_by: human` — the audit ledger will attribute an anonymous network request to a human reviewer. That is worse than no audit trail, because it looks authoritative.
**Evidence:** `api/app.py :: _require_auth`, `config.py :: Settings.api_token` / `.host`
**Requirements:** SEC-001, SEC-002
**Remaining fix:** decide whether `DW_API_TOKEN` should be required (not merely available) before any non-local deployment — currently a configuration choice, not an enforced one.

### GAP-02 — Live Bright Data path never validated
**State:** `LiveClient` (72 lines) is written and typed but has never completed a successful call. Recorded envelopes show `ai_trigger_failed`, `heal_trigger_failed`, `resume_failed`.
**Why it matters:** Every claim about Scraper Studio orchestration rests on `ReplayClient`, whose behaviour is defined by this project. The replay client is a faithful model, but a model of a system nobody has observed working. Envelope field names are asserted to match the real CLI; that assertion is unverified.
**Evidence:** `scripts/spike_out/*.json`; `brightdata/live.py`
**Root cause identified:** The CLI requires an interactive `bdata login` to provision `cli_unlocker` / `cli_browser` zones. A bare `BRIGHTDATA_API_KEY` does not provision them, producing `403 Automation not allowed`.
**Fix:** Run `bdata login`, re-run `scripts/day0_spike.ps1`, reconcile `envelopes.py`. **~30 minutes once logged in.**

### GAP-03 — Audit ledger integrity is untested
**State:** FR-026 and FR-028 are the system's integrity claims. No test asserts that a transition writes an audit row, or that audit rows are never mutated.
**Why it matters:** "Every decision is audited" is load-bearing for the product thesis and is currently protected by nothing. A refactor that drops a `db.audit()` call would pass all 23 tests.
**Fix:** Assert audit-row counts and actions across a full run; assert no `UPDATE`/`DELETE` path exists. **~1 hour.**

---

## HIGH

### GAP-04 — Onboarding cannot produce a working source
**State: MINIMUM FIX APPLIED (2026-08-22).** `POST /api/onboard` now checks for a contract file *before* calling the vendor and returns a `422` naming the missing path and how to fix it, instead of committing rows, spending a vendor call, then crashing on the first run. **The underlying capability gap is still open** — onboarding still cannot *produce* a working source for a genuinely new `source_id`; it now fails fast and clearly instead of fails messily.
**Original state:** `POST /api/onboard` created the scraper and rows, then called `run_source()`, which called `load_spec()`, which read `fixtures/contracts/<id>.yaml` and raised `FileNotFoundError` if absent, mid-request, after the vendor call and the row inserts had already happened.
**Why it matters:** The documented onboarding flow still fails for any genuinely new source. The demo works only because both sources ship with hand-written contracts. The improvement is that the failure is now legible and free (no vendor call, no orphaned rows) rather than a 500.
**Evidence:** `api/app.py :: onboard` (contract existence check, 422) → `contracts/engine.py :: load_spec`; `contracts.created_from` still reserves an unused `"auto_draft"` value
**Fix (applied):** Return a clear 422 naming the missing contract path instead of a 500, before spending a vendor call. **Done, ~30 minutes.**
**Fix (proper, still open):** Draft a contract from the AI-Flow schema, persist with `created_from='auto_draft'`, require human confirmation of anchors. **~1 day.**

### GAP-05 — Error taxonomy is dead code
**State:** `errors.py` defines 7 classes. Verified by grep: `FetchError`, `ContractViolation`, `HealRejected`, and `BudgetExceeded` are **raised zero times**. The pipeline raises bare `ValueError` instead.
**Why it matters:** The module's docstring claims "every failure mode maps to one of these classes, and every one maps to a visible pipeline state." That is not true, and a reviewer who greps will find it in under a minute. Documented intent contradicting implementation is more damaging than a missing feature.
**Evidence:** `runner.py:99` and `orchestrator.py:128` raise `ValueError`
**Fix:** Either raise the typed errors or delete the unused classes. **~1 hour.**

### GAP-06 — Credit budget defined but never enforced
**State:** `Settings.credit_budget = 4500` is parsed from `DW_CREDIT_BUDGET`; `BudgetExceeded` exists. Neither is ever read or raised. `credits_spent` is recorded per run but never summed against a limit.
**Why it matters:** In live mode a scheduler loop against several sources can consume the free-tier allowance with nothing to stop it. The guard is documented in the config comment ("Hard ceiling on Bright Data credit spend") but does not exist.
**Fix:** Check cumulative `credits_spent` before `run_scraper`; raise `BudgetExceeded`; surface in `/api/stats`. **~2 hours.**

### GAP-07 — Frontend entirely untested
**State:** 581 lines `app.js` + 257 lines `viz.js` + 213 lines CSS. Zero tests.
**Why it matters:** The UI is the demo. A rendering regression is invisible until it happens on screen. FR-032 is **UNVALIDATED**.
**Fix:** Smoke-test that each route renders without console errors. **~3 hours.**

### GAP-08 — Reliability guarantees never exercised
**State:** REL-001 (alert failure isolated), REL-002 (scheduler survives failures), REL-003 (LLM fallback) are implemented as try/except blocks and never tested by inducing the failure.
**Why it matters:** Untested exception handlers are among the most common sources of production surprises — the handler itself can be wrong.
**Fix:** Three tests injecting failures. **~2 hours.**

---

## MEDIUM

### GAP-09 — No retry or backoff on Bright Data calls
`LiveClient._cli` raises on any non-zero exit. Real CLI usage encounters transient 503s — observed directly in the spike output. REL-005 **NOT IMPLEMENTED**. **~1 hour.**

### GAP-10 — Class 5 relocation cannot be applied
`discover()` proposes candidates; no endpoint updates `sources.url`. The loop is open. **~2 hours.**

### GAP-11 — API test coverage is 3 of 19 routes
`test_api.py` covers sources listing, demo state, and variant rejection. 16 routes untested, including `review_decide`, which mutates production state. **~3 hours.**

### GAP-12 — No database indexes beyond primary keys
**RESOLVED (2026-08-22).** 8 indexes now cover every hot-path `source_id`/`status`/`trigger_event_id` lookup (`db.py :: SCHEMA`). Previously every query filtered on `source_id` or ordered by `id` with no supporting index — correct but scan-bound. See [Database Design § Indexing analysis](../04_Data/Database_Design.md#indexing-analysis). **Was ~30 minutes; done.**

### GAP-13 — Gate weights are unjustified constants
`GATE_WEIGHTS` and the two confidence thresholds are magic numbers with no sensitivity analysis. The approve/reject policy depends entirely on them. **~4 hours** to produce a sensitivity table.

### GAP-14 — No schema migration path
`CREATE TABLE IF NOT EXISTS` only. Any column change requires manual DB surgery. **~2 hours** for a minimal version table.

---

## LOW

| Gap | Detail | Effort |
|---|---|---|
| GAP-15 | No health/readiness endpoint (OBS-003) | 15 min |
| GAP-16 | No structured logging (OBS-004) | 2 h |
| GAP-17 | No OpenAPI specification | 3 h |
| GAP-18 | ~~Seeded `42.3s` MTTR displayed identically to measured values~~ **RESOLVED 2026-08-22** | done |
| GAP-19 | `driftwatch.zip` and `.ruff_cache` were tracked until recently | done |
| GAP-20 | No `.gitattributes`; CRLF churn across platforms | 15 min |

> **GAP-18 — resolved 2026-08-22, kept here as the record of what was wrong and why.** `/api/stats` used to return `heal_mttr_seconds` as the mean over *all* `heal_events.mttr_seconds`, including `seed.py`'s hardcoded `42.3` rows marked `"seeded": True` — a marker the API silently stripped, so the UI presented a fabricated constant in the same visual position as genuinely measured values. This was the single most misleading element in the product surface. **Fix:** `heal_events` gained a real `seeded` column; `/api/stats` now excludes `seeded = 1` from the mean and reports `heal_mttr_measured_count` alongside it; the UI shows "no measured heal yet" instead of a number until a real heal runs, and the Heal History table tags seeded rows explicitly.
> Evidence: `db.py :: SCHEMA` (`heal_events.seeded`), `seed.py` (`"seeded": 1`), `api/app.py :: stats`, `frontend/assets/app.js`

---

## Contradictions between documentation and implementation

Found by comparing docstrings and README against code:

| Claim | Location | Reality |
|---|---|---|
| "every failure mode maps to one of these classes" | `errors.py` docstring | 4 of 7 never raised (GAP-05) |
| "Hard ceiling on Bright Data credit spend" | `config.py:51` comment | Never enforced (GAP-06) |
| ~~"42s heal MTTR"~~ | UI stat tile | Was a seeded constant (GAP-18) — resolved 2026-08-22, now excluded from the measured mean |
| "restart-safe" scheduler | `scheduler.py` docstring | In-process thread; state survives but scheduling stops on exit |
| "Zero mandatory third-party deps beyond what ships in most distros" | `pyproject.toml` comment | Flask, Pydantic, jsonschema, PyYAML, httpx are not stdlib |

None are fatal, and all are fixable by editing a comment. They are listed because a rigorous reviewer will find them, and finding them undermines trust in claims that *are* accurate.

---

## Priority summary

| Priority | Count | Total effort |
|---|---|---|
| CRITICAL | 3 | ~3 h (+ login) |
| HIGH | 5 | ~9 h |
| MEDIUM | 6 | ~13 h |
| LOW | 6 | ~6 h |

The three CRITICAL gaps are all addressable in an afternoon. That is the encouraging read: the architecture is sound and the gaps are additive, not structural.

---

**Next:** [HLD](../03_Architecture/HLD.md) · [Gap Report](../11_Assessment/Engineering_Gap_Report.md)
