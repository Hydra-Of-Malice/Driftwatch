# API Documentation

[← Documentation index](../README.md)

---

**Base URL:** `http://localhost:8000` · **Content type:** `application/json`
**Source:** `apps/engine/driftwatch_engine/api/app.py` · **Routes:** 19

> ## ⚠ Authentication: OPT-IN, OFF BY DEFAULT (as of 2026-08-22)
> **No endpoint requires authentication or authorisation unless `DW_API_TOKEN` is set.** In the default configuration this still includes endpoints that mutate production state (`POST /api/review/<id>` approves an AI-generated template; `POST /api/onboard` spends vendor credits; `POST /api/run-all` triggers every source). The server binds `127.0.0.1` by default (was `0.0.0.0`).
> **If `DW_API_TOKEN` is set**, every route below except `GET /`, `/assets/*`, and `/mirror/*` requires `Authorization: Bearer <token>`, or returns `401 {"error": "unauthorized"}`. There is still **no authorisation/RBAC layer** (an authenticated caller can do anything any other authenticated caller can), **no rate limiting, no CSRF protection, and no security headers.**
> See [GAP-01](../02_Requirements/Requirements_Gap_Analysis.md#gap-01--no-authentication-on-any-endpoint) and [Threat Model T-03](../06_Security/Threat_Model.md).
>
> Every "Authentication / Authorization" row below reads **None (default) / Bearer token if `DW_API_TOKEN` is set** uniformly and is omitted per-endpoint to avoid repetition.

**OpenAPI specification: NOT IMPLEMENTED.** **RECOMMENDED** — generate from route inspection (GAP-17).

---

## Static & mirror

### `GET /`
Serves the SPA. → `200 text/html`.

### `GET /assets/<path:filename>`
Serves `apps/web/assets/*`. → `200` · `404`.
**Note:** `send_from_directory` provides path-traversal protection.

### `GET /mirror/<source_id>`
Serves the demo mirror page for the source's **current world variant** — the variant is not in the URL.

| Case | Response |
|---|---|
| variant is `v5_gone` | `404` with `<h1>404 — page moved</h1>` (deliberate) |
| fixture missing | `404` plain text |
| otherwise | `200 text/html` |

Evidence: `api/app.py :: mirror`

---

## Demo control

### `POST /api/demo/state`
Sets the mirror variant for a source.

**Request**
```json
{ "source_id": "nimbusai-pricing", "variant": "v2_redesign" }
```

`variant` ∈ `v1_baseline` · `v2_redesign` · `v3_semantic` · `v4_material` · `v5_gone`

**Responses**

| Code | Body |
|---|---|
| `200` | `{"source_id": "...", "variant": "..."}` |
| `400` | `{"error": "variant must be one of [...]"}` |

**Validation:** `variant` is checked against the allowlist. **`source_id` is NOT validated** — an unknown id is accepted and stored in the in-memory world dict. Harmless (dict key) but unvalidated.
**Side effects:** mutates in-memory `WorldState`; writes `audit_events` with actor `human`.
**Status:** **VALIDATED** — `test_api.py::test_invalid_variant_rejected`

### `GET /api/demo/state`
→ `200 {"<source_id>": "<variant>", ...}` for all known sources.

---

## Sources

### `GET /api/sources`
List sources with last run, last drift event, scraper, and current mirror variant.

**Response (abridged, real shape)**
```json
[{
  "id": "nimbusai-pricing",
  "name": "NimbusAI — Platform Pricing",
  "vertical": "ai-provider",
  "url": "http://localhost:8000/mirror/nimbusai-pricing",
  "schedule_minutes": 60,
  "status": "active",
  "last_run": { "id": 103, "state": "published", "confidence": 1.0, "credits_spent": 1 },
  "last_event": { "id": 12, "drift_class": 3, "class_label": "Material change",
                  "severity": "warning", "field_changes": [ ... ] },
  "scraper": { "collector_id": "c_replay_nimbusai-pricing", "active_version": 2 },
  "mirror_variant": "v1_baseline"
}]
```

**Performance note:** issues **3 queries per source** (last run, last event, scraper) inside a Python loop — a classic N+1. At 2 sources this is 7 queries. At 100 sources it is 301, each an unindexed scan. See [Database Design § Indexing](../04_Data/Database_Design.md#indexing-analysis).

### `GET /api/sources/<source_id>`
Full detail: source, latest contract (**from the `contracts` table — display only; the engine reads YAML**), scraper, last 40 runs, latest **non-quarantined** snapshot with payload and verdict.
→ `200` · `404 {"error": "unknown source"}`

### `GET /api/sources/<source_id>/timeline`
→ `200 {"runs": [...200], "events": [...100], "heals": [...50]}`.
**No 404** for an unknown source — returns three empty arrays.

---

## Events

### `GET /api/events?limit=100`
Drift events newest-first, each enriched with `class_label` and parsed `field_changes`.
**`limit` is `int()`-cast with no bounds check** — `?limit=99999999` is accepted; a non-numeric value raises `ValueError` → **500**.

### `GET /api/events/<int:event_id>`
Full event: before/after payloads, after-verdict, impact report (with parsed `affected`), alerts, and the triggering heal.
→ `200` · `404 {"error": "unknown event"}`

---

## Healing

### `GET /api/heals`
Last 50 heal events with parsed `preview_payload` and `verification`.

### `GET /api/review`
Heal events with `status = 'review'` — the human queue.

### `POST /api/review/<int:heal_id>` ⚠ **state-changing, unauthenticated**

**Request**
```json
{ "approve": true }
```

**Behaviour**
1. `decide_review()` — loads the heal; **raises `ValueError` if status ≠ `review`**
2. Calls `client.approve(collector_id, reject=not approve)` — the same vendor call the machine path uses
3. On approve: `active_version += 1`; records `decision='human_approved'`, `decided_by='human'`
4. On approve: immediately re-runs the source to verify
5. Returns the updated heal row

| Code | Condition |
|---|---|
| `200` | Decision applied |
| `500` | Heal not awaiting review — **unhandled `ValueError`**; should be `409` |
| `500` | Unknown `heal_id` — same path |

**Idempotency: NO.** A second call after approval raises (status is no longer `review`) and returns 500 rather than a clean conflict.
**Side effects:** vendor API call · version bump · DB writes · a full pipeline run.
**Status:** **VALIDATED** (happy path) — `test_healing.py::test_gray_band_lands_in_review_and_human_approval_uses_same_api`

---

## Ledger & alerts

### `GET /api/ledger?limit=200`
Append-only audit events newest-first with parsed `refs` and `payload`. Same unbounded-`limit` caveat.

### `GET /api/alerts`
Last 50 alerts with parsed payloads. Polled by the SPA for toasts.

---

## Stats

### `GET /api/stats`

```json
{
  "sources": 2,
  "runs": 103,
  "credits_spent": 104,
  "events_by_class": { "Structural drift": 1, "Benign content drift": 1, "Material change": 1 },
  "heal_mttr_seconds": null,
  "heal_mttr_measured_count": 0,
  "heal_verification_pass_rate": 1.0,
  "quarantined_snapshots": 1
}
```

*(Response shown for a fresh seeded DB before any real heal has run — `heal_mttr_seconds` is `null` and `heal_mttr_measured_count` is `0` until one does; both fields update once a real heal completes.)*

> **✅ Resolved 2026-08-22 — `heal_mttr_seconds` no longer mixes seeded and measured data.** `heal_events` gained a real `seeded` column; this endpoint now excludes `seeded = 1` rows from the mean and reports `heal_mttr_measured_count` alongside it, so a caller can distinguish "no real heal yet" (`heal_mttr_seconds: null`, count `0`) from a genuine measurement. Previously it silently averaged `seed.py`'s hardcoded `42.3` rows in with real ones. See [GAP-18](../02_Requirements/Requirements_Gap_Analysis.md).

**`heal_verification_pass_rate`** = approved heals ÷ total heals, with a `or 1` guard against division by zero — meaning **zero heals yields `0.0`, not `null`**. A fresh system reports a 0% pass rate having attempted nothing.

---

## Execution

### `POST /api/run/<source_id>`
Runs one source synchronously through the full pipeline. → `200` with the run summary.

**Summary shape varies by outcome** — a genuine API design weakness:

| Outcome | Keys returned |
|---|---|
| Class 0 | `run_id, class, state, snapshot_id` |
| Published | `run_id, class, state, snapshot_id, event_id, cost_delta_monthly, healed` |
| Class 4 / 5 | `run_id, class, state, event_id` |
| Structural review/quarantine | `run_id, class, state, event_id, heal_event_id` |

Clients must probe for keys. **RECOMMENDED:** one shape with explicit nulls.
**Errors:** unknown source → `ValueError` → **500** (should be 404).

### `POST /api/run-all` ⚠ **expensive, unauthenticated by default**
Runs **every** source sequentially in the request thread. In live mode each `run_scraper` can block up to 900 s, so this can hold a worker for minutes and spend unbounded credits (budget not enforced — GAP-06). Set `DW_API_TOKEN` to require a bearer token here — see the authentication banner above.

### `POST /api/onboard` ⚠ **spends credits, unauthenticated by default**

**Request**
```json
{
  "id": "openai-pricing",
  "name": "OpenAI — API Pricing",
  "url": "https://platform.openai.com/docs/pricing",
  "description": "For every model extract: model id, price per 1M input tokens, ...",
  "vertical": "ai-provider",
  "schedule_minutes": 60
}
```

`id` defaults to a slugified `name`. `url`, `description`, `name` are required → `400` otherwise.

**Response (success)**
```json
{ "source_id": "...", "collector_id": "c_...", "view_url": "https://brightdata.com/cp/scrapers/c_...",
  "ai_flow_steps": ["prepare_intent_analyzer","planner","schema_builder","template_builder","validation_run"],
  "first_run": { ... } }
```

**Response (no contract available) — `422`, added 2026-08-22**
```json
{ "error": "no contract available for this source",
  "detail": "onboarding requires a hand-authored semantic contract at <path> before the first run can pass; none exists for this source_id yet. Write one (copy fixtures/contracts/nimbusai-pricing.yaml as a starting point) and retry — see docs/09_AI_ML/Model_Limitations.md#8",
  "source_id": "..." }
```

> **⚠ This endpoint still cannot *produce* a working source for a genuinely new `source_id`** — that underlying gap ([GAP-04](../02_Requirements/Requirements_Gap_Analysis.md#gap-04--onboarding-cannot-produce-a-working-source)) is unchanged. **What changed 2026-08-22:** the failure mode. Previously it inserted `sources`/`scrapers` rows and paid for a Scraper Studio collector *before* discovering the missing contract, then crashed with a 500 — leaving persistent partial state and consumed credits behind. It now checks for the contract file **first** and returns a clean `422` with no rows written and no vendor call made, before any cost is incurred.

**No validation on `url`** — no scheme check, no SSRF guard. In live mode the URL is passed to the vendor CLI; in replay it is stored and echoed.

---

## Cross-cutting observations

| Aspect | State |
|---|---|
| Authentication / authorization | **NOT IMPLEMENTED** |
| Rate limiting | **NOT IMPLEMENTED** |
| CSRF protection | **NOT IMPLEMENTED** |
| Security headers (CSP, HSTS, X-Frame-Options) | **NOT IMPLEMENTED** |
| CORS | Not configured — same-origin only by default |
| Pagination | `limit` only; no cursor, no bounds check |
| Idempotency keys | **NOT IMPLEMENTED** |
| Consistent error envelope | **PARTIAL** — 400/404 return `{"error": ...}`; 500s return Flask HTML |
| Request validation | `get_json(force=True)` — malformed JSON raises → 500 |
| API versioning | **NOT IMPLEMENTED** — no `/v1` prefix |
| Response field ordering | Deliberately preserved (`app.json.sort_keys = False`) so snapshot tables mirror page order |

**Test coverage: 3 of 19 routes** (`test_api.py`). The untested set includes every state-changing endpoint. See [GAP-11](../02_Requirements/Requirements_Gap_Analysis.md).

---

**Next:** [API Error Catalog](API_Error_Catalog.md) · [Security Architecture](../06_Security/Security_Architecture.md)
