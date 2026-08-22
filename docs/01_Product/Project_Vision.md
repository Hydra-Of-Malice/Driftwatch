# Project Vision

[← Documentation index](../README.md)

---

## Vision

The public web is an undeclared dependency of most software. DriftWatch exists to give that dependency the properties every other dependency already has: **a version, a contract, a changelog, and a test that fails when it breaks.**

## Mission

Turn watched public pages into versioned semantic data contracts that repair themselves when structure changes, refuse to publish when meaning changes, and quantify the impact of every real change.

## Objectives

| ID | Objective | Status | Evidence |
|---|---|---|---|
| OBJ-1 | Detect meaning change that passes structural validation | **VALIDATED** | `contracts/engine.py::_gate_semantics`; `test_contracts.py` |
| OBJ-2 | Classify every change into an actionable taxonomy | **VALIDATED** | `drift/classifier.py`; `test_drift.py` (6 tests) |
| OBJ-3 | Repair structural breaks with no human in the loop | **VALIDATED (replay)** | `healing/orchestrator.py`; `test_healing.py` |
| OBJ-4 | Never accept a repair that cannot be re-proven | **VALIDATED** | `healing/verifier.py`; `test_garbage_preview_is_auto_rejected_never_trusted` |
| OBJ-5 | Prevent unvalidated data reaching consumers | **VALIDATED** | `pipeline/runner.py` quarantine paths; `test_e2e_pipeline.py` |
| OBJ-6 | Attach cost and code impact to material changes | **VALIDATED** | `impact/cost.py`, `impact/scanner.py`; E2E asserts `412.0` |
| OBJ-7 | Make every automated decision auditable | **IMPLEMENTED** | `db.audit()` at every transition |
| OBJ-8 | Suppress noise — never alert on cosmetic change | **VALIDATED** | `alerts.py` early return; `test_drift.py::test_benign` |
| OBJ-9 | Operate against real Bright Data infrastructure | **UNVALIDATED** | `brightdata/live.py` written; no successful live run recorded |

OBJ-9 is the one unmet objective, and it is unmet for an account-configuration reason rather than a code reason. See [AI Architecture § Live-path validation status](../09_AI_ML/AI_Architecture.md#live-path-validation-status).

## Design principles

These are observable in the code, not aspirational statements.

### 1. The dashboard cannot lie

A snapshot that fails its contract is written with `quarantined = 1` and is excluded from every downstream read. `_last_good()` filters on `quarantined = 0`, so a quarantined snapshot can never become the comparison baseline, never appears as `latest_snapshot`, and never feeds an alert.
Evidence: `pipeline/runner.py :: _last_good`, `api/app.py :: source_detail`

### 2. A repair is a claim, not a fact

`verify_preview()` re-evaluates the heal preview against the complete contract. The heal's own `status: awaiting_approval` is never used as evidence of correctness — only the independently computed `Verdict` decides.
Evidence: `healing/verifier.py`, `healing/orchestrator.py`

### 3. Decisions are deterministic; only prose is generated

Every branch in the pipeline is decided by explicit thresholds and rule evaluation. The LLM seam (`Provider`) affects alert wording and migration notes only. Removing the model entirely changes no state transition.
Evidence: `llm/provider.py :: HeuristicProvider` is the default from `make_provider(None)`

### 4. Confidence is a number, and it drives policy

Contract evaluation produces a weighted confidence in `[0, 1]` (schema 0.35, invariants 0.25, semantics 0.25, continuity 0.15). The heal policy reads that number against two thresholds and routes to auto-approve, human review, or auto-reject.
Evidence: `contracts/engine.py :: GATE_WEIGHTS`, `config.py :: auto_approve_threshold / auto_reject_threshold`

### 5. Failure is a state, not a log line

Seventeen explicit `RunState` values, each persisted and audited. There is no failure path that only exists in stderr.
Evidence: `domain.py :: RunState`

### 6. One seam per external dependency

Bright Data sits behind `BrightDataClient`; the LLM sits behind `Provider`. Both are `typing.Protocol` definitions with a deterministic offline implementation and a live implementation.
Evidence: `brightdata/protocol.py`, `llm/provider.py`

## Success criteria

### Achieved

| Criterion | Result |
|---|---|
| A semantic unit flip is caught while schema passes | ✅ `test_semantic_drift_fails_only_the_semantics_gate` |
| A garbage repair is refused, not approved | ✅ `test_garbage_preview_is_auto_rejected_never_trusted` |
| All five drift classes walk the full state machine | ✅ `test_full_lifecycle_across_all_drift_classes` |
| Cosmetic change produces no alert | ✅ `test_benign` + `alerts.py` guard |
| Heal prompt within vendor's documented limit | ✅ `test_prompt_is_specific_and_within_limit` |
| Suite green and lint clean in CI | ✅ 23/23, `ruff` clean |

### Not achieved

| Criterion | Status | Blocker |
|---|---|---|
| A real Scraper Studio collector created and executed | ❌ | Account zone provisioning — see [AI Architecture](../09_AI_ML/AI_Architecture.md#live-path-validation-status) |
| A real heal verified end-to-end against a live page | ❌ | Same |
| Drift observed against real public pages over time | ❌ | Requires the live path first |
| Any authentication on the API | ❌ | **NOT IMPLEMENTED** by design decision for the reference build — see [ADR-009](../03_Architecture/ADRs/README.md#adr-009--no-authentication-in-the-reference-build) |

## Non-goals

Deliberately out of scope, with reasoning in [Scope](Scope.md):

- A general-purpose scraping platform — DriftWatch orchestrates Scraper Studio, it does not replace it
- Proxy management, CAPTCHA solving, browser automation — the vendor's job
- AST-level call-graph analysis for impact — literal entity scanning is the stated v1 scope
- Multi-tenancy, billing, user management

---

**Next:** [User Personas](User_Personas.md) · [Scope](Scope.md) · [HLD](../03_Architecture/HLD.md)
