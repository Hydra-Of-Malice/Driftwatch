# Risk Register

[← Documentation index](../README.md)

---

Severity = Probability × Impact. Owner is "Project" throughout (single-maintainer build).

---

## Critical

| ID | Risk | Prob | Impact | Severity | Mitigation | Status |
|---|---|---|---|---|---|---|
| R-01 | **Live Bright Data path has never worked.** Every Scraper Studio claim rests on a replay client modelling a system nobody has observed. Envelope shapes are asserted, not verified | High | High | **CRITICAL** | Run `bdata login` to provision `cli_unlocker`/`cli_browser` zones, re-run the spike, reconcile `envelopes.py` | **OPEN** — root cause identified |
| R-02 | **No authentication.** Anyone reaching the port can approve templates, spend credits, and be recorded as `human` | High | High | **CRITICAL** | Bearer token in `before_request`; bind `127.0.0.1` | **MITIGATED 2026-08-22** — mechanism built (`_require_auth`, `DW_HOST` defaults to `127.0.0.1`); still **opt-in** via `DW_API_TOKEN`, so residual risk is "operator forgets to set it," not "no capability exists" |
| R-03 | **Seeded values presented as measurements.** `heal_mttr_seconds` averages a hardcoded `42.3` flagged `"seeded": True`; the API strips the flag | High | High | **CRITICAL** | Exclude seeded rows from `/api/stats`, or label them in the UI | **CLOSED 2026-08-22** — `heal_events.seeded` column added; `/api/stats` excludes it from the mean |

R-03 is scored Critical on **credibility** rather than system impact. A reviewer who greps `seed.py` finds a fabricated headline metric, and every other number in the documentation becomes suspect by association — including the ones that are honestly measured.

---

## High

| ID | Risk | Prob | Impact | Severity | Mitigation | Status |
|---|---|---|---|---|---|---|
| R-04 | Onboarding cannot produce a working source; fails *after* committing rows and paying for a collector | High | Med | **HIGH** | Validate contract before `create_scraper()`; return 422 | **PARTIALLY MITIGATED 2026-08-22** — now fails *before* any vendor call or row insert, with a clear 422; the underlying "cannot produce a working source" gap is still open |
| R-05 | Audit-ledger integrity untested — a dropped `db.audit()` call passes all 23 tests | Med | High | **HIGH** | Assert audit rows across a full run | **OPEN** |
| R-06 | Indirect prompt injection via scraped content into heal prompts (T-08) | Med | High | **HIGH** | Delimit untrusted values; negative anchors | **OPEN** |
| R-07 | Credit exhaustion — `credit_budget` parsed but never enforced; `run-all` unauthenticated | Med | High | **HIGH** | Enforce budget before `run_scraper` | **OPEN** |
| R-08 | Frontend untested — 838 lines of JS; the UI *is* the demo | Med | High | **HIGH** | Smoke tests per route | **OPEN** |
| R-09 | Reliability handlers never exercised — REL-001/002/003 are untested try/except blocks | Med | Med | **HIGH** | Three failure-injection tests | **OPEN** |

---

## Medium

| ID | Risk | Prob | Impact | Severity | Mitigation | Status |
|---|---|---|---|---|---|---|
| R-10 | No retry/backoff on vendor calls; the spike observed repeated 503s | High | Low | **MEDIUM** | Exponential backoff in `LiveClient._cli` | **OPEN** |
| R-11 | SQLite write contention — two threads, no `busy_timeout` | Med | Med | **MEDIUM** | `PRAGMA busy_timeout=5000` | **CLOSED 2026-08-22** |
| R-12 | Crash leaves runs stuck in non-terminal states forever; no reconciliation | Med | Low | **MEDIUM** | Startup sweep to `FAILED` | **OPEN** |
| R-13 | Gate weights and thresholds are unjustified constants governing production approval | Med | Med | **MEDIUM** | Sensitivity table over the fixture corpus | **OPEN** |
| R-14 | Unindexed hot-path query scans an unbounded table on every run | Low | Med | **MEDIUM** | 8 `CREATE INDEX` statements | **CLOSED 2026-08-22** |
| R-15 | No schema migrations | Med | Med | **MEDIUM** | Version table + runner | **OPEN** |
| R-16 | Anchor matching is naive substring — false positives on rephrase, false negatives on appended qualifiers | Med | Med | **MEDIUM** | Negative anchors; normalisation | **OPEN** |
| R-17 | Dead error taxonomy contradicts its own docstring | High | Low | **MEDIUM** | Raise them or delete them | **OPEN** |
| R-18 | Unbounded data growth; no retention policy | Med | Low | **MEDIUM** | Archival design | **OPEN** |
| R-19 | Supply chain — no lockfile, no scanning | Low | High | **MEDIUM** | Lockfile + `pip-audit` | **OPEN** |
| R-20 | `LiveClient` hardcodes a POSIX `PATH`, so live mode cannot work on Windows — the maintainer's own platform | Med | Med | **MEDIUM** | Inherit `PATH`, or branch per platform | **OPEN** |

