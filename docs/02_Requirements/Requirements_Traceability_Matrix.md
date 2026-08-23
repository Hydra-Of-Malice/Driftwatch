# Requirements Traceability Matrix

[← Documentation index](../README.md) · [← SRS](SRS.md)

---

Traces every requirement through **design → implementation → test → evidence**. A row with no test is a traceability gap and is marked as such.

Test file abbreviations: `TC` = `test_contracts.py`, `TD` = `test_drift.py`, `TH` = `test_healing.py`, `TE` = `test_e2e_pipeline.py`, `TA` = `test_api.py`. All under `backend/tests/`.

---

## Functional requirements

| Req | Design component | Implementation | Test | Status |
|---|---|---|---|---|
| FR-001 | Onboarding | `api/app.py :: onboard` | — | **IMPLEMENTED** |
| FR-002 | Contract loader | `contracts/engine.py :: load_spec` | TC (all, indirectly) | **VALIDATED** |
| FR-003 | Scheduler | `scheduler.py :: _due_sources` | — | **IMPLEMENTED** |
| FR-004 | Semantics gate | `contracts/engine.py :: _gate_semantics` | `TC::test_semantic_drift_fails_only_the_semantics_gate` | **VALIDATED** |
| FR-005 | Schema gate | `contracts/engine.py :: _gate_schema` | `TC::test_broken_extraction_fails_schema_and_coverage` | **VALIDATED** |
| FR-006 | Invariants gate | `contracts/engine.py :: _gate_invariants` | `TC::test_invariant_range_and_enum` | **VALIDATED** |
| FR-007 | Continuity gate | `contracts/engine.py :: _gate_continuity` | `TC::test_continuity_flags_implausible_jumps` | **VALIDATED** |
| FR-008 | Continuity vacuous pass | same | `TC::test_first_snapshot_has_vacuous_continuity` | **VALIDATED** |
| FR-009 | Confidence composition | `GATE_WEIGHTS`, `evaluate()` | — (values asserted indirectly in TH) | **IMPLEMENTED** |
| FR-010 | Unchanged fast path | `pipeline/runner.py` hash compare | `TC::test_baseline_passes_all_gates` | **VALIDATED** |
| FR-011 | Quarantine isolation | `runner.py :: _last_good` | `TE` | **VALIDATED** |
| FR-012 | Coverage collapse | `required_leaf_coverage`, `COVERAGE_COLLAPSE_THRESHOLD` | `TD::test_structural` | **VALIDATED** |
| FR-013 | Heal orchestration | `healing/orchestrator.py :: run_heal` | `TH::test_verified_heal_is_auto_approved_and_versions_bump` | **VALIDATED** |
| FR-014 | Prompt length guard | `healing/composer.py` | `TH::test_prompt_is_specific_and_within_limit` | **VALIDATED** |
| FR-015 | Prompt content | `healing/composer.py`, `diagnoser.py` | same | **VALIDATED** |
| FR-016 | Preview verification | `healing/verifier.py` | `TH::test_garbage_preview_is_auto_rejected_never_trusted` | **VALIDATED** |
| FR-017 | Auto-approve band | `orchestrator.py` | `TH::test_verified_heal_is_auto_approved_and_versions_bump` | **VALIDATED** |
| FR-018 | Auto-reject + retry | `orchestrator.py` attempt loop | `TH::test_garbage_preview_is_auto_rejected_never_trusted` | **VALIDATED** |
| FR-019 | Gray band → review | `orchestrator.py`, `decide_review` | `TH::test_gray_band_lands_in_review_and_human_approval_uses_same_api` | **VALIDATED** |
| FR-019a | Version pinning rollback | `orchestrator.py`, `runner.py :: _handle_structural` | `TH` (version asserted) | **VALIDATED** |
| FR-020a | Classification precedence | `drift/classifier.py :: classify` | `TD` ×6 | **VALIDATED** |
| FR-020b | Entity-resolved diff | `drift/differ.py` | `TD::test_reordering_entities_is_not_a_change`, `test_entity_keyed_change_paths` | **VALIDATED** |
| FR-020 | Call-site scanning | `impact/scanner.py :: scan_repo` | `TE` (asserts `src/payments.py`) | **VALIDATED** |
| FR-021 | Material cost delta | `impact/cost.py :: _material_delta` | `TE` (asserts `412.0`) | **VALIDATED** |
| FR-022 | Unit-flip cost delta | `impact/cost.py :: _unit_flip_delta` | `TE` (path exercised, value not asserted) | **IMPLEMENTED** |
| FR-023 | Migration note | `llm/provider.py :: migration_note` | — | **UNVALIDATED** |
| FR-024 | Relocation discovery | `runner.py :: _handle_unreachable` | `TE` (Class 5 asserted) | **PARTIAL** |
| FR-025 | Alert delivery | `alerts.py :: send_alert` | `TE` (in-app only) | **PARTIAL** |
| FR-025a | Zero-noise suppression | `alerts.py` guard | `TD::test_benign` | **VALIDATED** |
| FR-026 | Audit ledger | `db.py :: audit` | — | **UNVALIDATED** |
| FR-027 | Run states | `domain.py :: RunState` | `TE` (states asserted) | **VALIDATED** |
| FR-028 | Append-only | absence of UPDATE/DELETE | — | **UNVALIDATED** |
| FR-029 | API surface | `api/app.py` | `TA` ×3 (3 of 19 routes) | **PARTIAL** |
| FR-030 | Variant allowlist | `api/app.py :: demo_state` | `TA::test_invalid_variant_rejected` | **VALIDATED** |
| FR-031 | Single origin | `api/app.py` routes | Manual verification this review | **VALIDATED** |
| FR-032 | SPA views | `frontend/assets/app.js` | — | **UNVALIDATED** |

