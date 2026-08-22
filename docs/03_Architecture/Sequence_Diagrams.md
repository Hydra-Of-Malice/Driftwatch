# Sequence Diagrams

[← Documentation index](../README.md) · [← HLD](HLD.md)

---

Each diagram reflects the implementation. Every participant is a real module.

---

## SD-1 — Steady state: unchanged page (Class 0)

The cheapest path. Measured p50 **6.08 ms**.

```mermaid
sequenceDiagram
  participant SCH as Scheduler
  participant RUN as runner.run_source
  participant BD as BrightDataClient
  participant CE as contracts.evaluate
  participant DB as SQLite

  SCH->>RUN: run_source(source_id, deps)
  RUN->>DB: SELECT sources, scrapers
  RUN->>DB: load last-known-good (quarantined = 0)
  RUN->>DB: INSERT runs (state=SCRAPING)
  RUN->>DB: audit run.started
  RUN->>BD: run_scraper(collector_id, url, version)
  BD-->>RUN: RunResult(status=done, payload)
  RUN->>DB: UPDATE runs SET credits_spent
  RUN->>RUN: _set_state(VALIDATING)
  RUN->>CE: evaluate(payload, spec, last_good)
  CE-->>RUN: Verdict(passed=True, confidence)
  Note over RUN: hash(payload) == last_good.content_hash<br/>AND verdict.passed → fast path
  RUN->>DB: INSERT snapshots (quarantined=0)
  RUN->>RUN: _set_state(PUBLISHED)
  RUN-->>SCH: {class: 0, state: published}
```

No diff, no classification, no event. **Verified:** `v1_baseline` → `class: 0, state: published`.

---

## SD-2 — Structural break → autonomous heal (Class 1)

The headline loop. Measured p50 **12.22 ms** for the full cycle.

```mermaid
sequenceDiagram
  participant RUN as runner
  participant CE as contracts.evaluate
  participant DG as diagnoser
  participant CP as composer
  participant OR as orchestrator
  participant BD as BrightDataClient
  participant VF as verifier
  participant DB as SQLite

  RUN->>CE: evaluate(payload, spec, last_good)
  CE-->>RUN: Verdict(passed=False, coverage collapse)
  RUN->>DB: INSERT snapshots (quarantined=1)
  RUN->>DB: INSERT drift_events (class=1)
  RUN->>RUN: _set_state(DIAGNOSING)
  RUN->>DG: diagnose(verdict, payload, last_good, spec)
  DG-->>RUN: Diagnosis(failing_fields, examples, coverage)
  RUN->>RUN: _set_state(HEALING)
  RUN->>OR: run_heal(...)

  OR->>CP: compose_heal_prompt(attempt=1)
  CP-->>OR: prompt (≤1000 chars)
  OR->>DB: audit heal.requested
  OR->>BD: heal_scraper(collector_id, prompt, url)
  BD-->>OR: HealEnvelope(status=awaiting_approval, preview_result)

  rect rgb(235, 245, 235)
    Note over OR,VF: The heal's own success is NOT the criterion
    OR->>VF: verify_preview(preview, spec, last_good)
    VF->>CE: evaluate(preview, spec, last_good)
    CE-->>VF: Verdict
    VF-->>OR: Verdict(passed, confidence)
  end

  OR->>DB: INSERT heal_events (status=verifying)
  OR->>DB: audit heal.preview_verified

  alt passed AND confidence >= 0.90
    OR->>BD: approve(collector_id)
    OR->>DB: UPDATE scrapers SET active_version += 1
    OR->>DB: UPDATE heal_events (auto_approved, mttr_seconds)
    OR-->>RUN: HealOutcome(approved, new_version)
    RUN->>RUN: _set_state(RERUNNING)
    RUN->>BD: run_scraper(version=new_version)
    BD-->>RUN: RunResult(payload)
    RUN->>CE: evaluate(rerun payload)
    CE-->>RUN: Verdict(passed=True)
    RUN->>DB: INSERT snapshots (quarantined=0)
    RUN->>DB: audit heal.rerun_verified
    Note over RUN: healed page may also carry a real change → classify it
    RUN-->>RUN: _publish_and_classify(healed=True)
  else confidence <= 0.50
    OR->>BD: approve(reject=True)
    OR->>DB: UPDATE heal_events (auto_rejected)
    Note over OR: retry once, prompt now names the failure
  else gray band
    OR->>DB: UPDATE heal_events (status=review)
    Note over OR: vendor approval gate left OPEN for a human
  end
```

Two design points visible here:

1. The **green block** is the thesis. Verification calls the same `evaluate()` that detected the break.
2. After a successful heal the pipeline does **not** stop — it re-classifies, because a redesigned page may also carry a genuine data change.

**Verified:** `v2_redesign` → `class: 1, state: published, healed: true`.

---

## SD-3 — Semantic drift (Class 4) — the catch that matters

