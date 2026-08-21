# Driftwatch — Architecture

Two deployables, one database, zero microservices. Every design choice optimizes for one property:
**judges (and engineers) can audit the whole system in an afternoon.**

## The pipeline state machine

Every scheduled run is a row in `runs` walking explicit, persisted states. Every transition writes an
append-only `audit_events` row.

```
SCHEDULED → SCRAPING → VALIDATING
  ├─ fetch dead ──────────────► RELOCATING (discover) ─► REVIEW              [Class 5]
  ├─ contract broken ─────────► DIAGNOSING → HEALING → VERIFYING
  │                               ├─ conf ≥ 0.90 ► APPROVING → RERUNNING ─► PUBLISHED   [Class 1]
  │                               ├─ 0.50–0.90 ──► REVIEW (human, same approve API)
  │                               └─ conf ≤ 0.50 ► reject → retry once → QUARANTINED
  ├─ meaning shifted ─────────► REVIEW (quarantined + alerted + priced)      [Class 4]
  └─ verdict passes ──────────► DIFFING → CLASSIFYING [→ IMPACT → ALERTING] → PUBLISHED [0/2/3]
```

Invariant: **a snapshot that failed its contract is quarantined and never served to analytics,
alerts, or the UI's "latest verified snapshot."** The dashboard cannot lie.

## The Semantic Contract Engine (`contracts/`)

A contract per source (`fixtures/contracts/*.yaml`) = four gates, one weighted confidence:

| Gate | Checks | Weight |
|---|---|---|
| schema | JSON Schema (Draft 2020-12): required fields, types | 0.35 |
| invariants | ranges, enums, non-null, cardinality-drop | 0.25 |
| semantics | **unit anchors**: page text captured next to each value must still assert the contracted meaning | 0.25 |
| continuity | plausibility vs last-known-good: max % change, cardinality floors | 0.15 |

The semantics gate is the Class 4 tripwire: `price_input_per_1m: 2.50` extracts identically before
and after a page silently redefines the unit — but the captured `unit_context` ("USD per 1M input
tokens" → "…input + output combined") stops matching the contract's anchors. Schema green, meaning
red.

`evaluate()` is used in **both** places that matter: validating fresh extractions AND verifying heal
previews. One definition of correctness.

## The autonomous heal orchestrator (`healing/`)

Bright Data's `scraper heal` is deliberately human-shaped: a human notices breakage, writes a ≤1000
character prompt, reviews a `preview_result` at an `awaiting_approval` gate, then runs
`scraper approve`. Driftwatch closes that loop:

1. **detect** — the contract verdict fails (or required-leaf coverage collapses below 70%).
2. **diagnose** — exact failing fields + expected examples pulled from the last-known-good snapshot.
3. **compose** — a deterministic, length-guarded heal prompt built from the diagnosis (the "human
   description of what's wrong", machine-written).
4. **heal** — `scraper heal <collector_id> "<prompt>"` (replay: simulated with identical envelope
   shapes, including the approval gate).
5. **verify** — the preview is replayed against the full contract, *including continuity vs
   last-known-good*. A heal that "works" but returns implausible values fails here.
6. **decide** — three bands: auto-approve (≥0.90) → version bump → verification re-run;
   gray band → human Review Queue (whose buttons drive the *same* approve/reject API);
   auto-reject (≤0.50) → one retry with the failure appended to the prompt, then quarantine.

Rollback is version pinning: `scrapers.active_version` only advances after a verified re-run; a
rejected heal leaves the previous template active.

## The Bright Data seam (`brightdata/`)

`protocol.BrightDataClient` is the only surface the pipeline sees:
`create_scraper / run_scraper(version=…) / heal_scraper / approve(reject=…) / discover`.

- **ReplayClient** (default): recorded envelope shapes + a `WorldState` that says what each mirrored
  page currently looks like (`v1_baseline → v2_redesign → v3_semantic → v4_material → v5_gone`) and
  which variants the "template" has been healed for. Deterministic, offline, test-grade.
- **LiveClient** (`DW_MODE=live`): wraps the official `@brightdata/cli` (`--json` envelopes), which
  already handles auth, AI-Flow polling, the 3-concurrent-job cap and backoff. The CLI's documented
  envelopes (`collector_id`, `awaiting_approval`, `preview_result`, `diff_summary`) are the shared
  contract between both implementations.

## Impact Graph (`impact/`)

Deliberate 7-day scope: literal entity scanning. Entities are extracted from drift-event field paths
(`models[nimbus-large-2].price…` → `nimbus-large-2`) and endpoint-shaped values (`/v2/charges`),
then grepped across the connected repo (`fixtures/sample-repo`) → file/line/snippet call sites.
Cost deltas come from a declared usage profile (`usage.yaml`):

- Material price change: `Δ price/1M × declared monthly M-tokens` (e.g. **+$412/mo**).
- Semantic unit flip: the same price now billed on the wider base → `price × output volume`
  (e.g. **+$626/mo**). The number didn't move; the bill did.

## LLM seam (`llm/`)

Deterministic `HeuristicProvider` by default — the entire system runs and tests offline with zero
keys and zero variance. `ANTHROPIC_API_KEY` upgrades drift summaries and migration notes to model
prose (`AnthropicProvider`, graceful fallback). Decisions never depend on the LLM; only wording does.

## Persistence

SQLite (WAL) via a thin typed helper — tables: `sources, contracts, scrapers, runs, snapshots,
drift_events, heal_events, impact_reports, alerts, audit_events`. Vanilla SQL, JSON columns for
payloads; Postgres is a driver swap. The scheduler is a stdlib thread whose "queue" is the runs
table — restart-safe and visible in the product.

## Frontend

Zero-build vanilla ES modules + hand-rolled SVG. Palette validated with the repo's data-viz method
(all-pairs CVD + contrast on the dark surface); every drift-class mark pairs **color + glyph +
label** — identity never rides on color alone. Views: The Living Web (radial dependency map),
Source Seismograph, Drift Events (before/after diff + verification verdict + blast radius),
Heal Center (gate sequence + review queue), Audit Ledger. Single origin with the API and the mirror
site; polling for liveness; `prefers-reduced-motion` respected.

## Error taxonomy

`FetchError / ContractViolation / HealRejected / BudgetExceeded / BrightDataError / ConfigError` —
every failure mode maps to a visible pipeline state; no bare exceptions cross module boundaries.

## Testing

23 unittest cases: contract gates, entity-resolved differ, classifier per class, heal-loop
(auto-approve, garbage-preview auto-reject, gray-band review + human decision), API smoke, and an
end-to-end mirror-break test that walks **all five drift classes** through the full state machine —
the hackathon's central question, answered in CI.
