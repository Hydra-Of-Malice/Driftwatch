# DriftWatch — Technical reference

This page keeps the operational and integration detail that used to live in the top-level README.
For the pipeline state machine and design decisions, see the root [ARCHITECTURE.md](../ARCHITECTURE.md).
For the full engineering documentation set, see the [documentation index](README.md).

## The five-class drift taxonomy

| Class | Name | What happened | What DriftWatch does |
|---|---|---|---|
| 1 | **Structural** | Page changed shape; meaning intact | Auto-heal → verify → approve. Alerts only if the heal needs review or fails. |
| 2 | **Benign** | Copyedits, cosmetics | Ledger only. Never alerts. |
| 3 | **Material** | A watched fact actually changed | Alert + blast radius + cost delta + migration note. |
| 4 | **Semantic** | Extraction green, meaning shifted (unit/scope flip) | Quarantine + alert. Selectors can't see this; contracts can. |
| 5 | **Availability** | Page moved/removed/blocked | `discover`-powered relocation candidates for approval. |

## Bright Data integration

Everything above `brightdata/protocol.py` is identical in replay and live mode. `DW_MODE` picks the
implementation exactly once, in `api/app.py :: build_deps`. There is no silent live→replay
fallback anywhere in the codebase.

| Scraper Studio capability | Where DriftWatch drives it |
|---|---|
| `scraper create <url> "<description>"` | Source onboarding (`POST /api/onboard`) |
| `scraper run <collector_id> [--version N]` | Every scheduled run; version pinning is the rollback |
| `scraper heal <collector_id> "<prompt>"` | `healing/composer.py` writes it from the machine diagnosis |
| the `awaiting_approval` gate + `preview_result` | `healing/verifier.py` re-proves it against the contract |
| `scraper approve [--reject]` | The three-band policy; the human Review Queue calls the same API |
| `discover --intent` | Class 5 relocation candidates when a page 404s |

Full lifecycle detail: [SCRAPER_STUDIO.md](SCRAPER_STUDIO.md).

## Live status

Validated 2026-08-23 against `@brightdata/cli@0.3.5`. Raw envelopes, HTTP statuses and reproduction
commands: [LIVE_VALIDATION.md](LIVE_VALIDATION.md).

| Operation | Status |
|---|---|
| Authentication, `zones` | **Live — works** |
| Web Unlocker page retrieval | **Live — works** |
| `POST /dca/collector` → real `c_*` collector ID | **Live — works** |
| `discover --intent` (AI ranking) | **Live — works**, driven through `LiveClient` |
| Scraper Studio AI Flow (`automate_template`) | **Blocked — HTTP 403 `Automation not allowed`** |
| Self-healing (`refactor_template`) | **Blocked — HTTP 503 `Self healing tool is temporarily disabled`** |

Real collector IDs created by this project: `c_mt3vr49h1qtwyctl1g`, `c_mt5moeyi28i2av0bzd`,
`c_mt5og4ec1cp5lb1yjd`, `c_mt5p4epqlomcj1iim`, `c_mt5p5irb2aw2fyjfgu`.

**Why the two blocks are different.** A second API key with `Permissions = Admin` was issued and
the identical requests were replayed with each key. `/customer/balance` went `403 → 200`, proving
the token-scope mechanism is real, but `automate_template` returned `403` with both keys, on a
fresh collector and on two pre-existing ones. So the AI Flow refusal is an account-level feature
entitlement, not token scope, and no token change lifts it. The `503` on self-healing is a
server-side global feature disable. Bright Data's own error text for the first 403 points at token
permissions, which makes all three look like one problem; only holding the request constant while
varying the token separates them. That is why DriftWatch classifies failures itself instead of
trusting vendor remediation text.

## Going live

```bash
npm i -g @brightdata/cli          # installs both `brightdata` and `bdata` (aliases, same binary)
export BRIGHTDATA_API_KEY=...     # https://brightdata.com/cp/setting/users
export DW_MODE=live
python backend/serve.py
```