```mermaid
sequenceDiagram
  participant RUN as runner
  participant CE as contracts.evaluate
  participant DF as differ
  participant CO as cost
  participant SC as scanner
  participant AL as alerts
  participant DB as SQLite

  RUN->>CE: evaluate(payload, spec, last_good)
  Note over CE: schema ✅  invariants ✅<br/>semantics ❌  continuity ✅
  CE-->>RUN: Verdict(passed=False, semantics gate failed)

  rect rgb(250, 235, 235)
    Note over RUN,DB: Quarantined — never becomes the new baseline
    RUN->>DB: INSERT snapshots (quarantined=1)
  end

  RUN->>DF: diff(last_good, payload, entity_key)
  DF-->>RUN: [FieldChange(unit_context changed)]
  RUN->>DB: INSERT drift_events (class=4, severity=critical)
  RUN->>RUN: _set_state(IMPACT)
  RUN->>SC: scan_repo(sample_repo, entities)
  SC-->>RUN: [CallSite(file, line, snippet)]
  RUN->>CO: estimate(SEMANTIC, changes, usage)
  CO-->>RUN: CostEstimate(monthly_delta, basis)
  RUN->>DB: INSERT impact_reports
  RUN->>RUN: _set_state(ALERTING)
  RUN->>AL: send_alert(class=4, severity=critical, cost)
  AL->>DB: INSERT alerts (in_app)
  RUN->>RUN: _set_state(REVIEW)
```

The value never changed, so continuity passes and no statistical method would fire. Only the anchor assertion catches it.

**Verified:** `v3_semantic` → `class: 4, state: review`.

---

## SD-4 — Human review of a gray-band heal

```mermaid
sequenceDiagram
  actor MGR as Engineering Manager
  participant API as POST /api/review/{id}
  participant OR as orchestrator.decide_review
  participant BD as BrightDataClient
  participant RUN as runner
  participant DB as SQLite

  MGR->>API: {approve: true}
  Note over API: ⚠ AUTH OPT-IN, OFF BY DEFAULT — GAP-01 (mitigated 2026-08-22)
  API->>OR: decide_review(heal_id, approve=True, client)
  OR->>DB: SELECT heal_events WHERE id = ?
  alt status != 'review'
    OR-->>API: raise ValueError → HTTP 500
  end
  OR->>BD: approve(collector_id, reject=False)
  Note over OR,BD: same vendor call the machine path uses
  OR->>DB: UPDATE scrapers SET active_version += 1
  OR->>DB: UPDATE heal_events (human_approved, decided_by=human)
  OR->>DB: audit heal.human_approved
  OR-->>API: heal row
  API->>RUN: run_source(...) — verify immediately
  RUN-->>API: run summary
  API-->>MGR: heal JSON
```

Two observations:

- Machine and human converge on `client.approve()` — one vendor integration, two provenances.
- The `ValueError` for a non-review heal surfaces as an unhandled **500**, not a 409. See [API Error Catalog](../05_API/API_Error_Catalog.md).

---

## SD-5 — Page disappears (Class 5)

```mermaid
sequenceDiagram
  participant RUN as runner
  participant BD as BrightDataClient
  participant AL as alerts
  participant DB as SQLite

  RUN->>BD: run_scraper(collector_id, url)
  BD-->>RUN: RunResult(status=failed, http_status=404)
  RUN->>RUN: _set_state(RELOCATING)
  RUN->>BD: discover(query, intent)
  BD-->>RUN: DiscoverResult(candidates[])
  RUN->>DB: INSERT drift_events (class=5, up to 5 candidates)
  RUN->>AL: send_alert(class=5, severity=critical)
  AL->>DB: INSERT alerts
  RUN->>RUN: _set_state(REVIEW)
  Note over RUN,DB: ⚠ No endpoint applies a candidate — GAP-10
```

**Verified:** `v5_gone` → `class: 5, state: review`.

---

## SD-6 — Onboarding

```mermaid
sequenceDiagram
  actor ENG as Engineer
  participant API as POST /api/onboard
  participant BD as BrightDataClient
  participant RUN as runner
  participant CE as contracts.load_spec
  participant DB as SQLite

  ENG->>API: {id, name, url, description, vertical, schedule_minutes}
  alt missing url/description/name
    API-->>ENG: 400
  end
  API->>BD: create_scraper(url, description, name=source_id)
  BD-->>API: CreateEnvelope(collector_id, view_url, completed_steps)
  API->>DB: INSERT sources
  API->>DB: INSERT scrapers
  API->>DB: audit source.onboarded
  API->>RUN: run_source(source_id, deps)
  RUN->>CE: load_spec(source_id)
  alt contract YAML absent
    CE-->>RUN: FileNotFoundError → HTTP 500
    Note over CE,RUN: ⚠ GAP-04 — no contract is generated
  end
  RUN-->>API: first run summary
  API-->>ENG: {collector_id, view_url, ai_flow_steps, first_run}
```

This diagram documents a **broken** flow deliberately. For any genuinely new source, the run raises because no contract exists.

---

**Next:** [Data Flow Diagrams](Data_Flow_Diagrams.md) · [ADRs](ADRs/README.md) · [API Documentation](../05_API/API_Documentation.md)
