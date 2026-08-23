# DriftWatch

**The web your stack depends on has no changelog. Now it does.**

At 2:07 a.m., a provider quietly edits one line on a pricing page. No announcement, no email, no API
version bump. Every scraper watching it keeps returning green. Every one of them is now wrong.
DriftWatch exists for that moment.

DriftWatch turns the public pages your product silently depends on — model pricing, API docs, rate
limits, vendor terms — into **versioned, validated data contracts** that repair themselves when
sites change, and tells you what every real change means for your code and your bill:

> *"NimbusAI kept the price at $2.50 — but switched the unit from per-1M-input-tokens to
> input+output combined. Your scraper succeeded. Your bill grows **+$626/month**. Here are the
> 9 call sites."*

Built for the WeMakeDevs × Bright Data **Into the Scrape-Verse** hackathon, on top of **Bright Data
Scraper Studio** — create, run, heal, verify, approve — orchestrated autonomously.

> **Honesty note, up front.** Bright Data currently refuses two Scraper Studio operations on this
> account: the AI Flow that generates a scraper (`403 Automation not allowed`) and self-healing
> (`503 Self healing tool is temporarily disabled`). Those are real, reproducible vendor responses,
> documented with raw envelopes in **[docs/LIVE_VALIDATION.md](docs/LIVE_VALIDATION.md)**.
> DriftWatch does **not** simulate around them: in live mode it surfaces the actual failure,
> classified, and never falls back to replay. What *is* live-proven, and what is blocked, is spelled
> out in [Live status](#live-status) below.

---

## The problem

Scrapers don't fail loudly. A selector changes, extraction returns `null`, the HTTP status is still
`200`, and the dashboard stays green while the data behind it rots. Worse, extraction that
*succeeds* can still be *wrong*: the number is right and its meaning changed underneath you.

## The solution

```
detect (semantic contracts) → diagnose (failing fields + last-known-good examples)
  → compose the heal prompt → brightdata scraper heal → verify the preview AGAINST THE CONTRACT
  → three-band policy: auto-approve / human review / auto-reject+retry → re-run → audit ledger
```

Bright Data's Scraper Studio can *heal* a broken scraper, but its loop has a human at both ends:
someone must notice the breakage, write the heal prompt, review the preview, and approve.
**DriftWatch is that human, formalized.**

Every snapshot passes a **Semantic Contract** — shape (JSON Schema) + quality (invariants) +
**meaning** (unit anchors) + plausibility (continuity) — before anything downstream may see it.
Quarantined data never reaches analytics or alerts: **the dashboard cannot lie.**

## The five-class drift taxonomy

| Class | Name | What happened | What DriftWatch does |
|---|---|---|---|
| 1 | **Structural** | Page changed shape; meaning intact | Auto-heal → verify → approve. You see a green pulse. |
| 2 | **Benign** | Copyedits, cosmetics | Ledger only. Never alerts. |
| 3 | **Material** | A watched fact actually changed | Alert + blast radius + cost delta + migration note. |
| 4 | **Semantic** | Extraction green, meaning shifted (unit/scope flip) | Quarantine + alert. Selectors can't see this; contracts can. |
| 5 | **Availability** | Page moved/removed/blocked | `discover`-powered relocation candidates for approval. |

Most monitoring detects Class 1. DriftWatch is a product about Classes 3, 4 and 5 — with Class 1
handled so well you never see it.

---

## Architecture

```
frontend/      zero-build SPA (vanilla ES modules + SVG) — Living Web, seismographs,
               drift events, Heal Center, audit ledger, replay/live mode badge
backend/       one Flask service: REST API + scheduler + the pipeline state machine
  driftwatch_engine/
    contracts/   the Semantic Contract Engine (4 gates → confidence verdict)
    drift/       entity-resolved differ + five-class classifier
    healing/     diagnose → compose(≤1000 chars) → verify preview → three-band approve
    impact/      blast radius (repo scan) + cost-delta estimation
    brightdata/  the client seam: replay (fixtures) ⇄ live (official CLI)
    pipeline/    the run state machine (every transition audited)
    errors.py    vendor/application failure taxonomy (see Failure classification)
    obs.py       structured operation logging with credential scrubbing
fixtures/      contracts (YAML), snapshot variants, sample repo for impact scans
mirror/        the controlled demo site (v1 baseline → v2 redesign → v3 semantic → v4 material)
scripts/       live smoke test, day-0 spike, deterministic heal demo
```

The pipeline state machine and design decisions: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Bright Data integration

Everything above `brightdata/protocol.py` is identical in replay and live mode. `DW_MODE` picks the
implementation exactly once, in `api/app.py :: build_deps` — **there is no silent live→replay
fallback anywhere in the codebase.**

| Scraper Studio capability | Where DriftWatch drives it |
|---|---|
| `scraper create <url> "<description>"` | Source onboarding (`POST /api/onboard`) |
| `scraper run <collector_id> [--version N]` | Every scheduled run; version pinning is the rollback |
| `scraper heal <collector_id> "<prompt>"` | `healing/composer.py` writes it from the machine diagnosis |
| the `awaiting_approval` gate + `preview_result` | `healing/verifier.py` re-proves it against the contract |
| `scraper approve [--reject]` | The three-band policy; the human Review Queue calls the same API |
| `discover --intent` | Class 5 relocation candidates when a page 404s |

Full lifecycle detail: **[docs/SCRAPER_STUDIO.md](docs/SCRAPER_STUDIO.md)**.

## Live status

Validated 2026-08-23 against `@brightdata/cli@0.3.5`. Raw envelopes, HTTP statuses and reproduction
commands: **[docs/LIVE_VALIDATION.md](docs/LIVE_VALIDATION.md)**.

| Operation | Status |
|---|---|
| Authentication, `zones` | **Live — works** |
| Web Unlocker page retrieval | **Live — works** |
| `POST /dca/collector` → real `c_*` collector ID | **Live — works** |
| `discover --intent` (AI ranking) | **Live — works**, driven through `LiveClient` |
| Scraper Studio AI Flow (`automate_template`) | **Blocked — HTTP 403 `Automation not allowed`** |
| Self-healing (`refactor_template`) | **Blocked — HTTP 503 `Self healing tool is temporarily disabled`** |

Real collector IDs created by this project: `c_mt3vr49h1qtwyctl1g`, `c_mt5moeyi28i2av0bzd`,
`c_mt5og4ec1cp5lb1yjd`, `c_mt5p4epqlomcj1iim`, `c_mt5p5irb2aw2fyjfgu` — each viewable at
`https://brightdata.com/cp/scrapers/<id>`.

**Why the two blocks are different, and why it matters.** A controlled experiment settled it: the
account holder issued a second API key with `Permissions = Admin` and the identical requests were
replayed with each key. `/customer/balance` went `403 → 200`, proving the token-scope mechanism is
real — but `automate_template` returned `403` with **both** keys, on a fresh collector and on two
pre-existing ones. So the AI-Flow refusal is an **account-level feature entitlement**, not token
scope, and no token change lifts it. The `503` on self-healing is a server-side global feature
disable. Bright Data's own error text for the first 403 points at token permissions, which makes all
three look like one problem; only holding the request constant while varying the token separates
them. That is precisely why DriftWatch classifies failures itself instead of trusting vendor
remediation text.

---

## Quickstart (offline, zero external dependencies)

Requires Python 3.10+ with `flask`, `pydantic>=2`, `jsonschema`, `pyyaml`, `httpx`
(`pip install -r requirements.txt`). No database server, no queue, no build step.

```bash
python backend/serve.py
# → http://localhost:8000  (UI, API, and the demo mirror site on one origin)
```

The engine boots in **replay mode** — a recorded Bright Data client plus a controlled mirror site
(`/mirror/*`) simulating a provider's pricing page and a payments API reference, including an
overnight redesign, a silent unit flip, a real price change, and a 404. The UI shows a **REPLAY**
badge sourced from `GET /api/meta`, so replay can never be mistaken for live. Open **Demo controls**
(bottom-left) to change what the mirrored web looks like, then watch the pipeline detect, heal,
verify, approve and price the change.

## Going live

```bash
npm i -g @brightdata/cli          # installs both `brightdata` and `bdata` (aliases, same binary)
export BRIGHTDATA_API_KEY=...     # https://brightdata.com/cp/setting/users
export DW_MODE=live
python backend/serve.py
```

Live mode **fails loudly** if `BRIGHTDATA_API_KEY` is missing or the CLI is not on `PATH` — it will
not start and silently serve replay data. Verify the whole live path with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_smoke_test.ps1
```

It stages CLI → auth → Web Unlocker → `discover` → `scraper create` → run/heal/approve, prints a
PASS/FAIL/BLOCKED table, and uses distinct exit codes: **0** all-pass, **1** our fault (missing CLI,
bad auth, broken handling), **2** a documented vendor refusal. CI can tell those apart.

## Creating a real collector

```bash
curl -X POST localhost:8000/api/onboard -H 'Content-Type: application/json' -d '{
  "id": "example-pricing",
  "name": "Example — API Pricing",
  "url": "https://example.com/pricing",
  "description": "For every model extract: model id, price per 1M input tokens, price per 1M output tokens, the visible unit text next to each price (as unit_context), and model status.",
  "schedule_minutes": 60
}'
```

The response carries the real `collector_id`, the AI-Flow `completed_steps` and the Studio
`view_url`. A source also needs a hand-authored semantic contract at
`fixtures/contracts/<id>.yaml` — copy `nimbusai-pricing.yaml` as a starting point.

## Demonstrating drift and healing

Deterministic, terminal-driven, repeatable:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\heal_demo.ps1
```

