# Engineering Gap Report

[← Documentation index](../README.md) · [← Requirements Gap Analysis](../02_Requirements/Requirements_Gap_Analysis.md)

---

> **Relationship to the Requirements Gap Analysis.** [`02_Requirements/Requirements_Gap_Analysis.md`](../02_Requirements/Requirements_Gap_Analysis.md) enumerates every gap (`GAP-01`…`GAP-20`) in the order they surfaced during review. **This document re-ranks the highest-value subset by impact × feasibility** — a different ordering, a different ID space (`G-01`…`G-15`), and it is the one other documents point to when the *priority* of a gap matters rather than its existence. Each entry below cites the `GAP-NN` it corresponds to, so the two documents stay reconcilable.
>
> **Update 2026-08-22.** Four items on this list — **G-01** (partially, opt-in), **G-05** (minimum fix only), **G-12**, and **G-14** — were closed or mitigated same-day; each is marked inline below. `G-06` (credit budget enforcement) was **not** touched by today's fixes and remains open. The ranking order is left as originally derived — it reflects impact × feasibility at the time of review — with status annotations layered on top rather than re-sorted, so this document stays a stable record of the analysis.

## Methodology

**Impact** — what breaks, and how badly, if this is never fixed: correctness, trust/audit integrity, security exposure, or a headline product claim.
**Feasibility** — effort to close, and how self-contained the fix is (pure code change vs. blocked on an external account/vendor).

Rank favours **high impact, low effort** first; a high-impact item blocked on something outside this codebase's control (live vendor access) is ranked by impact but flagged as not schedulable the same way as a pure code fix.

## Ranked gaps

