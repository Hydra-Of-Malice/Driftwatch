# Test Cases

[← Documentation index](../README.md) · [← Test Strategy](Test_Strategy.md)

---

All 23 tests, mapped to requirements. **Actual result and status reflect an execution performed during this review** on Windows 11 / Python 3.13.11, and the same suite passing in CI on `ubuntu-latest` / Python 3.11.

```
Ran 23 tests in 0.385s — OK
```

---

## Contract engine — `test_contracts.py`

| ID | Requirement | Scenario | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-01 | FR-005, FR-010 | Baseline passes all four gates | `v1_baseline.json` | `passed=True`, all gates pass | As expected | **PASS** |
| TC-02 | FR-005, FR-012 | Broken extraction fails schema and coverage | `v2_redesign.broken.json` | Schema gate fails; coverage below threshold | As expected | **PASS** |
| TC-03 | **FR-004** | **Unit flip fails only the semantics gate** | `v3_semantic.json` | schema ✅ invariants ✅ **semantics ❌** | As expected | **PASS** |
| TC-04 | FR-007 | Continuity flags an implausible jump | Payload with a value beyond `max_change_pct` | Continuity gate fails | As expected | **PASS** |
| TC-05 | FR-006 | Range and enum invariants | Out-of-range price; invalid status | Invariants gate fails, fields listed | As expected | **PASS** |
| TC-06 | FR-008 | First snapshot passes continuity vacuously | `last_good=None` | Continuity passes with "vacuous pass" detail | As expected | **PASS** |

**TC-03 is the system's thesis test.** It proves the semantic gate isolates meaning drift from shape drift on a payload that every other validator would accept.

---

## Differ and classifier — `test_drift.py`

| ID | Requirement | Scenario | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-07 | FR-020b | Reordering entities is not a change | Same models, permuted order | `diff() == []` | As expected | **PASS** |
| TC-08 | FR-020b | Change paths carry entity labels | One price changed | Path contains `[nimbus-large-2]` not `[0]` | As expected | **PASS** |
| TC-09 | FR-020b | Added and removed entities detected | Model added; model removed | One `added`, one `removed` | As expected | **PASS** |
| TC-10 | FR-020a | Availability wins precedence | `fetch_failed=True` | `DriftClass.AVAILABILITY` | As expected | **PASS** |
| TC-11 | FR-012, FR-020a | Structural on schema/coverage failure | Failing verdict, low coverage | `DriftClass.STRUCTURAL`, critical | As expected | **PASS** |
| TC-12 | **FR-020a** | **Semantic beats material** | Semantics failed **and** a watched field changed | `DriftClass.SEMANTIC` | As expected | **PASS** |
| TC-13 | FR-020a | Material with severity escalation | Significant field changed > 10% | `MATERIAL`, `critical` | As expected | **PASS** |
| TC-14 | FR-025a | Benign change does not alert | Non-significant field changed | `BENIGN`, severity `info` | As expected | **PASS** |
| TC-15 | FR-020a | No change | Identical payloads | `DriftClass.NONE` | As expected | **PASS** |

**TC-12 encodes the precedence principle.** When both a meaning shift and a value change are present, the meaning shift wins — because a value you cannot interpret is not a value you can report as changed.

---

## Heal loop — `test_healing.py`

| ID | Requirement | Scenario | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-16 | FR-014, FR-015 | Prompt is specific and within limit | Diagnosis with failing fields | `len ≤ 1000`; names fields, coverage, examples | As expected | **PASS** |
| TC-17 | FR-013, FR-017, FR-019a | Verified heal auto-approves and bumps version | Redesign; preview matches truth | `status=approved`; `active_version` 1→2 | As expected | **PASS** |
| TC-18 | **FR-016, FR-018** | **Garbage preview is auto-rejected, never trusted** | Sabotaged preview via `world.sabotage_preview` | `status=rejected`; **version unchanged** | As expected | **PASS** |
| TC-19 | FR-019 | Gray band → review; human approval uses the same API | Preview verifying between thresholds | `status=review`; `decide_review` bumps version, records `human_approved` | As expected | **PASS** |

**TC-18 is the most important test in the repository.** It is the falsifiable form of the project's central claim: a repair that cannot be re-proven is refused, and the production template does not move. Delete `verify_preview()` and this test fails.

---

## API — `test_api.py`

| ID | Requirement | Scenario | Expected | Actual | Status |
|---|---|---|---|---|---|
| TC-20 | FR-029 | Sources list and run flow | `GET /api/sources` returns seeded sources; `POST /api/run/<id>` returns a summary | As expected | **PASS** |
| TC-21 | FR-030 | Demo state drives the world; events flow | Setting a variant changes extraction; events appear | As expected | **PASS** |
| TC-22 | FR-030 | Invalid variant rejected | `400` with an error naming the allowlist | As expected | **PASS** |

