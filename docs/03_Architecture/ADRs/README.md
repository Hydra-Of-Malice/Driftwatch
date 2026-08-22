# Architecture Decision Records

[← Documentation index](../../README.md) · [← HLD](../HLD.md)

---

> **Provenance warning — read before citing any rationale here.**
>
> This repository contains **no ADR history, no design documents predating the implementation, and no commit history explaining choices** (the history was rewritten; the current history is three commits).
>
> Therefore: **the "Decision" and "Consequences" sections below are observed facts from the code. The "Rationale" sections are inferred and must not be treated as historical record.** Where the code carries a comment or docstring stating a reason, it is quoted and marked *documented*. Everything else is marked *inferred*.

---

## ADR-001 — Modular monolith over services

**Status:** Accepted (observed)
**Context:** A pipeline with one workload, one writer, and a 7-day build window.
**Decision:** One Flask process serving API, SPA, and mirror, with a daemon-thread scheduler.
Evidence: `api/app.py :: create_app`, `serve()`

**Rationale — *inferred*.** No design document states this. Reasonable grounds visible in the code: the pipeline is inherently sequential per source; there is no independent scaling axis; splitting would add deployment surface without removing coupling.

**Trade-offs**
- ✅ One deployable, no inter-service failure modes, fast tests
- ❌ No independent scaling; a live-mode run blocks a Flask worker up to 900 s
- ❌ Scheduler dies with the process

**Reconsider when:** sources exceed ~100, or live-mode runs must not block HTTP.

---

## ADR-002 — SQLite as the only datastore

**Status:** Accepted (observed)
**Decision:** SQLite, WAL mode, per-thread connections, `foreign_keys=ON`.
Evidence: `db.py :: _connect`

**Rationale — *documented*.** `db.py` docstring: *"Deliberately thin: a schema, a per-thread connection, dict rows, JSON columns, and an append-only audit writer. Swapping to Postgres is a driver change, not a redesign — the schema is vanilla SQL."*

**Trade-offs**
- ✅ Zero setup; tests get an isolated DB per case; genuinely portable SQL
- ⚠️ Single writer — the Flask and scheduler threads can still collide under real contention, though `busy_timeout=5000` (added 2026-08-22) now makes a collision retry instead of raising immediately
- ❌ No migrations; `CREATE TABLE IF NOT EXISTS` only
- ❌ JSON columns are unqueryable without `json_extract`

**Reconsider when:** more than one writer process, or JSON payloads need querying.

---

## ADR-003 — Contracts as YAML files, not database rows

**Status:** Accepted (observed) — **and internally inconsistent**
**Decision:** `load_spec()` reads `fixtures/contracts/<source_id>.yaml`.
Evidence: `contracts/engine.py :: load_spec`

**Rationale — *inferred*.** Contracts are code-like artefacts: reviewable, diffable, version-controlled.

> **Inconsistency.** A `contracts` table exists with `version`, `spec`, and `created_from` columns, and `seed.py` populates it. Nothing reads it as a source of truth — `api/app.py :: source_detail` returns it for display only. The system has two contract stores, one authoritative and one decorative.
> **RECOMMENDED:** delete the table, or make it authoritative with the YAML as an import format.

**Trade-offs**
- ✅ Diffable in review; no migration needed to change a contract
- ❌ Contracts cannot be edited through the API
- ❌ Onboarding cannot produce a runnable source (GAP-04)

---

## ADR-004 — Protocol seam for Bright Data with a faithful replay implementation

**Status:** Accepted (observed)
**Decision:** `BrightDataClient` as `typing.Protocol`; `ReplayClient` (fixtures + world state) and `LiveClient` (CLI subprocess).
Evidence: `brightdata/protocol.py`, `replay.py`, `live.py`

**Rationale — *documented*.** `protocol.py`: *"Everything above this interface is identical in replay and live modes; flipping DW_MODE=live is the only change needed."*

**What makes this better than a mock:** `ReplayClient` models the approval gate, version pinning, outdated-template behaviour (`.broken.json`), and a sabotage hook for rejection tests — 154 lines of behaviour, not stubs. This is why the suite tests real decision logic.