Live mode fails loudly if `BRIGHTDATA_API_KEY` is missing or the CLI is not on `PATH`. It will not
start and silently serve replay data. Verify the whole live path with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_smoke_test.ps1
```

It stages CLI → auth → Web Unlocker → `discover` → `scraper create` → run/heal/approve, prints a
PASS/FAIL/BLOCKED table, and uses distinct exit codes: **0** all-pass, **1** our fault (missing CLI,
bad auth, broken handling), **2** a documented vendor refusal.

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

The response carries the real `collector_id`, the AI Flow `completed_steps` and the Studio
`view_url`. A source also needs a hand-authored semantic contract at
`fixtures/contracts/<id>.yaml`. Copy `nimbusai-pricing.yaml` as a starting point. If
`DW_API_TOKEN` is set, add `-H "Authorization: Bearer <token>"`.

## Demonstrating drift and healing from the terminal

```powershell
powershell -ExecutionPolicy Bypass -File scripts\heal_demo.ps1
```

It verifies a clean extraction, injects a controlled break, shows verification failing and which
gates failed, shows the machine-composed heal prompt, verifies the preview, applies the approval
policy, re-runs, confirms the data is restored, and restores the baseline world on exit. Only the
failure injection is controlled; the heal semantics are the real production code paths.

Presenter script with timings: [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Verification — the four gates

A healed scraper's output is never trusted; it is re-proven. `contracts/engine.py :: evaluate`
runs all four gates and composes a weighted confidence, and `healing/verifier.py` runs the same
function on a heal preview.

| Gate | Weight | What it proves |
|---|---|---|
| **schema** | 0.35 | JSON Schema (Draft 2020-12): the shape is right |
| **invariants** | 0.25 | `non_null` / `range` / `enum` / `cardinality_drop`: the values are usable |
| **semantics** | 0.25 | unit/scope anchors near each value still hold: the Class 4 tripwire |
| **continuity** | 0.15 | plausibility vs last-known-good: no silent implausible jumps |

| Confidence | Decision |
|---|---|
| `≥ 0.90` and all gates pass | auto-approve, bump version, re-run |
| `≤ 0.50` | auto-reject, retry once with a refined prompt |
| in between | human Review Queue (same Bright Data approval API) |

The active template version only advances after a verified re-run. A rejected heal leaves the
previous version active and the interval quarantined.

## Failure classification

A vendor refusal is never reported as a broken scraper. `errors.py` maps every failure to a stable
category: `VENDOR_AUTH_ERROR`, `VENDOR_PERMISSION_ERROR`, `VENDOR_UNAVAILABLE`,
`VENDOR_RATE_LIMIT`, `VENDOR_TIMEOUT`, `VENDOR_BAD_RESPONSE`, `CLI_COMPATIBILITY`,
`SCRAPER_FAILURE`, `SCHEMA_DRIFT`, `SEMANTIC_DRIFT`, `VERIFICATION_FAILURE`, `APPLICATION_ERROR`.
Vendor failures are returned by the API as HTTP 502 with `{category, operation, status, hint}` and
surfaced in the UI. `SCRAPER_FAILURE` is reserved for a scraper that genuinely ran and failed.

## Reliability guarantees

- The live client never manufactures success: an empty run, a `*_failed` envelope status, or a
  vendor error raises a classified failure.
- The CLI's JSON error envelope is parsed before the exit code, so the vendor's diagnostic is kept.
- Quarantined snapshots are never served downstream.
- Every run, verdict, heal prompt, preview, approval (machine and human) and alert is an
  append-only audit event.

## Security

- `.env` is gitignored.
- The live client redacts credential-shaped strings from vendor stderr/stdout before they can be
  raised, and `obs.py` scrubs by key name as a second layer. A test pins that the key never appears
  in a raised error.
- `subprocess` runs with `shell=False`, list-form argv, and an absolute resolved binary. URLs are
  validated to public `http(s)` and rejected if they begin with `-`.
- `source_id` is constrained to `[a-z0-9][a-z0-9_-]{0,63}` because it becomes a filesystem path.
- `DW_API_TOKEN` gates every `/api/*` route with a constant-time comparison when set. The public
  demo opts into a documented split (`DW_PUBLIC_DEMO`): reads and demo-driving writes are open,
  while `/api/onboard`, the only route that reaches Bright Data and spends credits, stays gated in
  every configuration. Both configurations are pinned by tests.
- Full posture, including accepted residual risks: [06_Security/](06_Security/).

## Testing and CI

```bash
cd backend && python -m unittest discover -s tests      # 50 tests
python -m ruff check backend                            # lint
```

CI runs the suite on `ubuntu-latest` and `windows-latest` with Python `3.10` and `3.12`. The
Windows job exists because every Windows-specific bug this project shipped (a hardcoded POSIX
`PATH` that wiped the child environment, a bare `brightdata` invocation that cannot launch the npm
`.cmd` shim, and a cp1252 decode that discarded CLI stdout) survived while CI was Linux-only.

## Deployment

`render.yaml` deploys the demo in replay mode. Secrets are never in the file: `BRIGHTDATA_API_KEY`,
`ANTHROPIC_API_KEY` and `DW_SLACK_WEBHOOK` are `sync: false` (dashboard-only) and `DW_API_TOKEN` is
generated by Render. The service runs `gunicorn` with one worker, because the scheduler is an
in-process thread and SQLite is single-writer. To run against real Bright Data, set `DW_MODE=live`
and `BRIGHTDATA_API_KEY` in the Render dashboard; the free Python runtime does not ship the Bright
Data CLI, which live mode requires.
