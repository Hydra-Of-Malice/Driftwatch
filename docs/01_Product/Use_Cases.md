# Use Cases

[← Documentation index](../README.md)

---

Format: **Actor → Action → System Behaviour → Expected Outcome**, with implementation evidence and status.

---

## Primary use cases

### UC-001 — Onboard a new watched source
**Actor:** Platform Engineer
**Action:** `POST /api/onboard` with `{id, name, url, description, vertical, schedule_minutes}`
**System behaviour:** Calls `create_scraper()` (Scraper Studio AI Flow) → inserts `sources` and `scrapers` rows → audits `source.onboarded` → executes a first run
**Expected outcome:** `collector_id`, `view_url`, AI-Flow steps, and the first run summary
**Status:** **PARTIALLY IMPLEMENTED** — succeeds only if `fixtures/contracts/<id>.yaml` already exists; `load_spec()` has no fallback
**Evidence:** `api/app.py :: onboard`; `contracts/engine.py :: load_spec`

### UC-002 — Detect semantic drift under a passing schema
**Actor:** System (scheduled)
**Action:** Run a source whose page redefined a unit while keeping values valid
**System behaviour:** Schema ✅, invariants ✅, semantics ❌ → snapshot quarantined → Class 4 event → cost estimated → critical alert → `REVIEW`
**Expected outcome:** Alert naming the failed anchor and asserted meaning; data withheld from consumers
**Status:** **VALIDATED**
**Evidence:** `contracts/engine.py :: _gate_semantics`; `pipeline/runner.py :: _handle_semantic`; `test_contracts.py::test_semantic_drift_fails_only_the_semantics_gate`

### UC-003 — Publish an unchanged extraction cheaply
**Actor:** System
**Action:** Run a source whose page has not changed
**System behaviour:** Content hash equals last-known-good and verdict passes → publish without diffing or classification
**Expected outcome:** `class: 0, state: published`; no event, no alert
**Status:** **VALIDATED** — measured p50 6.08 ms
**Evidence:** `pipeline/runner.py` fast path; [Performance Validation](../07_Testing/Performance_Validation.md)

### UC-004 — Autonomously repair a structural break
**Actor:** System
**Action:** Run a source whose page was redesigned
**System behaviour:** `DIAGNOSING` → compose prompt → `HEALING` → `VERIFYING` → confidence ≥ 0.90 → approve, version+1 → `RERUNNING` → `PUBLISHED`
**Expected outcome:** `healed: true`, active version incremented, no human involved
**Status:** **VALIDATED (replay)** — the live path is unproven
**Evidence:** `healing/orchestrator.py :: run_heal`; `test_healing.py::test_verified_heal_is_auto_approved_and_versions_bump`

### UC-005 — Refuse a repair that cannot be verified
**Actor:** System
**Action:** Heal returns a preview that fails the contract
**System behaviour:** Confidence ≤ 0.50 → `client.approve(reject=True)` → retry once with a refined prompt naming the prior failure → if still failing, `QUARANTINED` on the previous version
**Expected outcome:** Bad template never activated; source pinned to last good version
**Status:** **VALIDATED**
**Evidence:** `healing/orchestrator.py`; `test_healing.py::test_garbage_preview_is_auto_rejected_never_trusted`

> This is the single most important behaviour in the system. It is the difference between "self-healing" and "self-healing you can trust".

### UC-006 — Escalate an uncertain repair to a human
**Actor:** System, then Engineering Manager
**Action:** Heal verifies between the two thresholds (0.50 < confidence < 0.90)
**System behaviour:** `heal_events.status = 'review'`, warning alert, run ends in `REVIEW`; Bright Data's approval gate is left open
**Expected outcome:** Item in the Review Queue with prompt, preview, and per-gate verdict
**Status:** **VALIDATED**
**Evidence:** `test_healing.py::test_gray_band_lands_in_review_and_human_approval_uses_same_api`

### UC-007 — Apply a human approval decision
**Actor:** Engineering Manager
**Action:** `POST /api/review/<heal_id>` with `{approve: true|false}`
**System behaviour:** Calls the **same** `client.approve()` the machine would have; on approval bumps the version, records `human_approved`, and immediately re-runs the source
**Expected outcome:** Decision applied and audited with `decided_by: human`
**Status:** **VALIDATED**
**Security note:** **unauthenticated by default** (opt-in via `DW_API_TOKEN`, added 2026-08-22) — see [Threat Model T-03](../06_Security/Threat_Model.md)
**Evidence:** `api/app.py :: review_decide`; `healing/orchestrator.py :: decide_review`