**Trade-offs**
- ✅ Fully offline, deterministic tests and demo
- ❌ **The replay client is a model of a system nobody has observed working** (GAP-02). Envelope shapes are asserted to match the real CLI; unverified

---

## ADR-005 — Wrap the official CLI rather than calling REST

**Status:** Accepted (observed)
**Decision:** `LiveClient` shells out to `bdata`/`brightdata` with `--json`.
Evidence: `brightdata/live.py`

**Rationale — *documented*.** *"the CLI already handles auth, AI-Flow polling, the 3-concurrent-job cap with backoff, and stable JSON envelopes. Wrapping it keeps this integration honest to the documented surface and trivially auditable."*

**Trade-offs**
- ✅ Vendor owns auth, polling, concurrency; list-form argv avoids shell injection
- ❌ Requires Node and a global npm install — a real deployment burden
- ❌ 900 s blocking subprocess per call
- ❌ No retry on transient failure (REL-005); the spike observed repeated 503s

---

## ADR-006 — LLM confined to prose, behind a Protocol, defaulting off

**Status:** Accepted (observed)
**Decision:** `Provider` Protocol with two `str`-returning methods; `HeuristicProvider` is the default; `AnthropicProvider` **inherits** from it so failure falls back structurally.
Evidence: `llm/provider.py`

**Rationale — *documented*.** *"The HeuristicProvider is the default and makes the whole system deterministic and offline-runnable… behavior, states and decisions do not change, only prose quality."*

**This is the strongest decision in the system.** Because both interface methods return `str`, it is *structurally impossible* for the model to influence a branch — there is nothing for a conditional to read. Determinism is enforced by type, not by discipline.

**Trade-offs**
- ✅ Fully deterministic; no model dependency; graceful degradation by inheritance
- ❌ Forgoes LLM assistance where it could genuinely help (drafting contracts, adjudicating semantic equivalence)
- ⚠️ Untrusted scraped content still reaches the model's prompt (T-08)

---

## ADR-007 — Three-band confidence policy with fixed thresholds

**Status:** Accepted (observed)
**Decision:** Auto-approve ≥ 0.90; auto-reject ≤ 0.50; human review between. Gate weights 0.35 / 0.25 / 0.25 / 0.15.
Evidence: `config.py`, `contracts/engine.py :: GATE_WEIGHTS`

**Rationale — *inferred*.** No justification appears anywhere in the repository.

> **Weakest-justified decision in the system.** Six constants govern whether an AI-generated template reaches production, and none has a stated derivation or sensitivity analysis. Why 0.90 and not 0.85? Why is schema weighted 0.35? A judge will ask, and the honest answer today is "chosen, not derived."
> **RECOMMENDED:** produce a sensitivity table over the fixture corpus showing decision changes as thresholds vary (GAP-13).

**Trade-offs**
- ✅ Simple, explainable, tunable per deployment
- ❌ Unvalidated constants on the critical path

---

## ADR-008 — Version pinning as the rollback mechanism

**Status:** Accepted (observed)
**Decision:** `scrapers.active_version` advances only after a verified re-run; runs pass `version=` explicitly.
Evidence: `orchestrator.py`, `runner.py :: _handle_structural`

**Rationale — *documented*.** *"Rollback is version pinning: the active version only advances after a verified re-run; a failed heal leaves the previous template active and the interval quarantined."*

Elegant: there is no rollback *operation* to get wrong, because rollback is the absence of a mutation. Failure is the default state.

**Trade-offs**
- ✅ No rollback code path can be buggy; audit trail shows `vN → vN+1`
- ❌ Depends on the vendor honouring `--version` — **unverified** (GAP-02)

---

## ADR-009 — No authentication in the reference build

**Status:** Accepted (observed) — **partially revised 2026-08-22**
**Original decision:** All 19 routes unauthenticated; server binds `0.0.0.0`.
Evidence: `api/app.py`; `serve()` previously had `# noqa: S104 - demo server`

**Rationale — *inferred*.** The `noqa` comment showed the exposure was noticed and consciously waived for demo convenience.

