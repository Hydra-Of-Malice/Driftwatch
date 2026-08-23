# Software Requirements Specification

[← Documentation index](../README.md)

---

## 1. Introduction

### 1.1 Purpose
Specifies functional and non-functional requirements for DriftWatch. Requirements are reverse-engineered from the implementation and labelled with verification status; this is a specification of **what the system does**, with gaps marked rather than hidden.

### 1.2 Scope
Covers the engine (`backend`), web client (`frontend`), contracts, fixtures, and mirror. Excludes Bright Data Scraper Studio internals and the Anthropic API.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| **Source** | A watched page with a URL, schedule, and contract |
| **Contract** | Schema + invariants + semantic assertions + continuity rules |
| **Gate** | One of four checks: schema, invariants, semantics, continuity |
| **Verdict** | Aggregate gate result with weighted confidence in `[0,1]` |
| **Snapshot** | One extraction payload with verdict and quarantine flag |
| **Drift class** | 0 none · 1 structural · 2 benign · 3 material · 4 semantic · 5 availability |
| **Heal** | Bright Data AI regeneration of an extraction template |
| **Preview** | Sample output returned at the heal approval gate |
| **Collector ID** | Scraper Studio scraper identifier (`c_*`) |
| **Quarantine** | Snapshot flagged so no consumer path reads it |
| **Last-known-good** | Most recent non-quarantined snapshot for a source |

### 1.4 Stakeholders
Platform Engineer (P1), AI Application Engineer (P2), Engineering Manager (P3), Evaluator (P4) — see [User Personas](../01_Product/User_Personas.md).

### 1.5 System overview
Single Flask process serving SPA, JSON API, and mirror on one origin; daemon-thread scheduler; SQLite (10 tables); Bright Data behind a Protocol seam with replay and live implementations.

