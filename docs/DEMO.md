# The 2-minute demo — script and reproduction guide

One continuous screen recording. The live break runs against the self-hosted mirror — say so on
screen ("simulated overnight redesign — same pipeline, real heal semantics"): honesty reads as
engineering rigor.

## Setup (once)

```bash
rm -f driftwatch.db && python3 backend/serve.py     # fresh seeded world
# open http://localhost:8000  → The Living Web, calm, with 12 days of history
```

Open **Demo controls** (bottom-left). Keep `/mirror/nimbusai-pricing` open in a second tab.

## Beat sheet (timings for the video)

| t | Beat | Where | What to do / say |
|---|---|---|---|
| 0:00 | Hook | title card | *"Everything your product depends on is written on pages that can change tonight."* |
| 0:10 | The calm | `#/web` | Living Web + stat tiles: 12 days of verified truth, 42s heal MTTR. |
| 0:20 | The page | mirror tab | Show the pricing page. *"Watched by a Scraper Studio scraper Driftwatch created from one sentence."* |
| 0:35 | Overnight | Demo controls | NimbusAI → **v2 — overnight redesign** → Apply & run all. Show the redesigned page (cards). |
| 0:45 | Break→heal | `#/heal` | The repair happened autonomously in that one run: gate sequence all green, heal history shows the machine-composed prompt, v→v+1, MTTR. *"No human noticed. None needed to."* |
| 1:05 | The killer | Demo controls → `#/events` | NimbusAI → **v3 — unit meaning silently changes** → Apply & run all. Open the new **Class 4 · Semantic** event. |
| 1:15 | Show it | event view | Schema ✓ invariants ✓ **semantics ✕**. Same $2.50 — unit now "input + output combined". *"The scraper succeeded. The truth changed. Only a contract catches that."* |
| 1:30 | The bill | same view | Blast radius: **+$626/mo**, 8 call sites, migration note. Alert toast lands top-right. |
| 1:45 | It's real | `#/ledger` + `#/sources/...` | Audit ledger (machine decisions end-to-end) + seismograph week view. In the live build: real catches from the soak week. |
| 1:55 | Close | title card | *"The web changed overnight. Driftwatch noticed, healed its own pipeline, proved the fix, and priced the impact — before your first coffee."* |

## The full loop, scriptable (for rehearsal or judges)

```bash
# overnight redesign → autonomous heal (returns healed:true, state:published)
curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v2_redesign"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing

# silent unit flip → Class 4, quarantined, priced, alerted
curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v3_semantic"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing

# real price change → Class 3 with $412/mo blast radius
curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v4_material"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing

# page removed → Class 5 with discover relocation candidates
curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v5_gone"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing
```

Slack alerts: set `DW_SLACK_WEBHOOK=https://hooks.slack.com/services/…` before `serve.py` and the
Class 3/4/5 alerts also land in your channel — a nice extra beat on the video.
