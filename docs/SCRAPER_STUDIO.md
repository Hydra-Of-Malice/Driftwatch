# Scraper Studio usage — the whole lifecycle, orchestrated

Driftwatch doesn't *use* Scraper Studio; it **completes** it. Every capability of the
Studio/CLI surface is load-bearing:

Live status below is as validated on 2026-08-23 against `@brightdata/cli@0.3.5`; the raw
envelopes and reproduction commands are in [LIVE_VALIDATION.md](LIVE_VALIDATION.md).

| Capability | Where Driftwatch drives it | Live status |
|---|---|---|
| `scraper create <url> "<description>"` (AI Flow, NL → schema + code → `collector_id`) | Source onboarding (`POST /api/onboard`, `seed.ensure_sources`) — one custom Studio scraper per source; the generated schema is hardened into a semantic contract | **Partial** — `POST /dca/collector` returns a real `c_*` id; the `automate_template` AI trigger is refused **403 `Automation not allowed`** |
| `scraper run <collector_id> [--version N]` | Every scheduled pipeline run; version pinning is the rollback mechanism | Blocked downstream of create (`Collector does not have a template`) |
| `scraper heal <collector_id> "<prompt ≤1000 chars>"` | `healing/composer.py` writes the prompt from the machine diagnosis; `healing/orchestrator.py` sends it | **Vendor-disabled** — `refactor_template` returns **503 `Self healing tool is temporarily disabled`** |
| the `awaiting_approval` gate + `preview_result` + `diff_summary` | `healing/verifier.py` replays the preview against the full semantic contract — the heal's own "success" is never trusted | Unreachable while heal is 503 |
| `scraper approve [--reject]` | Driven by the three-band confidence policy; the human Review Queue buttons call the *same* API | Unreachable while heal is 503 |
| `discover --intent` | Class 5 (availability) relocation candidates when a page 404s | **LIVE — verified working** (real AI ranking, ~17s) |
| free-tier credit model (1 credit / page load) | surfaced in `/api/stats` and the Heal Center | Zone reads live; `/customer/balance` is 403 for a `User`-scoped token |

## Replay vs live

The mode is exposed at `GET /api/meta` and rendered as a badge in the UI, so a viewer can never
mistake replay for live. This reference build ships in **replay mode**: recorded envelope shapes (matching the official
CLI's JSON output) + a controlled mirror site, so the entire break → heal → verify → approve story
is reproducible offline, in tests, and on stage. The `BrightDataClient` protocol
(`driftwatch_engine/brightdata/protocol.py`) is the seam; `DW_MODE=live` swaps in the CLI-backed
client with zero changes above the seam.

## Live onboarding walkthrough

```bash
npm i -g @brightdata/cli               # installs both `brightdata` and `bdata`
export BRIGHTDATA_API_KEY=...          # needs Admin permissions, not User (see LIVE_VALIDATION.md)
export DW_MODE=live
python backend/serve.py                # Python 3.11+
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

### Live evidence captured (2026-08-23)

- [x] `scraper create` transcript + real `collector_id`s: `c_mt3vr49h1qtwyctl1g`,
      `c_mt5moeyi28i2av0bzd`, `c_mt5og4ec1cp5lb1yjd` — all real, all visible at
      `https://brightdata.com/cp/scrapers/<id>`. The AI-Flow step behind them is refused
      with HTTP 403 `Automation not allowed`, so their templates remain stubs.
- [x] `discover --intent` run live end-to-end through `LiveClient`, returning real
      AI-ranked candidates normalized into the pipeline's `{url, title, score, reason}` shape.
- [x] Web Unlocker retrieval of a real public page through the account's `cli_unlocker` zone.
- [ ] A real heal round trip — **not capturable**: `refactor_template` is returning HTTP 503
      `Self healing tool is temporarily disabled`, a server-side global feature disable.
      Driftwatch surfaces that 503 as `VENDOR_UNAVAILABLE`; it does **not** substitute a
      replay result for it. See [LIVE_VALIDATION.md](LIVE_VALIDATION.md) § Two distinct blockers.

## CLI identity: `brightdata` and `bdata`

`@brightdata/cli` installs **both** names from one entrypoint (`bin: {brightdata: dist/index.js,
bdata: dist/index.js}`). `bdata` is an alias, not a second toolchain — captured envelopes whose
`next_step` reads `bdata scraper run ...` are the CLI suggesting its own short form.
`LiveClient` resolves either name via `shutil.which` and invokes the **absolute** resolved path,
which is required on Windows where the npm shim is `brightdata.CMD`.

## Envelope drift found and handled

`discover` returns `{link, title, description, relevance_score}`; everything above the seam
speaks `{url, title, score, reason}`. `live._normalize_candidate` translates at the boundary so
two vocabularies never leak upward. Create/heal/approve envelopes additionally carry
`completed_steps` and the failure statuses `ai_trigger_failed` / `heal_trigger_failed` /
`resume_failed`, which the models in `brightdata/envelopes.py` now represent explicitly — a
vendor refusal arrives *inside* a well-formed envelope, so it must be representable without
being mistaken for a result.