### 1.6 Requirement conventions
IDs are stable. Every requirement is atomic and testable. Status uses the labels in [Evidence & Status Conventions](../README.md#evidence--status-conventions).

---

## 2. Functional Requirements

### 2.1 Source management

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| <a id="fr-001"></a>**FR-001** | The system shall create a Scraper Studio scraper from a natural-language description and persist the returned `collector_id` and `view_url`. | **IMPLEMENTED** | `api/app.py :: onboard` |
| **FR-002** | The system shall load a source's contract from `fixtures/contracts/<source_id>.yaml`. | **IMPLEMENTED** | `contracts/engine.py :: load_spec` |
| **FR-003** | The system shall execute a source's scraper at an interval no shorter than `schedule_minutes`. | **IMPLEMENTED** | `scheduler.py :: _due_sources` |

> **Gap.** FR-001 has no companion requirement for contract generation, because none exists. A source onboarded through the API cannot run until a human authors its YAML. See [Gap Analysis](Requirements_Gap_Analysis.md).

### 2.2 Contract evaluation

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| <a id="fr-004"></a>**FR-004** | The system shall fail the semantics gate when the captured unit-context text for a field matches none of its asserted anchors. | **VALIDATED** | `contracts/engine.py :: _gate_semantics`; `test_contracts.py::test_semantic_drift_fails_only_the_semantics_gate` |
| **FR-005** | The system shall validate each payload against the contract's JSON Schema (Draft 2020-12). | **VALIDATED** | `_gate_schema`; `test_broken_extraction_fails_schema_and_coverage` |
| **FR-006** | The system shall evaluate `range`, `enum`, `non_null`, and `cardinality_drop` invariants. | **VALIDATED** | `_gate_invariants`; `test_invariant_range_and_enum` |
| **FR-007** | The system shall flag numeric changes exceeding a field's `max_change_pct` against last-known-good. | **VALIDATED** | `_gate_continuity`; `test_continuity_flags_implausible_jumps` |
| **FR-008** | The continuity gate shall pass vacuously when no prior snapshot exists. | **VALIDATED** | `test_first_snapshot_has_vacuous_continuity` |
| **FR-009** | The system shall compute confidence as the weighted sum of gate scores (schema 0.35, invariants 0.25, semantics 0.25, continuity 0.15). | **IMPLEMENTED** | `GATE_WEIGHTS`; `evaluate()` |
| <a id="fr-010"></a>**FR-010** | The system shall publish without diffing when the content hash equals last-known-good and the verdict passes. | **VALIDATED** | `pipeline/runner.py`; `test_baseline_passes_all_gates` |
| <a id="fr-011"></a>**FR-011** | The system shall exclude quarantined snapshots from every consumer read path. | **VALIDATED** | `_last_good()`; `api/app.py :: source_detail`; `test_e2e_pipeline.py` |
| **FR-012** | The system shall compute required-leaf coverage and treat < 0.70 as structurally broken. | **VALIDATED** | `required_leaf_coverage`; `COVERAGE_COLLAPSE_THRESHOLD`; `test_structural` |

### 2.3 Healing

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| <a id="fr-013"></a>**FR-013** | On structural drift the system shall diagnose, compose a heal prompt, and invoke `heal_scraper` without human input. | **VALIDATED (replay)** | `healing/orchestrator.py :: run_heal` |
| **FR-014** | Heal prompts shall not exceed `heal_prompt_max_chars` (default 1000), truncating on a word boundary. | **VALIDATED** | `composer.py`; `test_prompt_is_specific_and_within_limit` |
| **FR-015** | The heal prompt shall name failing fields, coverage percentage, and last-known-good example values. | **VALIDATED** | `composer.py`; same test |
| <a id="fr-016"></a>**FR-016** | The system shall re-evaluate the heal preview against the **full** contract and use only that verdict to decide approval. | **VALIDATED** | `verifier.py`; `test_garbage_preview_is_auto_rejected_never_trusted` |
| <a id="fr-017"></a>**FR-017** | Heals verifying at confidence ≥ `auto_approve_threshold` shall be approved and the active version incremented. | **VALIDATED** | `test_verified_heal_is_auto_approved_and_versions_bump` |
| <a id="fr-018"></a>**FR-018** | Heals verifying at confidence ≤ `auto_reject_threshold` shall be rejected and retried once with a prompt naming the prior failure. | **VALIDATED** | `orchestrator.py` loop `for attempt in (1, 2)` |
| **FR-019** | Heals verifying between thresholds shall be queued for human review, applying the decision through the same approval API. | **VALIDATED** | `test_gray_band_lands_in_review_and_human_approval_uses_same_api` |
| **FR-019a** | The active scraper version shall advance only after a verified re-run; a failed heal shall leave the previous version active. | **IMPLEMENTED** | `orchestrator.py`; `runner.py :: _handle_structural` |

### 2.4 Drift classification

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| **FR-020a** | The system shall classify in precedence order: availability > structural > semantic > material > benign > none. | **VALIDATED** | `classifier.py :: classify`; 6 tests |
| **FR-020b** | The system shall diff snapshots by entity key, not list index. | **VALIDATED** | `differ.py`; `test_reordering_entities_is_not_a_change` |
| <a id="fr-020"></a>**FR-020** | The system shall identify call sites in a connected repository by literal entity matching across 9 file extensions. | **VALIDATED** | `impact/scanner.py`; E2E asserts `src/payments.py` |

### 2.5 Impact and alerting

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| <a id="fr-021"></a>**FR-021** | For material price changes the system shall compute monthly cost delta from declared usage volume. | **VALIDATED** | `impact/cost.py :: _material_delta`; E2E asserts `412.0` |
| <a id="fr-022"></a>**FR-022** | For semantic unit flips the system shall compute cost delta by applying the unchanged price to newly-billed volume. | **IMPLEMENTED** | `_unit_flip_delta` |
| **FR-023** | The system shall generate a migration note listing changed fields, touch points, and cost basis. | **IMPLEMENTED** | `llm/provider.py :: migration_note` |
| <a id="fr-024"></a>**FR-024** | On fetch failure the system shall request relocation candidates via `discover()` and record up to five. | **PARTIALLY IMPLEMENTED** | `runner.py :: _handle_unreachable` — no endpoint applies a candidate |
| <a id="fr-025"></a>**FR-025** | The system shall deliver in-app alerts for classes 3, 4, 5 and optionally to Slack. | **IMPL / UNVALIDATED** | `alerts.py` — Slack branch untested |
| **FR-025a** | The system shall not alert for classes 0, 1(resolved), and 2. | **VALIDATED** | `alerts.py` guard; `test_benign` |

### 2.6 Audit and state

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| <a id="fr-026"></a>**FR-026** | Every state transition, heal decision, and alert shall append a row to `audit_events` with actor, action, refs, payload, timestamp. | **IMPLEMENTED** | `db.py :: audit` |
| **FR-027** | The system shall persist runs through 17 explicit states. | **IMPLEMENTED** | `domain.py :: RunState` |
| **FR-028** | Audit records shall be append-only (no update or delete path). | **IMPLEMENTED** | No `UPDATE`/`DELETE` targets `audit_events` |

> **Note.** FR-028 is enforced by absence of code, **not by a database constraint**. A `GRANT`-level or trigger-level guarantee is **NOT IMPLEMENTED**.

### 2.7 API and UI

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| **FR-029** | The system shall expose the API documented in [API Documentation](../05_API/API_Documentation.md). | **IMPLEMENTED** | `api/app.py` — 19 routes |
| <a id="fr-030"></a>**FR-030** | The demo-state endpoint shall reject variants outside the allowlist with HTTP 400. | **VALIDATED** | `test_api.py::test_invalid_variant_rejected` |
| **FR-031** | The system shall serve SPA, API, and mirror from one origin. | **VALIDATED** | Verified: `/`, `/assets/*`, `/mirror/*`, `/api/*` all 200 |
| **FR-032** | The SPA shall present Living Web, Sources, Events, Heal Center, and Ledger views. | **IMPLEMENTED — UNVALIDATED** | `frontend/assets/app.js` — no frontend tests |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| **PERF-001** | Contract evaluation shall complete within 1 ms p95 for a 4-model payload. | **VALIDATED** | Measured p95 **0.20 ms** |
| **PERF-002** | A no-change pipeline run shall complete within 20 ms p95 in replay mode. | **VALIDATED** | Measured p95 **7.62 ms** |
| **PERF-003** | A structural-break heal cycle shall complete within 50 ms p95 in replay mode. | **VALIDATED** | Measured p95 **14.55 ms** |
| **PERF-004** | Live-mode latency shall be characterised. | **NOT IMPLEMENTED** | No live run has succeeded |
| **PERF-005** | Throughput under concurrent sources shall be characterised. | **NOT IMPLEMENTED** | Never tested beyond 2 sources |

Methodology and hardware: [Performance Validation](../07_Testing/Performance_Validation.md).

### 3.2 Reliability

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| **REL-001** | Alert delivery failure shall not fail the pipeline. | **IMPLEMENTED** | `alerts.py` try/except + audit |
| **REL-002** | A single source failure shall not stop the scheduler. | **IMPLEMENTED** | `scheduler.py` per-tick try/except |
| **REL-003** | LLM provider failure shall fall back to deterministic templates. | **IMPLEMENTED** | `AnthropicProvider._complete` returns `None` → `super()` |
| **REL-004** | A failed heal shall leave the source on its last good version. | **VALIDATED** | FR-019a evidence |
| **REL-005** | The system shall retry transient Bright Data failures with backoff. | **NOT IMPLEMENTED** | `LiveClient._cli` raises on non-zero exit; no retry |
| **REL-006** | The system shall enforce a Bright Data credit budget. | **NOT IMPLEMENTED** | `credit_budget` and `BudgetExceeded` defined but never read or raised |

### 3.3 Security

| ID | Requirement | Status |
|---|---|---|
| **SEC-001** | API endpoints shall require authentication. | **PARTIALLY IMPLEMENTED** — bearer-token gate exists (`api/app.py :: _require_auth`); opt-in via `DW_API_TOKEN`, not required by default |
| **SEC-002** | State-changing endpoints shall require authorisation. | **NOT IMPLEMENTED** — authentication only; no role/permission distinction exists between an authenticated caller and any other |
| **SEC-003** | Secrets shall not be committed. | **IMPLEMENTED** — `.env` gitignored; verified absent from history |
| **SEC-004** | Database access shall use parameterised queries for all user-supplied values. | **IMPLEMENTED** — `db.query/insert/update` bind values; table/column names are internal literals |
| **SEC-005** | Subprocess invocation shall avoid shell interpretation. | **IMPLEMENTED** — `subprocess.run` list form, no `shell=True` |
| **SEC-006** | Rate limiting shall protect expensive endpoints. | **NOT IMPLEMENTED** |
| **SEC-007** | Content supplied by scraped pages shall be treated as untrusted when composing prompts. | **NOT IMPLEMENTED** — see [Threat Model T-08](../06_Security/Threat_Model.md) |
| **SEC-008** | Security headers and CSRF protection shall be applied. | **NOT IMPLEMENTED** |

Full analysis: [Security Architecture](../06_Security/Security_Architecture.md).

### 3.4 Maintainability / Compatibility / Observability

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| **MNT-001** | Code shall pass `ruff` with the configured rule set (E, F, W, I, UP, B, SIM). | **VALIDATED** | CI green |
| **MNT-002** | External dependencies shall sit behind Protocol seams. | **IMPLEMENTED** | `BrightDataClient`, `Provider` |
| **CMP-001** | The system shall run on Python ≥ 3.10. | **VALIDATED** | CI matrix: {ubuntu-latest, windows-latest} x {3.10, 3.12} |
| **CMP-002** | The system shall behave identically on Windows and Linux. | **VALIDATED 2026-08-23** | `scanner.py` posix paths asserted, **and** the live path's two Windows-only defects fixed on 2026-08-23: `LiveClient` no longer replaces the child environment with a hardcoded POSIX `PATH` (`brightdata/live.py:99-103`) and resolves the CLI to the absolute `shutil.which` path so the `brightdata.cmd` npm shim launches (`brightdata/live.py:63-74`); pinned by `backend/tests/test_live_client.py:142`. *Correction: this row read **VALIDATED** before 2026-08-23, while [R-20](../06_Security/Risk_Register.md) correctly recorded the `PATH` bug as OPEN. The row was wrong when written; it is accurate now.* |
| **OBS-001** | Every automated decision shall be reconstructable from the ledger. | **IMPLEMENTED** | `audit_events` |
| **OBS-002** | The system shall expose operational metrics. | **PARTIALLY IMPLEMENTED** | `/api/stats` only; no Prometheus/OTel |
| **OBS-003** | The system shall expose a health endpoint. | **NOT IMPLEMENTED** | No `/healthz` |
| **OBS-004** | The system shall emit structured application logs. | **NOT IMPLEMENTED** | Flask default request log only |

### 3.5 AI-specific

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| **AI-001** | No pipeline state transition shall depend on a language model. | **IMPLEMENTED** | `HeuristicProvider` is the default; `Provider` methods return prose only |
| **AI-002** | LLM output shall never be used as a validation verdict. | **IMPLEMENTED** | `evaluate()` is pure rule evaluation |
| **AI-003** | LLM failure shall degrade prose quality only. | **IMPLEMENTED** | REL-003 evidence |
| **AI-004** | AI-generated extraction templates shall be verified before activation. | **VALIDATED** | FR-016 evidence |
| **AI-005** | Prompts shall be deterministic given the same diagnosis. | **IMPLEMENTED** | `compose_heal_prompt` is pure |
| **AI-006** | Scraped content entering prompts shall be sanitised. | **NOT IMPLEMENTED** | Last-known-good values flow into heal prompts unsanitised |

---

## 4. Constraints, assumptions, dependencies

See [Scope](../01_Product/Scope.md).

---

## 5. Summary

| Status | Count |
|---|---|
| **VALIDATED** | 27 |
| **IMPLEMENTED** (untested) | 18 |
| **PARTIALLY IMPLEMENTED** | 3 |
| **NOT IMPLEMENTED** | 13 |

The 13 unimplemented requirements cluster in security (8) and operations (4). That is a coherent picture: a system engineered for **correctness of data**, not yet for **operation as a service**.

---

**Next:** [Traceability Matrix](Requirements_Traceability_Matrix.md) · [Gap Analysis](Requirements_Gap_Analysis.md)