**Coverage note: 3 of 19 routes.** `POST /api/review/<id>`, `POST /api/run-all`, `POST /api/onboard`, and all detail endpoints are untested at the HTTP layer.

---

## End-to-end — `test_e2e_pipeline.py`

### TC-23 — Full lifecycle across all five drift classes

**Requirement:** FR-011, FR-013, FR-020, FR-021, FR-024, FR-027
**Preconditions:** Fresh DB, two seeded sources, replay world at `v1_baseline`

| Step | Action | Assertion |
|---|---|---|
| 1 | Run at baseline | Published; verdict passes |
| 2 | Set `v2_redesign`, run | Class 1; healed; version bumped; published |
| 3 | Set `v3_semantic`, run | Class 4; snapshot quarantined; alert raised |
| 4 | Run PayFlux at `v4_material` | Class 3; published; `impact_reports.affected` contains **`src/payments.py`** |
| 5 | Set NimbusAI `v4_material`, run | Class 3; `cost_delta_monthly == 412.0` exactly |
| 6 | Set `v5_gone`, run | Class 5; relocation candidates recorded |

**Actual:** All assertions pass. **Status: PASS**

Two assertions are worth singling out:

- **Step 4** asserts a POSIX path. This test **failed on Windows** before this review, because `scanner.py` emitted `src\payments.py`. CI never caught it (`ubuntu-latest` only). Fixed in commit `f0c9b7b`.
- **Step 5** asserts an exact float, `412.0`, derived from `(0.90 × 320) + (0.50 × 248)`. Pinning the arithmetic rather than a range means a cost-model regression cannot pass silently.

---

## Manual verification performed during this review

Not part of the automated suite; executed against a live server and recorded here as evidence.

| ID | Scenario | Method | Result |
|---|---|---|---|
| MV-01 | Server boots from a clean DB | `python backend/serve.py` | ✅ Up in ~1 s |
| MV-02 | All five classes over HTTP | `POST /api/demo/state` + `POST /api/run/<id>` per variant | ✅ Classes 0,1,4,3,5 with expected states |
| MV-03 | Class 1 heals autonomously | `v2_redesign` | ✅ `healed: true`, published |
| MV-04 | Class 3 prices correctly | `v4_material` | ✅ `cost_delta_monthly: 412.0` |
| MV-05 | Impact paths are POSIX on Windows | Query `impact_reports.affected` | ✅ No backslash paths |
| MV-06 | SPA and assets serve | `GET /`, `/assets/{app.js,styles.css,viz.js}` | ✅ 200 |
| MV-07 | Mirror serves both sources | `GET /mirror/<id>` | ✅ 200 |
| MV-08 | `v5_gone` returns 404 by design | `GET /mirror/nimbusai-pricing` at `v5_gone` | ✅ 404 |
| MV-09 | Lint clean | `ruff check backend` | ✅ All checks passed |
| MV-10 | CI green | GitHub Actions run | ✅ success, 20 s |

---

## Requirement coverage from tests

| Requirement | Test |
|---|---|
| FR-004 | TC-03 |
| FR-005 | TC-01, TC-02 |
| FR-006 | TC-05 |
| FR-007 | TC-04 |
| FR-008 | TC-06 |
| FR-010 | TC-01 |
| FR-011 | TC-23 |
| FR-012 | TC-02, TC-11 |
| FR-013 | TC-17, TC-23 |
| FR-014, FR-015 | TC-16 |
| FR-016 | TC-18 |
| FR-017 | TC-17 |
| FR-018 | TC-18 |
| FR-019, FR-019a | TC-19, TC-17 |
| FR-020a | TC-10…TC-15 |
| FR-020b | TC-07, TC-08, TC-09 |
| FR-020 | TC-23 |
| FR-021 | TC-23 |
| FR-024 | TC-23 |
| FR-025a | TC-14 |
| FR-027 | TC-23 |
| FR-029 | TC-20 |
| FR-030 | TC-22 |

**Untested requirements:** FR-001, FR-002 (direct), FR-003, FR-009 (direct), FR-022 (value), FR-023, FR-025 (Slack), FR-026, FR-028, FR-031 (automated), FR-032, and all REL-*, OBS-*, SEC-* except SEC-003.

---

**Next:** [Performance Validation](Performance_Validation.md) · [Traceability Matrix](../02_Requirements/Requirements_Traceability_Matrix.md)