It verifies a clean extraction, injects a controlled break, shows verification failing and *which
gates* failed, shows the machine-composed heal prompt, verifies the preview, applies the approval
policy, re-runs, confirms the data is restored, and restores the baseline world on exit. Only the
*failure injection* is controlled — the heal semantics are the real production code paths.

Presenter script with timings: **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)**.

## Verification — the four gates

A healed scraper's output is never trusted; it is **re-proven**. `contracts/engine.py :: evaluate`
runs all four gates and composes a weighted confidence, and `healing/verifier.py` runs *the same
function* on a heal preview — one definition of correctness everywhere.

| Gate | Weight | What it proves |
|---|---|---|
| **schema** | 0.35 | JSON Schema (Draft 2020-12) — the shape is right |
| **invariants** | 0.25 | `non_null` / `range` / `enum` / `cardinality_drop` — the values are usable |
| **semantics** | 0.25 | unit/scope anchors near each value still hold — **the Class-4 tripwire** |
| **continuity** | 0.15 | plausibility vs last-known-good — no silent implausible jumps |

The verdict, not the heal's own success status, decides approval:

| Confidence | Decision |
|---|---|
| `≥ 0.90` and all gates pass | auto-approve, bump version, re-run |
| `≤ 0.50` | auto-reject, retry once with a refined prompt |
| in between | human Review Queue (same Bright Data approval API) |

