# Driftwatch

**The web your stack depends on has no changelog. Now it does.**

At 2:07 a.m., a provider quietly edits one line on a pricing page. No announcement, no email, no API
version bump. Every scraper watching it keeps returning green. Every one of them is now wrong.
Driftwatch exists for that moment.

Driftwatch turns the public pages your product silently depends on — model pricing, API docs, rate
limits, vendor terms — into **versioned, validated data contracts** that repair themselves when sites
change, and tells you what every real change means for your code and your bill:

> *"NimbusAI kept the price at $2.50 — but switched the unit from per-1M-input-tokens to
> input+output combined. Your scraper succeeded. Your bill grows **+$626/month**. Here are the
> 8 call sites."*

Built for the WeMakeDevs × Bright Data **Into the Scrape-Verse** hackathon (Aug 17–23, 2026), on top
of **Bright Data Scraper Studio** — create, run, heal, approve — orchestrated autonomously.

---

## The idea in 60 seconds

Every serious scraper breaks when pages change. Bright Data's Scraper Studio can *heal* a broken
scraper — but its loop has a human at both ends: someone must notice the breakage, write the heal
prompt, review the preview, and approve it. **Driftwatch is that human, formalized:**

```
detect (semantic contracts) → diagnose (failing fields + last-known-good examples)
  → compose the heal prompt → brightdata scraper heal → verify the preview AGAINST THE CONTRACT
  → three-band policy: auto-approve / human review / auto-reject+retry → re-run → audit ledger
```

And because extraction that *succeeds* can still be *wrong*, every snapshot passes a **Semantic
Contract** — shape (JSON Schema) + quality (invariants) + **meaning** (unit anchors) + plausibility
(continuity) — before anything downstream may see it. Quarantined data never reaches analytics or
alerts: **the dashboard cannot lie.**

## The five-class drift taxonomy

| Class | Name | What happened | What Driftwatch does |
|---|---|---|---|
| 1 | **Structural** | Page changed shape; meaning intact | Auto-heal → verify → approve. You see a green pulse. |
| 2 | **Benign** | Copyedits, cosmetics | Ledger only. Never alerts. |
| 3 | **Material** | A watched fact actually changed | Alert + blast radius + cost delta + migration note. |
| 4 | **Semantic** | Extraction green, meaning shifted (unit/scope flip) | Quarantine + alert. Selectors can't see this; contracts can. |
| 5 | **Availability** | Page moved/removed/blocked | `discover`-powered relocation candidates for approval. |

Most monitoring detects Class 1. Driftwatch is a product about Classes 3, 4 and 5 — with Class 1
handled so well you never see it.

## Quickstart (offline, zero external dependencies)

Requires Python 3.11+ with `flask`, `pydantic>=2`, `jsonschema`, `pyyaml`, `httpx`
(`pip install -r requirements.txt` if needed). No database server, no queue, no build step.

```bash
python3 apps/engine/serve.py
# → http://localhost:8000  (UI, API, and the demo mirror site on one origin)
```

The engine boots in **replay mode**: a recorded Bright Data client plus a controlled mirror site
(`/mirror/*`) simulating a real provider's pricing page and a payments API reference — including an
overnight redesign, a silent unit flip, a real price change, and a 404. Open **Demo controls**
(bottom-left) to change what the mirrored web looks like, then watch the pipeline detect, heal,
verify, approve, and price the change.

Run the test suite (the E2E test walks all five drift classes through the full state machine):

```bash
make test     # or: cd apps/engine && python3 -m unittest discover -s tests
```

## Going live against real Bright Data

```bash
npm i -g @brightdata/cli && brightdata login       # Scraper Studio CLI
export BRIGHTDATA_API_KEY=...                      # from brightdata.com/cp/setting/users
export DW_MODE=live
python3 apps/engine/serve.py
```

Same engine, same states, same UI — the client seam (`driftwatch_engine/brightdata/`) swaps the
recorded envelopes for the real CLI (`scraper create / run / heal / approve`, `discover`). See
[docs/SCRAPER_STUDIO.md](docs/SCRAPER_STUDIO.md) for the full lifecycle evidence and live onboarding.

## Architecture (two deployables, one database, zero microservices)

```
apps/web       zero-build SPA (vanilla ES modules + SVG) — the Living Web, seismographs,
               drift events, Heal Center, audit ledger
apps/engine    one Flask service: REST API + scheduler + the pipeline state machine
  driftwatch_engine/
    contracts/   the Semantic Contract Engine (4 gates → confidence verdict)
    drift/       entity-resolved differ + five-class classifier
    healing/     diagnose → compose(≤1000 chars) → verify preview → three-band approve
    impact/      blast radius (repo scan) + cost-delta estimation
    brightdata/  the client seam: replay (fixtures) ⇄ live (official CLI)
    pipeline/    the run state machine (every transition audited)
    llm/         deterministic heuristics by default; Claude upgrade behind one env var
fixtures/      contracts (YAML), snapshot variants, sample repo for impact scans
mirror/        the controlled demo site (v1 baseline → v2 redesign → v3 semantic → v4 material)
```

Full state machine and design decisions: [ARCHITECTURE.md](ARCHITECTURE.md).

## Reliability guarantees

- A healed scraper's output is **never trusted — it is re-proven** against the full contract before
  `scraper approve` is called; failed verification rejects the fix and stays on the pinned version.
- Quarantined snapshots are never served downstream.
- Every run, verdict, heal prompt, preview, approval (machine *and* human) and alert is an
  append-only audit event.
- Zero-noise alerting: Classes 0–2 never page anyone.

## Hackathon submission notes

- **Scraper Studio usage:** [docs/SCRAPER_STUDIO.md](docs/SCRAPER_STUDIO.md)
- **2-minute demo script:** [docs/DEMO.md](docs/DEMO.md)
- **Example structured output:** [fixtures/snapshots/](fixtures/snapshots/) (contract-stamped
  extractions for every page variant)
- Public web data only; the demo runs against a self-hosted mirror so the break-and-heal moment is
  reproducible on stage — clearly labeled, same pipeline, real heal semantics.
