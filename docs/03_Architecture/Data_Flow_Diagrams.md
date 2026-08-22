# Data Flow Diagrams

[← Documentation index](../README.md) · [← HLD](HLD.md)

---

## DFD Level 0 — Context

```mermaid
flowchart TB
  ENG([Engineer])
  MGR([Engineering Manager])
  BD[/Bright Data<br/>Scraper Studio/]
  AN[/Anthropic API<br/>optional/]
  SL[/Slack<br/>optional/]
  REPO[(Connected repo<br/>read-only)]
  DW{{DriftWatch}}

  ENG -->|source definition, contract YAML| DW
  MGR -->|approve / reject heal| DW
  DW -->|drift events, verdicts, cost, call sites| MGR
  DW -->|create / run / heal / approve / discover| BD
  BD -->|payloads, previews, candidates| DW
  DW -->|change description| AN
  AN -->|prose only| DW
  DW -->|alert text| SL
  REPO -->|source file contents| DW
```

**Trust note.** Only two inbound flows are trusted: the engineer's contract YAML and the manager's decision. Everything from Bright Data originates on a third-party web page and is **untrusted input**.

---

## DFD Level 1 — Major flows

```mermaid
flowchart TB
  subgraph TB1[TRUST BOUNDARY 1 — Network · auth opt-in, off by default]
    P1[1.0 HTTP API]
  end

  subgraph internal[Application internals]
    P2[2.0 Run pipeline]
    P3[3.0 Evaluate contract]
    P4[4.0 Diff & classify]
    P5[5.0 Diagnose & heal]
    P6[6.0 Verify repair]
    P7[7.0 Assess impact]
    P8[8.0 Alert]
  end

  D1[(D1 sources / scrapers)]
  D2[(D2 snapshots)]
  D3[(D3 drift_events)]
  D4[(D4 heal_events)]
  D5[(D5 impact_reports)]
  D6[(D6 alerts)]
  D7[(D7 audit_events)]
  F1[/F1 contracts YAML/]
  F2[/F2 fixtures/]

  EXT[/Bright Data/]
  REPO[(Repo)]

  P1 --> P2
  SCHED([Scheduler]) --> P2
  P2 -->|collector_id, url| EXT
  EXT -->|payload| P2
  F1 --> P3
  F2 -.replay.-> EXT
  P2 --> P3
  P3 -->|Verdict| P2
  P2 -->|pass| P4
  P2 -->|structural fail| P5
  P5 -->|prompt| EXT
  EXT -->|preview| P6
  P6 --> P3
  P6 -->|Verdict| P5
  P5 -->|approve/reject| EXT

  P2 --> D1
  P2 --> D2
  P4 --> D3
  P5 --> D4
  P4 -->|class 3/4| P7
  REPO --> P7
  P7 --> D5
  P7 --> P8
  P8 --> D6
  P2 & P4 & P5 & P7 & P8 --> D7
```

### Store write matrix

| Store | Written by | Read by |
|---|---|---|
| D1 sources/scrapers | 1.0 onboard, 5.0 version bump | 2.0, API |
| D2 snapshots | 2.0 | 2.0 (last-known-good), API |
| D3 drift_events | 2.0/4.0 | API |
| D4 heal_events | 5.0 | 5.0, API |
| D5 impact_reports | 7.0 | API |
| D6 alerts | 8.0 | API |
| D7 audit_events | **all** | API (append-only) |

---

## DFD Level 2 — Contract evaluation (process 3.0)

```mermaid
flowchart LR
  IN[/payload/] --> G1[3.1 Schema gate<br/>Draft 2020-12]
  IN --> G2[3.2 Invariants gate<br/>range · enum · non_null · cardinality]
  IN --> G3[3.3 Semantics gate<br/>anchor match on unit_context]
  IN --> G4[3.4 Continuity gate<br/>vs last-known-good]
  SPEC[/contract spec/] --> G1 & G2 & G3 & G4
  LG[(last-known-good)] --> G2 & G4

  G1 -->|score, weight 0.35| AGG[3.5 Compose verdict]
  G2 -->|score, weight 0.25| AGG
  G3 -->|score, weight 0.25| AGG
  G4 -->|score, weight 0.15| AGG
  AGG --> OUT[/Verdict:<br/>passed = all gates<br/>confidence = Σ w·score<br/>failing_fields/]
```

The four gates are **independent** — none reads another's result. That independence is what allows the classifier to distinguish "shape broke" from "meaning broke" by inspecting which gate failed.

---

## DFD Level 2 — Impact assessment (process 7.0)

```mermaid
flowchart LR
  CH[/FieldChange list/] --> E[7.1 entities_from_changes<br/>regex on path + endpoint values]
  E -->|entity labels| SC[7.2 scan_repo<br/>literal match, 9 extensions]
  REPO[(repo files)] --> SC
  SC --> SITES[/CallSite: file, line, snippet, entity/]

  CH --> CO{7.3 estimate}
  USAGE[/usage.yaml/] --> CO
  CO -->|MATERIAL| M[7.4 _material_delta<br/>Δprice × volume]
  CO -->|SEMANTIC| U[7.5 _unit_flip_delta<br/>price × newly-billed volume]
  M --> COST[/monthly_delta + basis/]
  U --> COST

  SITES --> NOTE[7.6 migration_note]
  COST --> NOTE
  NOTE --> REP[(impact_reports)]
```

7.5 is the interesting path: it produces a dollar figure for a change where **no numeric value moved at all**, by applying the unchanged price to volume that was previously not billed.
Evidence: `impact/cost.py :: _unit_flip_delta`

---

## Untrusted data flow — the security-relevant view

This traces third-party page content through the system. It is the basis for [Threat Model T-08](../06_Security/Threat_Model.md).

```mermaid
flowchart TB
  PAGE[/Third-party page<br/>UNTRUSTED/]:::untrusted
  PAGE --> EX[Scraper Studio extraction]
  EX --> PAY[/payload/]:::untrusted
  PAY --> SNAP[(snapshots)]:::untrusted
  SNAP --> LG[/last-known-good/]:::untrusted

  LG --> DIAG[diagnoser<br/>expected_examples]
  DIAG --> COMP[composer]
  COMP --> PROMPT[/heal prompt/]:::danger
  PROMPT --> BDAI[/Bright Data AI<br/>regenerates extraction code/]:::danger

  PAY --> DIFF[differ] --> AIPROV[AnthropicProvider<br/>drift_summary]:::danger
  PAY --> API2[JSON API] --> SPA[SPA rendering]:::caution

  classDef untrusted fill:#5a2d2d,stroke:#c66,color:#fff
  classDef danger fill:#6b2020,stroke:#e55,color:#fff
  classDef caution fill:#5a4a1f,stroke:#cc4,color:#fff
```

Three sinks receive untrusted content with **no sanitisation**:

| Sink | Path | Consequence |
|---|---|---|
| Heal prompt → vendor AI | `snapshots.payload` → `diagnoser.expected_examples` → `composer` → `heal_scraper()` | Page content becomes instructions to an AI that generates executable extraction logic |
| Anthropic prompt | `FieldChange.before/after` → `drift_summary()` | Standard prompt injection into alert prose |
| SPA | `payload` → `/api/events/<id>` → DOM | XSS if any render path misses `esc()` |

The first is the most serious and is genuinely novel as a risk class: **indirect prompt injection where the injected content influences generated scraping code.** No mitigation exists (SEC-007, AI-006 both **NOT IMPLEMENTED**).

---

**Next:** [ADRs](ADRs/README.md) · [Threat Model](../06_Security/Threat_Model.md)
