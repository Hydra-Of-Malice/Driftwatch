# Scraper Studio usage — the whole lifecycle, orchestrated

Driftwatch doesn't *use* Scraper Studio; it **completes** it. Every capability of the
Studio/CLI surface is load-bearing:

| Capability | Where Driftwatch drives it |
|---|---|
| `scraper create <url> "<description>"` (AI Flow, NL → schema + code → `collector_id`) | Source onboarding (`POST /api/onboard`, `seed.ensure_sources`) — one custom Studio scraper per source; the generated schema is hardened into a semantic contract |
| `scraper run <collector_id> [--version N]` | Every scheduled pipeline run; version pinning is the rollback mechanism |
| `scraper heal <collector_id> "<prompt ≤1000 chars>"` | `healing/composer.py` writes the prompt from the machine diagnosis; `healing/orchestrator.py` sends it |
| the `awaiting_approval` gate + `preview_result` + `diff_summary` | `healing/verifier.py` replays the preview against the full semantic contract — the heal's own "success" is never trusted |
| `scraper approve [--reject]` | Driven by the three-band confidence policy; the human Review Queue buttons call the *same* API |
| `discover --intent` | Class 5 (availability) relocation candidates when a page 404s |
| free-tier credit model (1 credit / page load) | surfaced in `/api/stats` and the Heal Center |

## Replay vs live

This reference build ships in **replay mode**: recorded envelope shapes (matching the official
CLI's JSON output) + a controlled mirror site, so the entire break → heal → verify → approve story
is reproducible offline, in tests, and on stage. The `BrightDataClient` protocol
(`driftwatch_engine/brightdata/protocol.py`) is the seam; `DW_MODE=live` swaps in the CLI-backed
client with zero changes above the seam.

## Live onboarding walkthrough

```bash
npm i -g @brightdata/cli
brightdata login                       # or: export BRIGHTDATA_API_KEY=...
export DW_MODE=live
python3 backend/serve.py
```

Onboard a real page (NL description → Studio AI Flow → collector):

```bash
curl -X POST localhost:8000/api/onboard -H 'Content-Type: application/json' -d '{
  "id": "openai-pricing",
  "name": "OpenAI — API Pricing",
  "url": "https://platform.openai.com/docs/pricing",
  "description": "For every model on this pricing page extract: model id, price per 1M input tokens,
    price per 1M output tokens, the visible unit text next to each price (as unit_context),
    rate limit if shown, and model status.",
  "vertical": "ai-provider",
  "schedule_minutes": 60
}'
```

The response carries the real `collector_id`, the AI-Flow `completed_steps`, and the Studio
`view_url` — paste that URL into the browser to see the generated scraper in the Bright Data
control panel. Then write the source's contract (`fixtures/contracts/openai-pricing.yaml`) —
start by copying `nimbusai-pricing.yaml` and editing fields/anchors.

### Live evidence to capture for the submission (during hackathon week)

- [ ] `scraper create` transcript + `collector_id` + control-panel screenshot (`view_url`)
- [ ] A real heal: the machine-composed prompt, the `awaiting_approval` envelope with
      `preview_result`, the verification verdict, and the `scraper approve` call — all of which
      Driftwatch records in `heal_events` and the audit ledger automatically
- [ ] `brightdata budget` before/after a soak day (credit spend)

## Notes for the Day-0 spike (before kickoff)

The LiveClient wraps the official CLI rather than raw REST — the CLI owns auth, AI-Flow polling and
the 3-concurrent-job backoff. Verify on a toy page that your installed CLI version's JSON envelopes
match `brightdata/envelopes.py` (they mirror the README of `@brightdata/cli` as of Aug 2026), and
adjust field names there if the CLI has moved — nothing above the seam changes.
