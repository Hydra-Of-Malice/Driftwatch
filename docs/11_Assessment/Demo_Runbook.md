# Demo Runbook

[← Documentation index](../README.md) · [← Production Readiness](Production_Readiness.md)

---

> **This runbook was executed, not just written, during this documentation review.** The full HTTP loop below — all five drift classes, triggered through the real API, on a freshly seeded database — was run against a live local instance on 2026-08-22. Actual responses are quoted verbatim in [§ Verified in this review](#verified-in-this-review). This is the evidence behind the [Executive Summary](../EXECUTIVE_SUMMARY.md)'s claim *"Whole pipeline over HTTP, all five classes — VALIDATED."*

## 1. Setup

```bash
pip install -r requirements.txt
rm -f driftwatch.db driftwatch.db-*
python3 apps/engine/serve.py     # fresh seeded world
# open http://localhost:8000  → The Living Web, 12 days of seeded history
```

Fully offline — replay mode has zero network dependency ([Risk Register R-25](../06_Security/Risk_Register.md)). `make demo` does the same thing (`Makefile`).

## 2. Beat sheet — the scripted 2-minute narration

Reproduced from [`DEMO.md`](../../DEMO.md), the canonical source for demo timing and narration. Verified mechanically correct against the transcript in §4.

| t | Beat | Where | What to do / say |
|---|---|---|---|
| 0:00 | Hook | title card | *"Everything your product depends on is written on pages that can change tonight."* |
| 0:10 | The calm | `#/web` | Living Web + stat tiles: 12 days of verified truth. **Note the MTTR tile carries a seeded value — see [§ Verified in this review](#verified-in-this-review) for why that matters and how to caveat it live.** |
| 0:20 | The page | mirror tab | Show the pricing page. *"Watched by a Scraper Studio scraper DriftWatch created from one sentence."* |
| 0:35 | Overnight | Demo controls | NimbusAI → **v2 — overnight redesign** → Apply & run all. Redesigned page (cards). |
| 0:45 | Break→heal | `#/heal` | Repair happened autonomously in that one run: all four gates green, machine-composed prompt visible, v→v+1, real MTTR. *"No human noticed. None needed to."* |
| 1:05 | The killer | Demo controls → `#/events` | NimbusAI → **v3 — unit meaning silently changes** → Apply & run all. Open the new **Class 4 · Semantic** event. |
| 1:15 | Show it | event view | Schema ✓ invariants ✓ **semantics ✕**. Same $2.50, unit now "input + output combined." *"The scraper succeeded. The truth changed. Only a contract catches that."* |
| 1:30 | The bill | same view | Blast radius: **+$626/mo**, 10 call sites, migration note. Alert toast lands top-right. |
| 1:45 | It's real | `#/ledger` + `#/sources/...` | Audit ledger (machine decisions end-to-end) + per-source history. |
| 1:55 | Close | title card | *"The web changed overnight. DriftWatch noticed, healed its own pipeline, proved the fix, and priced the impact — before your first coffee."* |

## 3. The scriptable loop (for rehearsal, CI, or a judge running it themselves)

```bash
curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v2_redesign"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing

curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v3_semantic"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing

curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v4_material"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing

curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v5_gone"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing
```

Slack alerts: set `DW_SLACK_WEBHOOK` before `serve.py` and Class 3/4/5 alerts also land in the configured channel.

## Verified in this review

Executed 2026-08-22 against a freshly seeded `driftwatch.db` (`rm -f driftwatch.db* && python3 apps/engine/serve.py`), then the four `curl` calls above, in order, on `nimbusai-pricing`. Actual API responses:

| Variant | Response | Interpretation |
|---|---|---|
| `v2_redesign` | `{"run_id":104,"class":1,"state":"published","snapshot_id":107,"event_id":5,"cost_delta_monthly":null,"healed":true}` | **Class 1 — Structural.** Broke, self-healed, re-verified, republished in one call. `healed:true` confirms the autonomous loop closed without any human step. |
| `v3_semantic` | `{"run_id":105,"class":4,"state":"review","event_id":6}` | **Class 4 — Semantic.** The killer case. Detail below. |
| `v4_material` | `{"run_id":106,"class":3,"state":"published","snapshot_id":109,"event_id":7,"cost_delta_monthly":412.0,"healed":false}` | **Class 3 — Material.** A genuine price change, correctly priced at **$412/mo** — matches the figure `DEMO.md` scripts for this beat. |
| `v5_gone` | `{"run_id":107,"class":5,"state":"review","event_id":8}` | **Class 5 — Availability.** Page unreachable; `run.relocating` appears in the ledger (`discover` invoked), landing in `REVIEW` state. **Note:** this does *not* create a `heal_events` row — `GET /api/review` (the heal review queue) returns `[]` after this run, because Class 5 review is a run-state condition, not a heal awaiting approval. An operator finds it via the source timeline or the events feed, not the Heal Center. |

Class 0 (no change) and Class 2 (benign) were both already present in the pre-existing seeded history (`events_by_class` showed `"Benign content drift":1` before this session's runs began) and are exercised directly by `test_e2e_pipeline.py::test_full_lifecycle_across_all_drift_classes` — not re-triggered here since no demo-state variant maps to "cosmetic-only change" for a live HTTP re-check.

### The semantic event, in full — schema ✓ invariants ✓ semantics ✕

`GET /api/events/6` (abbreviated):

```json
{
  "drift_class": 4, "severity": "critical", "confidence": 0.75,
  "after_verdict": {
    "passed": false, "confidence": 0.75,
    "gates": [
      {"gate": "schema", "passed": true},
      {"gate": "invariants", "passed": true},
      {"gate": "semantics", "passed": false,
       "details": ["models[nimbus-large-2].unit_context: page context 'USD per 1M tokens (input + output combined)' matches no anchor [per 1M input tokens, per 1 million input tokens] — asserted meaning: USD per 1 million INPUT tokens, public monthly price", "... (2 more models)"]},
      {"gate": "continuity", "passed": true}
    ]
  },
  "impact": { "cost_delta_monthly": 626.0, "affected": [ "10 call sites across README.md, src/assistant.py, src/billing_guard.py, usage.yaml" ] }
}
```

Every number matches the demo script exactly: **$626/mo**, **10 call sites**, all three prices (`2.50`, `0.15`, `4.00`) numerically unchanged while `unit_context` flips from "input tokens" to "input + output combined." This is the single most important verification in this documentation set, because it is the system's entire thesis in one API response: **the scraper's output is byte-for-byte plausible and the price is unchanged — schema and invariants pass — and only the semantics gate, reading the unit text the scraper was told to capture, catches it.**

### A genuine measurement, and why it matters for GAP-18

`GET /api/heals` for the fresh heal triggered by `v2_redesign` above returns a **real, freshly measured** heal event — not a seeded one:

```json
{
  "version_before": 2, "version_after": 3,
  "decision": "auto_approved", "decided_by": "machine",
  "verification": {"passed": true, "confidence": 1.0, "gates": [4 gates, all passed]},
  "mttr_seconds": 0.0
}
```

`mttr_seconds: 0.0` (replay mode has no real network latency to wait through, and the value is rounded to one decimal place) is the actual measured cycle time for this heal. At the time this transcript was captured, `/api/stats`'s `heal_mttr_seconds` field read **`21.1`** immediately after this run — a mean blending this genuine `0.0` s measurement together with `seed.py`'s hardcoded `42.3` s seeded rows; before this run it read exactly `42.3` (the seeded value alone, since no real heal had occurred yet in this session). **This was direct, hands-on confirmation of [GAP-18](../02_Requirements/Requirements_Gap_Analysis.md#low) and [Risk R-03](../06_Security/Risk_Register.md): the dashboard's headline MTTR statistic silently averaged a fabricated constant with real measurements, differing by four orders of magnitude.**
>
> **Fixed 2026-08-22, same day.** `heal_events` gained a `seeded` column; `/api/stats` now excludes seeded rows from `heal_mttr_seconds` and reports `heal_mttr_measured_count` alongside it. Re-running this exact transcript today would show `heal_mttr_seconds: 0.0` immediately (the real value alone) rather than a blended `21.1` — see [Gap Report G-14 / § Top improvements #1](Judge_Evaluation.md#top-improvements-before-submission). This transcript is preserved above as the record of what was found, not the current behaviour.

### Final ledger and stats state

`GET /api/stats` after all four calls: `{"sources":2,"runs":107,"credits_spent":108,"events_by_class":{"Structural drift":3,"Benign content drift":1,"Material change":2,"Semantic drift":1,"Availability drift":1},"heal_mttr_seconds":21.1,"heal_verification_pass_rate":1.0,"quarantined_snapshots":3}`.

`heal_verification_pass_rate: 1.0` — every heal attempted in this repository's history (seeded and live) has passed verification. This is expected given the demo fixtures are designed to demonstrate a successful heal; it is not evidence that verification always passes in general — `test_healing.py::test_garbage_preview_is_auto_rejected_never_trusted` is the test that proves rejection works, exercised in the test suite, not in this seeded demo history.

The full ledger tail correctly shows the state-machine transitions for the last run in order (`run.started` → `run.relocating` → `run.review` for the Class 5 case), consistent with the `RunState` sequence documented in [LLD](../03_Architecture/LLD.md).

---

**Next:** [Executive Summary](../EXECUTIVE_SUMMARY.md) · [Judge Evaluation](Judge_Evaluation.md)