### UC-008 — Quantify the cost of a material price change
**Actor:** System
**Action:** A watched price field changes
**System behaviour:** `_material_delta()` multiplies the per-1M delta by declared monthly volume from `usage.yaml`
**Expected outcome:** `cost_delta_monthly` on the impact report
**Status:** **VALIDATED** — E2E asserts exactly `412.0` from `(0.90×320)+(0.50×248)`
**Evidence:** `impact/cost.py :: _material_delta`; `test_e2e_pipeline.py`

### UC-009 — Quantify the cost of a unit redefinition
**Actor:** System
**Action:** Unit context flips from input-only to input+output
**System behaviour:** `_unit_flip_delta()` applies the unchanged price to the previously unbilled output volume
**Expected outcome:** Dollar figure for a change where no price number moved
**Status:** **IMPLEMENTED**, exercised in E2E
**Evidence:** `impact/cost.py :: _unit_flip_delta`

### UC-010 — Locate affected code
**Actor:** AI Application Engineer
**Action:** Open a Class 3/4 event
**System behaviour:** `entities_from_changes()` extracts entity labels; `scan_repo()` walks the connected repo for literal matches across 9 file extensions
**Expected outcome:** File, line, snippet, and matched entity per call site
**Status:** **IMPLEMENTED** — literal matching only; AST analysis is an explicit non-goal
**Evidence:** `impact/scanner.py`

### UC-011 — Audit an automated decision
**Actor:** Engineering Manager
**Action:** `GET /api/ledger`
**System behaviour:** Returns append-only `audit_events` newest-first with actor, action, refs, payload
**Expected outcome:** Complete decision trail
**Status:** **IMPLEMENTED**
**Evidence:** `db.py :: audit`; `api/app.py :: ledger`

### UC-012 — Handle a page that disappears
**Actor:** System
**Action:** Fetch fails
**System behaviour:** `RELOCATING` → `discover()` → up to 5 candidates as `FieldChange` rows → Class 5 critical alert → `REVIEW`
**Expected outcome:** Relocation candidates presented
**Status:** **PARTIALLY IMPLEMENTED** — no endpoint applies a chosen candidate
**Evidence:** `pipeline/runner.py :: _handle_unreachable`

---

## Secondary use cases

### UC-013 — Drive the demo world
**Actor:** Presenter · **Action:** `POST /api/demo/state {source_id, variant}`
**Behaviour:** Sets the mirror variant; validates against a 5-value allowlist, `400` otherwise
**Status:** **VALIDATED** — `test_api.py::test_invalid_variant_rejected`

### UC-014 — Run every source on demand
**Actor:** Presenter · **Action:** `POST /api/run-all`
**Status:** **IMPLEMENTED** — unauthenticated by default (opt-in via `DW_API_TOKEN`); synchronous; see [Risk R-07](../06_Security/Risk_Register.md)

### UC-015 — Suppress cosmetic noise
**Actor:** System · **Behaviour:** Classes 0–2 return from `send_alert()` before any write
**Status:** **VALIDATED** — `test_drift.py::test_benign`

### UC-016 — Deliver alerts to Slack
**Actor:** System · **Behaviour:** If `DW_SLACK_WEBHOOK` set, POST the text; failures are audited, never raised
**Status:** **IMPLEMENTED — UNVALIDATED** (no test covers the Slack branch)
**Evidence:** `alerts.py`

---

## Coverage matrix

| Use case | Requirement | Test | Status |
|---|---|---|---|
| UC-001 | FR-001 | — | **PARTIAL** |
| UC-002 | FR-004 | `test_semantic_drift_fails_only_the_semantics_gate` | **VALIDATED** |
| UC-003 | FR-010 | `test_baseline_passes_all_gates` | **VALIDATED** |
| UC-004 | FR-013 | `test_verified_heal_is_auto_approved_and_versions_bump` | **VALIDATED** |
| UC-005 | FR-016 | `test_garbage_preview_is_auto_rejected_never_trusted` | **VALIDATED** |
| UC-006 | FR-017 | `test_gray_band_lands_in_review_and_human_approval_uses_same_api` | **VALIDATED** |
| UC-007 | FR-018 | same | **VALIDATED** |
| UC-008 | FR-021 | `test_full_lifecycle_across_all_drift_classes` | **VALIDATED** |
| UC-009 | FR-022 | E2E (indirect) | **IMPLEMENTED** |
| UC-010 | FR-020 | `test_full_lifecycle_across_all_drift_classes` | **VALIDATED** |
| UC-011 | FR-026 | — | **UNVALIDATED** |
| UC-012 | FR-024 | `test_full_lifecycle_across_all_drift_classes` | **PARTIAL** |
| UC-013 | FR-030 | `test_invalid_variant_rejected` | **VALIDATED** |
| UC-016 | FR-025 | — | **UNVALIDATED** |

---

**Next:** [SRS](../02_Requirements/SRS.md) · [Traceability Matrix](../02_Requirements/Requirements_Traceability_Matrix.md)