The active template version only advances **after** a verified re-run. A rejected heal leaves the
previous version active and the interval quarantined.

## Failure classification

A vendor refusal is never reported as a broken scraper. `errors.py` maps every failure to a stable
category — `VENDOR_AUTH_ERROR`, `VENDOR_PERMISSION_ERROR`, `VENDOR_UNAVAILABLE`,
`VENDOR_RATE_LIMIT`, `VENDOR_TIMEOUT`, `VENDOR_BAD_RESPONSE`, `CLI_COMPATIBILITY`,
`SCRAPER_FAILURE`, `SCHEMA_DRIFT`, `SEMANTIC_DRIFT`, `VERIFICATION_FAILURE`, `APPLICATION_ERROR` —
carried through the API as HTTP 502 with `{category, operation, status, hint}` and surfaced in the
UI. `SCRAPER_FAILURE` is reserved for a scraper that genuinely ran and failed.

## Reliability guarantees

- The live client **never manufactures success**: an empty run, a `*_failed` envelope status, or a
  vendor error raises a classified failure. An HTTP 200 is not an outcome.
- The vendor's own wording survives — the CLI's JSON error envelope is parsed *before* the exit
  code, so the diagnostic is never discarded for a generic "CLI failed".
- Quarantined snapshots are never served downstream.
- Every run, verdict, heal prompt, preview, approval (machine *and* human) and alert is an
  append-only audit event.