## Non-functional requirements

| Req | Implementation | Test / measurement | Status |
|---|---|---|---|
| PERF-001 | `contracts/engine.py` | Benchmark p95 0.20 ms | **VALIDATED** |
| PERF-002 | `pipeline/runner.py` | Benchmark p95 7.62 ms | **VALIDATED** |
| PERF-003 | `healing/orchestrator.py` | Benchmark p95 14.55 ms | **VALIDATED** |
| PERF-004 | `brightdata/live.py` | — | **NOT IMPLEMENTED** |
| PERF-005 | — | — | **NOT IMPLEMENTED** |
| REL-001 | `alerts.py` try/except | — | **UNVALIDATED** |
| REL-002 | `scheduler.py` try/except | — | **UNVALIDATED** |
| REL-003 | `provider.py` fallback | — | **UNVALIDATED** |
| REL-004 | version pinning | `TH` | **VALIDATED** |
| REL-005 | — | — | **NOT IMPLEMENTED** |
| REL-006 | — | — | **NOT IMPLEMENTED** |
| SEC-001 | `api/app.py :: _require_auth` | Manually verified 2026-08-22 (no token → 401, correct token → 200); no automated test | **PARTIALLY IMPLEMENTED** — opt-in, off by default |
| SEC-002 | — | — | **NOT IMPLEMENTED** |
| SEC-003 | `.gitignore` | Verified: no `.env` in history | **VALIDATED** |
| SEC-004 | `db.py` parameter binding | Code review this session | **IMPLEMENTED** |
| SEC-005 | `live.py` list-form subprocess | Code review this session | **IMPLEMENTED** |
| SEC-006…008 | — | — | **NOT IMPLEMENTED** |
| MNT-001 | `pyproject.toml` ruff config | CI green | **VALIDATED** |
| MNT-002 | Protocol seams | `TH`, `TE` use replay client | **VALIDATED** |
| CMP-001 | `requires-python` | CI matrix {ubuntu-latest, windows-latest} x {3.10, 3.12} | **VALIDATED** |
| CMP-002 | `scanner.py` posix paths | `TE` passes on Windows and CI | **VALIDATED** |
| OBS-001 | `audit_events` | — | **UNVALIDATED** |
| OBS-002 | `/api/stats` | `TA` (indirect) | **PARTIAL** |
| OBS-003…004 | — | — | **NOT IMPLEMENTED** |
| AI-001 | `HeuristicProvider` default | `TH`, `TE` run with heuristic provider | **VALIDATED** |
| AI-002 | `evaluate()` purity | All TC tests | **VALIDATED** |
| AI-003 | provider fallback | — | **UNVALIDATED** |
| AI-004 | `verifier.py` | `TH` | **VALIDATED** |
| AI-005 | `compose_heal_prompt` purity | `TH` | **VALIDATED** |
| AI-006 | — | — | **NOT IMPLEMENTED** |

---

## Coverage summary

| Metric | Value |
|---|---|
| Requirements traced to implementation | 51 / 64 (80%) |
| Requirements traced to a passing test | 33 / 64 (52%) |
| Requirements with no implementation | 13 |
| Implemented but untested | 18 |

## Untested implemented requirements — ranked

These represent the highest-value test additions. Each is code that exists and works but is not protected against regression.

| Priority | Req | Why it matters |
|---|---|---|
| **CRITICAL** | FR-026, FR-028 | The audit ledger is the system's integrity claim. Nothing tests that transitions are recorded or that records are never mutated |
| **CRITICAL** | REL-001, REL-002 | Both are "the system survives a failure" claims. Neither failure is ever induced in a test |
| **HIGH** | FR-025 (Slack) | Network branch, entirely untested |
| **HIGH** | FR-032 | 581 lines of untested UI |
| **HIGH** | REL-003 / AI-003 | LLM fallback never exercised |
| **MEDIUM** | FR-001, FR-003 | Onboarding and scheduling untested |
| **MEDIUM** | FR-023 | Migration-note generation untested |
| **MEDIUM** | FR-009 | Confidence weights asserted only indirectly |

## Reverse traceability — code without requirements

Modules with no governing requirement:

| Code | Note |
|---|---|
| `errors.py` (7 exception classes) | `BudgetExceeded`, `ContractViolation`, `HealRejected`, `FetchError` are **defined but never raised anywhere**. Dead taxonomy |
| `seed.py` (261 lines) | Demo data generation. Legitimately requirement-free, but it produces the `42.3s` MTTR figure the UI displays as if measured |
| `frontend/assets/viz.js` (257 lines) | Visualisation only |

> **Finding.** `errors.py` defines a careful error taxonomy that the pipeline does not use — it raises `ValueError` for unknown sources and lets `BrightDataError` through from the client. This is a real inconsistency between documented design intent and implementation. See [Gap Report G-07](../11_Assessment/Engineering_Gap_Report.md).

---

**Next:** [Gap Analysis](Requirements_Gap_Analysis.md) · [Test Strategy](../07_Testing/Test_Strategy.md)