R-20 is worth flagging to anyone attempting the live path: even after `bdata login` succeeds, `LiveClient` passes `PATH=/usr/local/bin:/usr/bin:/bin` to the subprocess, which will not locate `bdata.cmd` on Windows.
Evidence: `brightdata/live.py :: _cli`

---

## Demo and submission risks

| ID | Risk | Prob | Impact | Severity | Mitigation |
|---|---|---|---|---|---|
| R-21 | Judge asks "show me a real collector ID that ran" — the honest answer is that none exists | **High** | High | **CRITICAL** | Fix R-01, or disclose replay scope proactively and lead with the verification thesis |
| R-22 | Judge greps `seed.py` and finds the MTTR constant | Med | High | **HIGH** | **CLOSED 2026-08-22** — R-03 fixed; the constant still exists in `seed.py` but is now excluded from `/api/stats`, not silently blended in |
| R-23 | Judge runs `POST /api/onboard` from the docs and gets a 500 | Med | Med | **MEDIUM** | **CLOSED 2026-08-22** — R-04 mitigated; a judge following the docs against an unknown source now gets a 422 with an explanation, not a 500 |
| R-24 | Demo machine has stale `driftwatch.db` with unexpected state | Low | High | **MEDIUM** | `make demo` already deletes the DB first ✅ |
| R-25 | Live network dependency during the demo | Low | High | **LOW** | Replay mode needs no network ✅ |

R-21 deserves a strategy note. The weakest posture is to let a judge discover the replay boundary by asking. The strongest is to state it first — *"the heal loop is verified against recorded envelopes and a controlled mirror; here is the test that proves a bad repair is refused; the live path is blocked on account zone provisioning"* — which reframes it from a hidden gap into a disclosed limitation with a diagnosed cause.

---

## Risk distribution

As originally assessed: **Critical 4** (R-01, R-02, R-03, R-21), **High 7**, **Medium 12**, **Low 2**.

**As of 2026-08-22:** R-02 mitigated (opt-in, not forced), R-03 closed. Remaining open Critical: **R-01** (live path unproven — blocked on vendor account access, not code) and **R-21** (the judge-facing framing of the same gap, now strengthened by the real spike transcript in `scripts/spike_out/` — see [AI Architecture § Live-path validation status](../09_AI_ML/AI_Architecture.md#live-path-validation-status)).

## What changes the picture most

Ranked by severity removed per hour of work. **Status reflects fixes applied 2026-08-22:**

| Action | Effort | Removes | Status |
|---|---|---|---|
| Exclude seeded MTTR from `/api/stats` | 30 m | R-03, R-22 | ✅ **Done** |
| Token auth + bind localhost | 1 h | R-02, and downgrades T-01…T-06 | ✅ **Done** (opt-in) |
| Validate contract before onboarding | 30 m | R-04, R-23 | ✅ **Done** (fails fast now; underlying gap open) |
| `PRAGMA busy_timeout` | 5 m | R-11 | ✅ **Done** |
| 8 index statements | 30 m | R-14 | ✅ **Done** |
| `bdata login` + re-run spike | 30 m | R-01, R-21 (largest single win) | ⬜ **Still open** — blocked on vendor account access, not code |

**Five of six items closed same-day.** The remaining one (R-01/R-21) is the one item on this list that was never a pure engineering task — see [AI Architecture § Live-path validation status](../09_AI_ML/AI_Architecture.md#live-path-validation-status) for the real spike evidence and what would retire it.

---

**Next:** [Engineering Gap Report](../11_Assessment/Engineering_Gap_Report.md) · [Judge Evaluation](../11_Assessment/Judge_Evaluation.md)