- Zero-noise alerting: Classes 0–2 never page anyone.

## Security

- `.env` is gitignored and has never been committed (verified against full history).
- No credential reaches a log, an exception, an API response, or the frontend bundle. The live
  client redacts credential-shaped strings from vendor stderr/stdout before they can be raised, and
  `obs.py` scrubs by key name as a second layer. A test pins that the key never appears in a raised
  error.
- `subprocess` runs with `shell=False`, list-form argv, and an absolute resolved binary — no
  command-injection surface. URLs are validated to public `http(s)` and rejected if they begin with
  `-` (argv-flag injection).
- `source_id` is constrained to `[a-z0-9][a-z0-9_-]{0,63}` because it becomes a filesystem path.
- `DW_API_TOKEN` gates every `/api/*` route with a constant-time comparison when set. The public
  demo opts into a documented split (`DW_PUBLIC_DEMO`): reads and demo-driving writes are open so
  anonymous judges can use it, while `/api/onboard` — the only route that reaches Bright Data and
  spends credits — stays gated in every configuration. The relaxation is opt-in; the default gates
  everything, and both configurations are pinned by tests.
- Full posture, including accepted residual risks: **[docs/06_Security/](docs/06_Security/)**.

## Testing

```bash
cd backend && python -m unittest discover -s tests      # 50 tests
```

```bash
python -m ruff check backend                            # lint
```

CI runs the suite on a matrix of `ubuntu-latest` × `windows-latest` and Python `3.10` × `3.12`. The
Windows job exists for a reason: every Windows-specific bug this project shipped (a hardcoded POSIX
`PATH` that wiped the child environment, a bare `brightdata` invocation that cannot launch the npm
`.cmd` shim, and a cp1252 decode that silently discarded all CLI stdout) survived precisely because
CI was Linux-only.

## Deployment

`render.yaml` deploys the public demo in **replay mode**, deliberately and visibly. Secrets are
never in the file — `BRIGHTDATA_API_KEY` and `ANTHROPIC_API_KEY` are `sync: false` (dashboard-only)
and `DW_API_TOKEN` is Render-generated. The health check is `/`. To run a deployment against real Bright Data, set `DW_MODE=live` and
`BRIGHTDATA_API_KEY` in the Render dashboard; note the free Python runtime does not ship the Bright
Data CLI, which live mode requires.

## Limitations

These are real and reproducible, not hedges:

1. **Scraper Studio AI Flow is refused for this account** (`403 Automation not allowed`). Collectors
   are created for real, but their templates stay stubs, so a live `scraper run` cannot be
   demonstrated end-to-end. Not fixable by token scope — see [Live status](#live-status).
2. **Self-healing is disabled server-side by Bright Data** (`503`). The live heal round trip is
   therefore not demonstrable at all right now. DriftWatch surfaces the 503 as `VENDOR_UNAVAILABLE`
   rather than substituting a replay result.
3. Because of (1) and (2), the break→heal→verify→approve→recover story is demonstrated against the
   deterministic replay world and the bundled mirror site, clearly labeled **REPLAY** in the UI. The
   heal *semantics* — prompt composition, four-gate verification, three-band approval, version
   pinning, audit ledger — are the real production code paths; only the vendor transport is replayed.
4. Semantic contracts are hand-authored per source. Onboarding a source without one fails with 422
   by design rather than guessing at correctness.
5. Bright Data authentication was observed to flap (a transient `401` for ~10 minutes with an
   unchanged key). The smoke test classifies `401` as our-fault/exit-1 so CI does not shrug it off.

## Hackathon submission notes

- **Live validation log:** [docs/LIVE_VALIDATION.md](docs/LIVE_VALIDATION.md)
- **Scraper Studio usage:** [docs/SCRAPER_STUDIO.md](docs/SCRAPER_STUDIO.md)
- **Demo script:** [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- **AI coding assistant usage:** [docs/AI_USAGE.md](docs/AI_USAGE.md)
- **Example structured output:** [fixtures/snapshots/](fixtures/snapshots/)
- Public web data only. The demo runs against a self-hosted mirror so the break-and-heal moment is
  reproducible on stage — clearly labeled, same pipeline, real heal semantics.
