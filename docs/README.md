# DriftWatch — Engineering Documentation

Complete technical documentation for DriftWatch. Every claim here is traceable to source code, configuration, or a test; see [Evidence & Status Conventions](#evidence--status-conventions) for how claims are labelled.

**Start here:** [Executive Summary](EXECUTIVE_SUMMARY.md) — the whole system in 3 minutes.
**Hackathon submission:** [AI Usage Disclosure](AI_USAGE.md) · [Scraper Studio usage](SCRAPER_STUDIO.md) · [Demo script](DEMO.md)

---

## Navigation

### 01 — Product
| Document | What it covers |
|---|---|
| [Problem Statement](01_Product/Problem_Statement.md) | Silent scraper failure, semantic drift, who it hurts |
| [Project Vision](01_Product/Project_Vision.md) | Mission, objectives, success criteria |
| [User Personas](01_Product/User_Personas.md) | Four personas with goals and system needs |
| [User Journey](01_Product/User_Journey.md) | Onboarding → steady state → drift event → resolution |
| [Use Cases](01_Product/Use_Cases.md) | UC-001…UC-012, actor → action → behaviour → outcome |
| [Scope](01_Product/Scope.md) | In scope, out of scope, assumptions, constraints |
| [Competitive Analysis](01_Product/Competitive_Analysis.md) | Versus monitoring, diffing, and scraping platforms |
| [USP & Novelty](01_Product/USP_Novelty.md) | Rigorous separation of genuine novelty from combination |

### 02 — Requirements
| Document | What it covers |
|---|---|
| [SRS](02_Requirements/SRS.md) | FR-001…FR-032, NFR/SEC/PERF/REL/AI requirements |
| [Traceability Matrix](02_Requirements/Requirements_Traceability_Matrix.md) | Requirement → design → code → test → evidence |
| [Requirements Gap Analysis](02_Requirements/Requirements_Gap_Analysis.md) | Untraceable requirements, prioritised |

### 03 — Architecture
| Document | What it covers |
|---|---|
| [High-Level Design](03_Architecture/HLD.md) | Context, containers, architectural style, boundaries |
| [Low-Level Design](03_Architecture/LLD.md) | Contract engine, classifier, differ, heal orchestrator |
| [Sequence Diagrams](03_Architecture/Sequence_Diagrams.md) | Run, heal, semantic catch, relocation, human review |
| [Data Flow Diagrams](03_Architecture/Data_Flow_Diagrams.md) | DFD levels 0–2 with trust boundaries |
| [Architecture Decision Records](03_Architecture/ADRs/README.md) | ADR-001…ADR-012 with honest rationale labelling |

### 04 — Data
| Document | What it covers |
|---|---|
| [Database Design](04_Data/Database_Design.md) | ER diagram, all 10 tables, data dictionary, indexing analysis |

### 05 — API
| Document | What it covers |
|---|---|
| [API Documentation](05_API/API_Documentation.md) | All 19 routes with requests, responses, side effects |
| [API Error Catalog](05_API/API_Error_Catalog.md) | Error taxonomy and HTTP mapping |

### 06 — Security
| Document | What it covers |
|---|---|
| [Security Architecture](06_Security/Security_Architecture.md) | What exists, what does not — no aspirational claims |
| [Threat Model](06_Security/Threat_Model.md) | STRIDE, including indirect prompt injection via scraped content |
| [Risk Register](06_Security/Risk_Register.md) | Ranked technical, security, and demo risks |

### 07 — Testing & Performance
| Document | What it covers |
|---|---|
| [Test Strategy](07_Testing/Test_Strategy.md) | Layers, tooling, coverage analysis, gaps |
| [Test Cases](07_Testing/Test_Cases.md) | All 23 tests mapped to requirements |
| [Performance Validation](07_Testing/Performance_Validation.md) | Measured latencies, methodology, unmeasured areas |

### 08 — Deployment
| Document | What it covers |
|---|---|
| [Deployment Architecture](08_Deployment/Deployment_Architecture.md) | Actual topology, environments, configuration |
| [CI/CD](08_Deployment/CI_CD.md) | The real pipeline, plus a recommended production one |

### 09 — AI/ML
| Document | What it covers |
|---|---|
| [AI Architecture](09_AI_ML/AI_Architecture.md) | Model inventory, pipeline, prompt architecture, safety |
| [Model Limitations](09_AI_ML/Model_Limitations.md) | Known failure modes, stated plainly |

### 10 — Operations
| Document | What it covers |
|---|---|
| [Observability](10_Operations/Observability.md) | Audit ledger, what operators can and cannot see |
| [Reliability & Failure Design](10_Operations/Reliability_and_Failure_Design.md) | Per-dependency failure behaviour, DR posture |

### 11 — Assessment
| Document | What it covers |
|---|---|
| [Judge Evaluation](11_Assessment/Judge_Evaluation.md) | Adversarial review against the six judging criteria |
| [Production Readiness](11_Assessment/Production_Readiness.md) | 0–5 maturity scores per category, justified |
| [Engineering Gap Report](11_Assessment/Engineering_Gap_Report.md) | Top gaps ranked by impact × feasibility |
| [Demo Runbook](11_Assessment/Demo_Runbook.md) | Reproducible demo with exact commands |

---

## Evidence & Status Conventions

Every substantive claim carries one of these labels. They are never mixed.

| Label | Meaning |
|---|---|
| **IMPLEMENTED** | Verified present in the repository, with a file reference |
| **VALIDATED** | Implemented *and* covered by a test that actually passes |
| **PARTIALLY IMPLEMENTED** | Some of the capability exists; the rest does not |
| **UNVALIDATED** | Code exists but no test or measurement backs it |
| **NOT IMPLEMENTED** | Does not exist in the codebase |
| **PLANNED** | Stated intent, no implementation |
| **RECOMMENDED** | An engineering recommendation, not a description of the system |

Evidence is cited as a repository path, optionally with a symbol or line:

```
Evidence: apps/engine/driftwatch_engine/contracts/engine.py :: evaluate()
Evidence: apps/engine/tests/test_contracts.py::test_semantic_drift_fails_only_the_semantics_gate
```

### Two standing caveats

1. **The reference build runs in replay mode.** Bright Data calls are served by
   `ReplayClient` against recorded fixtures and a self-hosted mirror site. The live
   path (`LiveClient`) is implemented but **UNVALIDATED** — see
   [AI Architecture § Live-path validation status](09_AI_ML/AI_Architecture.md#live-path-validation-status).
2. **Seeded demo values are not measurements — resolved 2026-08-22.** `seed.py` still
   inserts a hardcoded `42.3s` demo heal event, but `/api/stats` now excludes it from
   the dashboard's headline MTTR (a real `heal_events.seeded` column, filtered out of
   the mean). A fresh demo now shows "no measured heal yet" until a real heal runs,
   rather than silently presenting the seed value as a timing observation. See
   [Performance Validation § What is not measured](07_Testing/Performance_Validation.md#what-is-not-measured).

---

## Reproducing every claim

```bash
pip install -r requirements.txt
make test        # 23 tests
make lint        # ruff
make demo        # http://localhost:8000
```