**Update (2026-08-22).** A bearer-token gate (`api/app.py :: _require_auth`) and a `127.0.0.1`-by-default bind (`Settings.host`) now exist. Both are **opt-in** — the default configuration is unchanged so the documented demo flow (`DEMO.md`, `SCRAPER_STUDIO.md`) keeps working without modification. This converts the finding from "no capability exists" to "the operator must choose to enable it," which is a materially better posture but not the same as auth being on by default.

> **Assessment.** Still defensible for a localhost demo in its default configuration; still indefensible anywhere else *if left unconfigured*. `POST /api/review/<id>` still records `decided_by: "human"` for an unauthenticated request unless `DW_API_TOKEN` is set — the audit ledger can still attribute a network call to a person it cannot verify. A system whose thesis is *trustworthy, auditable automated decisions* now has the means to close that gap, one environment variable away.
> This was the highest-severity finding in the review (GAP-01, T-03). ~1 hour to fix — done; the remaining question is whether to make it mandatory rather than optional.

**Reconsider:** whether `DW_API_TOKEN` should be *required* (fail startup if unset and `DW_HOST` is not `127.0.0.1`) rather than merely available, before any non-localhost deployment.

---

## ADR-010 — In-process thread scheduler; the runs table is the queue

**Status:** Accepted (observed)
**Decision:** Daemon thread, 30 s tick, due-source detection from `runs.started_at`.
Evidence: `scheduler.py`

**Rationale — *documented*.** *"The jobs 'queue' is the runs table itself — restart-safe, observable, and visible in the product UI."*

**Partly overstated.** *State* is restart-safe (nothing is lost), but scheduling stops entirely when the process exits, and there is no supervision, leader election, or catch-up policy. A source can silently stop being watched.

**Trade-offs**
- ✅ No broker; schedule state visible in the product's own UI
- ❌ Dies with the process; no HA; a slow run blocks all other sources on that tick

---

## ADR-011 — Zero-build vanilla-ES-module frontend

**Status:** Accepted (observed)
**Decision:** No bundler, no framework. `app.js` (581) + `viz.js` (257) + `styles.css` (213), hash router.
Evidence: `apps/web/`

**Rationale — *inferred*.** Judges can clone and run with no `npm install`; nothing to break in a demo.

**Trade-offs**
- ✅ Zero build step; no supply chain; instant startup
- ❌ **Zero tests** (GAP-07); manual DOM construction risks XSS if `esc()` is missed

---

## ADR-012 — Alert suppression for classes 0–2 as code, not configuration

**Status:** Accepted (observed)
**Decision:** `send_alert()` returns before any write for `NONE` and `BENIGN`.
Evidence: `alerts.py`

**Rationale — *documented*.** *"Zero-noise policy: Classes 0-2 never alert."*

**Trade-offs**
- ✅ Alert fatigue impossible by construction; the guarantee is testable
- ❌ Not configurable; a user wanting benign-change notifications must edit code

---

## Summary

| ADR | Decision | Justification quality |
|---|---|---|
| 001 | Monolith | Inferred, sound |
| 002 | SQLite | **Documented** |
| 003 | YAML contracts | Inferred — **internally inconsistent** |
| 004 | Bright Data seam | **Documented**, well-executed |
| 005 | CLI wrapper | **Documented** |
| 006 | LLM prose-only | **Documented** — strongest decision |
| 007 | Three-band thresholds | **Unjustified** — weakest |
| 008 | Version pinning | **Documented**, elegant |
| 009 | No auth by default | Inferred — **partially mitigated 2026-08-22**, opt-in auth now exists |
| 010 | Thread scheduler | **Documented**, partly overstated |
| 011 | Zero-build SPA | Inferred, reasonable |
| 012 | Alert suppression | **Documented** |

Seven of twelve carry a rationale in the code itself, which is unusually good for a 7-day build. The two weakest — ADR-007's unjustified constants and ADR-009's missing authentication — are both cheap to address.

---

**Next:** [Database Design](../../04_Data/Database_Design.md) · [Security Architecture](../../06_Security/Security_Architecture.md)