| Rank | Gap | Impact | Effort | Maps to |
|---|---|---|---|---|
| **G-01** | No authentication on any endpoint | **Critical** | ~1 h | ✅ **Partially resolved 2026-08-22** (opt-in) — [GAP-01](../02_Requirements/Requirements_Gap_Analysis.md#gap-01--no-authentication-on-any-endpoint) |
| **G-02** | Reliability handlers (REL-001/002/003) never exercised by a failure-injection test | **High** | ~3 h | [GAP-08](../02_Requirements/Requirements_Gap_Analysis.md#gap-08--reliability-guarantees-never-exercised) |
| **G-03** | Indirect prompt injection via scraped content into the heal prompt is unmitigated | **High** | ~2 h | [Threat Model T-08](../06_Security/Threat_Model.md#t-08-in-depth--the-ai-specific-threat-that-matters) |
| **G-04** | Live Bright Data path never validated | **High** | Blocked on vendor account access, not code | [GAP-02](../02_Requirements/Requirements_Gap_Analysis.md#gap-02--live-bright-data-path-never-validated) |
| **G-05** | Onboarding cannot produce a working source (no contract is generated) | **High** | ~1 day | ⚠️ **Minimum fix only 2026-08-22** (fails fast with 422, doesn't yet generate a contract) — [GAP-04](../02_Requirements/Requirements_Gap_Analysis.md#gap-04--onboarding-cannot-produce-a-working-source) |
| **G-06** | Credit budget defined but never enforced | **Medium** | ~1 h | [GAP-06](../02_Requirements/Requirements_Gap_Analysis.md#gap-06--credit-budget-defined-but-never-enforced) |
| **G-07** | Error taxonomy is dead code — the pipeline raises bare `ValueError` instead of its own typed errors | **Medium** | ~2 h | [GAP-05](../02_Requirements/Requirements_Gap_Analysis.md#gap-05--error-taxonomy-is-dead-code) |
| **G-08** | Three-band gate weights are unjustified constants, no sensitivity analysis | **Medium** | ~4 h | [GAP-13](../02_Requirements/Requirements_Gap_Analysis.md#gap-13--gate-weights-are-unjustified-constants) |
| **G-09** | No retry or backoff on Bright Data calls; the spike observed real 503s | **Medium** | ~2 h | [GAP-09](../02_Requirements/Requirements_Gap_Analysis.md#gap-09--no-retry-or-backoff-on-bright-data-calls) |
| **G-10** | Class 5 relocation candidates are surfaced but cannot be applied | **Medium** | ~1 day | [GAP-10](../02_Requirements/Requirements_Gap_Analysis.md#gap-10--class-5-relocation-cannot-be-applied) |
| **G-11** | API test coverage is 3 of 19 routes; every state-changing endpoint is untested | **Medium–High** | ~1 day | [GAP-11](../02_Requirements/Requirements_Gap_Analysis.md#gap-11--api-test-coverage-is-3-of-19-routes) |
| **G-12** | No database indexes beyond primary keys | **Low today, grows with data** | ~30 min | ✅ **Resolved 2026-08-22** — [GAP-12](../02_Requirements/Requirements_Gap_Analysis.md#gap-12--no-database-indexes-beyond-primary-keys) |
| **G-13** | No schema migration path | **Low today, high later** | ~1 day (adopt a tool) | [GAP-14](../02_Requirements/Requirements_Gap_Analysis.md#gap-14--no-schema-migration-path) |
| **G-14** | Seeded `42.3s` MTTR displayed identically to measured values | **Medium (credibility)** | ~30 min | ✅ **Resolved 2026-08-22** — [GAP-18](../02_Requirements/Requirements_Gap_Analysis.md#low) |
| **G-15** | Zero frontend tests — 581 lines of `app.js`, manual DOM construction | **Medium** | ~1 day | [GAP-07](../02_Requirements/Requirements_Gap_Analysis.md#gap-07--frontend-entirely-untested) |

## Detail on the top five

### G-01 — No authentication on any endpoint

**Status: partially resolved 2026-08-22.** A bearer-token check now exists in a Flask `before_request` hook (`api/app.py :: _require_auth`), allowlisting `/`, `/assets/*`, `/mirror/*`, and the server now binds `127.0.0.1` by default instead of `0.0.0.0`. **What remains open:** both are opt-in — `DW_API_TOKEN` must be set for auth to activate, and the default out-of-the-box configuration is unchanged, so `POST /api/review/<id>` still writes `decided_by: "human"` for an unauthenticated request unless an operator turns the token on. The fix converts this from "no capability" to "a configuration decision," which is a real improvement but not full closure.
**Original state (for the record).** All 19 routes were reachable by anyone with network access; the server bound `0.0.0.0` unconditionally. **Why it mattered:** this was not merely an access-control gap — it corrupted the product's central claim, since the ledger could attribute an anonymous network call to "a human" it could not identify. **Applied fix:** bearer-token check + `127.0.0.1` default. **Effort:** ~1 hour, done. **Remaining decision:** whether to make `DW_API_TOKEN` mandatory rather than optional. See [Security Architecture](../06_Security/Security_Architecture.md), [ADR-009](../03_Architecture/ADRs/README.md#adr-009--no-authentication-in-the-reference-build).

### G-02 — Reliability handlers never exercised

**Current state.** `REL-001` (Slack failure isolation), `REL-002` (scheduler tick survives a source failure), and `REL-003` (LLM fallback) are each one `try`/`except` block, and none is triggered by any of the 23 tests. **Why it matters:** an untested exception handler is not a verified guarantee — it is a guess about what exception type and shape will occur, and a mismatched `except` clause fails exactly when it is needed, silently. **Recommended fix:** three targeted tests — mock `httpx.post` to raise inside `send_alert`, mock `run_source` to raise inside a scheduler tick, mock `AnthropicProvider._complete` to raise — each asserting the system continues correctly. **Effort:** ~3 hours (roughly 1 hour per test). See [Reliability & Failure Design § 3](../10_Operations/Reliability_and_Failure_Design.md#3-the-untested-reliability-finding), [Risk R-09](../06_Security/Risk_Register.md).

### G-03 — Indirect prompt injection into the heal prompt

**Current state.** `healing/composer.py` interpolates `expected_examples` values — taken verbatim from the last-known-good extraction of a third-party page — directly into an f-string sent to the vendor's heal AI, with no delimiting or sanitisation. **Why it matters:** this is the one threat in the system's own threat model rated to survive even a fully-trusted, localhost-only deployment, because the attacker is the watched page, not a network client — and the blast radius is "regenerated executable extraction logic," not merely misleading text. **Recommended fix:** delimit untrusted values with explicit markers in the prompt template, and consider a negative-anchor check ("if the composed prompt contains an imperative sentence pattern, flag for review before sending"). **Effort:** ~2 hours for delimiting; the negative-anchor heuristic is a further increment. See [AI Architecture § 5](../09_AI_ML/AI_Architecture.md#5-ai-safety), [Threat Model T-08](../06_Security/Threat_Model.md#t-08-in-depth--the-ai-specific-threat-that-matters).

### G-04 — Live Bright Data path never validated

**Current state.** `LiveClient` is fully implemented and untested by any successful run; the gap is account/zone provisioning, not code, per [Project Vision § OBJ-9](../01_Product/Project_Vision.md). **Why it matters:** every claim this system makes about production-grade vendor integration rests on a code path that has literally never executed successfully — the envelope-parsing assumptions in `brightdata/envelopes.py` are unverified against a real CLI response. **Recommended fix:** the checklist already exists in `SCRAPER_STUDIO.md` — one successful `scraper create` → `scraper heal` → `scraper approve` transcript retires this gap outright. **Effort:** not a code estimate — this is blocked on external access, which is why it ranks by impact rather than by the same effort-first logic as the other top-five items. See [AI Architecture § Live-path validation status](../09_AI_ML/AI_Architecture.md#live-path-validation-status).

### G-05 — Onboarding cannot produce a working source

**Status: minimum fix applied 2026-08-22, capability gap still open.** `POST /api/onboard` now checks for the contract file before calling the vendor's AI Flow and returns `422` with an actionable message if it's missing, instead of committing rows and spending a vendor call before crashing on the first run. **What remains open:** onboarding still cannot *produce* a working source for a genuinely new `source_id` — "watch any page in one sentence" is a headline capability claim that is still not true for any source outside the two pre-seeded demo sources. **Recommended fix (proper, still open):** translate the AI Flow's generated JSON Schema into a minimal `ContractSpec` (schema gate only, no semantic assertions — those still require a human to identify anchor text) and write it to `fixtures/contracts/<id>.yaml`, or persist it via the already-existing but currently-decorative `contracts` table ([ADR-003](../03_Architecture/ADRs/README.md#adr-003--contracts-as-yaml-files-not-database-rows)). **Effort:** ~1 day. See [Model Limitations § 8](../09_AI_ML/Model_Limitations.md#8-onboarding-a-genuinely-new-source-does-not-currently-produce-a-runnable-pipeline).

## Housekeeping (low-effort, not separately ranked)

These are real but small — grouped rather than individually ranked, matching their treatment in the [Requirements Gap Analysis](../02_Requirements/Requirements_Gap_Analysis.md):

| Item | Effort |
|---|---|
| `GAP-15` — no health/readiness endpoint | 15 min |
| `GAP-16` — no structured logging | 2 h |
| `GAP-17` — no OpenAPI specification | 3 h |
| `GAP-19` — build artifacts (`driftwatch.zip`, `.ruff_cache`) were tracked until recently | done |
| `GAP-20` — no `.gitattributes`; CRLF churn across platforms | 15 min |
| CI installs a hand-duplicated dependency list instead of `pip install -r requirements.txt` | 5 min |

## Roadmap

Grouped by when each item should happen, not by rank — some high-rank items (G-04) simply cannot be scheduled the way a pure code fix can.

**Phase 1 — before any non-local demo or submission.** ~~G-01 (auth), G-14 (unmark the seeded MTTR or separate it from measured values).~~ **Both done 2026-08-22** (G-01 opt-in, G-14 fully resolved), along with G-12 (indexes) and G-05's minimum fix, which were bundled into the same pass since all four were same-day, low-risk changes.

**Phase 2 — high-value, still same-week.** G-02 (reliability tests), G-03 (prompt delimiting), G-06 (credit budget enforcement), G-07 (use the error taxonomy), G-09 (retry/backoff). None requires new infrastructure. Still open.

**Phase 3 — production hardening.** G-05's proper fix (onboarding→auto-drafted contract, beyond today's fail-fast minimum), G-08 (gate-weight sensitivity table), G-11 (API test coverage), G-15 (frontend tests), plus everything in [Deployment Architecture § Recommended production shape](../08_Deployment/Deployment_Architecture.md#9-recommended--production-deployment-shape) (containerise, WSGI server, Postgres, reverse proxy).

**Phase 4 — future scale.** G-04 (live validation, pending vendor access), G-10 (relocation apply), G-13 (migrations, once schema needs to change on a live database).

---

**Next:** [Judge Evaluation](Judge_Evaluation.md) · [Production Readiness](Production_Readiness.md)
