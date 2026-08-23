# DriftWatch — the 5-minute presenter script

[← Documentation index](README.md) · [2-minute video beat sheet](DEMO.md) · [Demo Runbook](11_Assessment/Demo_Runbook.md) · [Live validation evidence](LIVE_VALIDATION.md)

> This is the **presenter's** script: what to say, what to click, what the audience sees, beat by
> beat, on a wall clock. [`DEMO.md`](DEMO.md) remains the tighter 2-minute *video* beat sheet — this
> document does not replace it, it expands it for a live 3–5 minute walkthrough.

---

## What is live and what is replay in this demo

**Read this section before you present, and say a compressed version of it out loud at 1:00.**
Being precise here is the difference between a demo that survives a judge's question and one that
does not. The raw request/response evidence for every claim below is in
[`docs/LIVE_VALIDATION.md`](LIVE_VALIDATION.md).

### LIVE and provable, today, on this account

| Capability | Endpoint / command | Result |
|---|---|---|
| Bright Data authentication | `GET /zone/get_active_zones` | **200** |
| Zone access | zones `cli_unlocker` (unblocker), `cli_browser` (browser_api) | present and usable |
| Web Unlocker page retrieval | fetch via `cli_unlocker` | **200**, full page content returned |
| Collector creation | `POST /dca/collector` | **200**, real collector id `c_mt5og4ec1cp5lb1yjd` |
| AI-ranked source discovery | `brightdata discover` | **200**, real ranking: 5 queries → 18 candidates → 3 reranked, 17 s |

Three real `c_*` collectors were created through the CLI against this account:
`c_mt3vr49h1qtwyctl1g`, `c_mt5moeyi28i2av0bzd`, `c_mt5og4ec1cp5lb1yjd`. They are viewable at
`https://brightdata.com/cp/scrapers/<id>`.

### BLOCKED by the vendor, right now

| Capability | Endpoint | Status | Vendor message |
|---|---|---|---|
| Scraper Studio AI Flow (template generation) | `POST /dca/collectors/{id}/automate_template` | **403** | `Automation not allowed` |
| **Self-healing** | `POST /dca/collectors/{id}/refactor_template` | **503** | `Self healing tool is temporarily disabled` |

These are two different blockers and must not be conflated. The 403 is permission-shaped — the same
signature as the 403 on `/customer/balance`, whose body explicitly blames token scope. The **503 is
a server-side global feature disable**: HTTP 503 Service Unavailable, not an account, plan, or
credential problem. No token change and no code change on our side can lift it. The vendor has to
re-enable the feature.

### Therefore

The **break → heal → verify → approve → recover** beats of this demo (2:00 through 4:30) run on
DriftWatch's **deterministic replay world** against a **controlled mirror site we host ourselves**
at `/mirror/<source_id>`. The UI labels this: the demo source's collector id is literally
`c_replay_nimbusai-pricing`, and the Demo controls panel names the variant currently being served.
Nothing on screen pretends to be a live vendor heal.

What is **not** replayed is the part that matters:

- **prompt composition** — `healing/composer.py`, the real deterministic composer, ≤1000 chars
- **4-gate verification** — `contracts/engine.py::evaluate`, the same function that verifies live data
- **three-band approval policy** — `healing/orchestrator.py`, ≥0.90 auto-approve / ≤0.50 auto-reject
  plus one refined retry / in-between to the human review queue
- **version pinning** — the active template version advances only after a *verified re-run*
- **audit ledger** — every machine decision written to `audit_events`

Only the vendor **transport** is replayed. Say it in one sentence on stage:

> *"Bright Data's self-heal endpoint is returning 503 — globally disabled, not an account problem —
> so the vendor call you're about to see is replayed against a mirror site we control. Every
> decision around it is the production code path, and here's the raw 503 if you want it."*

There is also a no-clicking version of beats 2:00–4:30 that runs from a terminal and self-checks
every assertion:

```powershell
powershell -NoProfile -File scripts\heal_demo.ps1
```

Its first line of output states that it is running in replay mode. It exits non-zero if any step
does not behave as expected, and it restores the mirror world to the baseline variant on the way
out — including when it fails.

---

## Setup (before you hit record)

```bash
rm -f driftwatch.db driftwatch.db-*
py -3.12 backend/serve.py          # fresh seeded world, replay mode, http://localhost:8000
```

- Tab 1: `http://localhost:8000` — the DriftWatch SPA, on `#/web`.
- Tab 2: `http://localhost:8000/mirror/nimbusai-pricing` — the controlled mirror page.
- Tab 3: `https://brightdata.com/cp/scrapers/c_mt5og4ec1cp5lb1yjd` — the real Bright Data console.
- Tab 4: an editor showing `fixtures/contracts/nimbusai-pricing.yaml`.
- Open **Demo controls** (bottom-left of the SPA) and leave it open.

Confirm before recording: `#/web` is calm, NimbusAI shows variant `v1_baseline`, no quarantined
snapshots for NimbusAI.

---

## Beat sheet

| t | Beat | Where |
|---|---|---|
| 0:00 | The problem — silent scraper failure | title card / a terminal |
| 0:30 | DriftWatch — the source and its semantic contract | editor: `fixtures/contracts/nimbusai-pricing.yaml` |
| 1:00 | The real Bright Data collector | Bright Data console tab |
| 1:30 | Successful extraction | `#/sources/nimbusai-pricing` |
| 2:00 | The break | Demo controls → `v2_redesign` |
| 2:30 | Detection — which of the 4 gates failed | `#/events/<detection event>` |
| 3:00 | Autonomous heal — the machine-composed prompt | same page, "Self-heal record" card |
| 3:30 | Verification — schema / invariants / semantics / continuity | `#/heal` (+ terminal for per-gate detail) |
| 4:00 | Approval — the three-band policy | `#/heal` → Heal history |
| 4:15 | Recovery — re-run the same collector id | Demo controls → Apply & run all → `#/sources/nimbusai-pricing` |
| 4:30 | Final result — data flowing + the cost / blast-radius payoff | `#/events/<semantic event>` |
| 4:50 | Close | title card |

---

## 0:00 — The problem: silent scraper failure

**Say:**
> "Here's the failure mode nobody has instrumentation for. A scraper you wrote six months ago is
> still running on schedule. Overnight, the site ships a redesign and one selector stops matching.
> The scraper still returns HTTP 200. It still returns valid JSON. The fields are just empty.
> Every dashboard downstream stays green, and your pricing table quietly goes blank."

**Do:** Show the title card, or a terminal with the shape of the broken output.

**Audience sees:** The three lines that make the whole product make sense —
`HTTP 200` · `valid JSON` · `every price is null`. Point at the word "200". That is the whole
problem: the transport succeeded, so nothing alerted.

---

## 0:30 — DriftWatch: the source and its semantic contract

**Say:**
> "DriftWatch watches a source against a *semantic data contract* — not a schema, a contract.
> This is a real file in the repo. It says what shape the data has, what values are plausible, and —
> this is the part nobody else does — what the numbers are *supposed to mean*."

**Do:** Switch to the editor tab on `fixtures/contracts/nimbusai-pricing.yaml`. Scroll to the
`assertions:` block and put your cursor on `anchors:`.

**Audience sees:** Four named blocks in one file: `schema:`, `invariants:`, `assertions:`,
`continuity:`. Highlight this assertion out loud:

```yaml
assertions:
  - field: "models[].price_input_per_1m"
    meaning: "USD per 1 million INPUT tokens, public monthly price"
    unit_context_field: "models[].unit_context"
    anchors: ["per 1M input tokens", "per 1 million input tokens"]
```

> "That's an executable claim about meaning. If the page silently redefines the unit, the number
> still extracts perfectly and this is the only thing in the system that catches it."

---

## 1:00 — The real Bright Data collector

**Say:**
> "The collectors are real. This one — `c_mt5og4ec1cp5lb1yjd` — was created through the Bright Data
> CLI against this account with `POST /dca/collector`, returned 200, and it's here in the console.
> Two honest caveats, and then I'll show you the receipts: the AI Flow step that generates the
> template returns 403 `Automation not allowed`, and the self-heal endpoint returns **503, 'Self
> healing tool is temporarily disabled'** — that's a global server-side feature disable, not
> something wrong with my account. So the heal you're about to watch runs against a mirror site I
> host, clearly labelled as replay, with the real production heal logic around it."

**Do:** Switch to Tab 3 — `https://brightdata.com/cp/scrapers/c_mt5og4ec1cp5lb1yjd`. Read the id off
the URL bar. Then, if a judge wants proof of the blockers, open `docs/LIVE_VALIDATION.md` §
"Two distinct blockers" and show the verbatim 403 and 503 envelopes.

**Audience sees:** A real `c_*` collector id in the real Bright Data control panel, and — the moment
they ask — the raw vendor error bodies. Do not skip the caveat. It is the most credible thirty
seconds in the whole demo.

> Note for the presenter: the demo source inside the SPA shows collector id
> `c_replay_nimbusai-pricing`. That prefix is deliberate and visible. Never present a `c_replay_*`
> id as a Bright Data collector.

---

## 1:30 — Successful extraction

**Say:**
> "Normal operation. The collector runs on a schedule, the payload is verified against the contract,
> and only a payload that passes all four gates is published."

**Do:** Tab 1 → click NimbusAI on the Living Web, landing on `#/sources/nimbusai-pricing`.
(Terminal equivalent: `curl -X POST localhost:8000/api/run/nimbusai-pricing`.)

**Audience sees:** Real structured output — the extracted pricing table, the same shape the contract
declares:

```
model_id             in/1M   out/1M   unit_context
nimbus-large-2         2.5     10.0   USD per 1M input tokens
nimbus-mini-3         0.15      0.6   USD per 1M input tokens
nimbus-vision-1        4.0     16.0   USD per 1M input tokens
```

…plus the verdict badge: **schema ✓ invariants ✓ semantics ✓ continuity ✓, confidence 1.0**, active
template **v2**, snapshot not quarantined.

---

## 2:00 — The failure: introduce the controlled break

**Say:**
> "Now the overnight redesign. I'm flipping the mirror site to a rebuilt layout. Nothing else
> changes — same collector, same contract, same schedule. This is the controlled version of the
> thing that ruins your Tuesday."

**Do:** Demo controls (bottom-left) → **NimbusAI** → select
**`v2 — overnight redesign (breaks template)`** → click **Apply & run all**. Flip to Tab 2 and
reload `/mirror/nimbusai-pricing` so they see the page genuinely looks different.

Terminal equivalent:

```bash
curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v2_redesign"}'
curl -X POST localhost:8000/api/run/nimbusai-pricing
```

**Audience sees:** The mirror page visibly redesigned (card layout instead of the table), and the
Demo controls panel now reading `v2_redesign` — the label that says *this is the replay world*.

---

## 2:30 — DriftWatch detection: which of the four gates failed

**Say:**
> "The scraper did not error. It returned 200 and well-formed JSON with both models present — and
> every price null. A liveness check passes. A schema-only check on `models: minItems 1` passes.
> The contract is what fails, and it tells you exactly which gate and exactly which field."

**Do:** `#/events` → open the newest **Class 1 · Structural drift** event with severity **critical**
(that's the *detection* event; the `info`-severity "redesign absorbed" event right above it is the
post-heal record). Scroll to the verdict panel.

**Audience sees:**

```
schema       FAIL   models.0.price_input_per_1m: None is not of type 'number'
invariants   FAIL   models[nimbus-large-2].price_input_per_1m: expected number in [0.01, 500.0], got None
semantics    FAIL   models[nimbus-large-2].unit_context: page context 'None' matches no anchor
continuity   PASS
composite    FAILED   confidence 0.178
```

And the diagnosis line: **field coverage fell to 17%**. Say the punchline:

> "Three of four gates failed, and the snapshot is quarantined — it never reaches the dashboard.
> The dashboard cannot lie to you, because bad data is never published in the first place."

---

## 3:00 — Autonomous heal: the machine-composed repair prompt

**Say:**
> "Bright Data's heal API expects a *human* to notice the breakage and write a prompt of at most a
> thousand characters describing what's wrong. DriftWatch is that human. It composes the prompt
> deterministically from the diagnosis — the exact failing fields, the coverage drop, and
> last-known-good example values."

**Do:** Stay on the same event page and scroll to the **"Self-heal record"** card — it shows the
decision, the MTTR, and the block labelled *"machine-composed heal prompt (sent to Scraper Studio)"*.
(Terminal equivalent: `curl -s localhost:8000/api/heals | jq -r '.[0].composed_prompt'`.)

**Audience sees:** the machine-written prompt, verbatim, with its character count:

> *"After a page redesign on NimbusAI — Platform Pricing, these fields fail extraction:
> models.0.price_input_per_1m, models.0.price_output_per_1m, models.0.rate_limit_rpm,
> models.0.status, models.0.unit_context, models.1.price_input_per_1m. Field coverage fell to 17%.
> Previously valid values looked like: {"models[].price_input_per_1m": 2.5,
> "models[].price_output_per_1m": 10.0, "models[].rate_limit_rpm": 500, "models[].status":
> "active"}. Fix the template so every field extracts with the same schema and JSON field names as
> before; numeric fields must be plain numbers (no currency symbols), and keep the unit_context
> fields populated with the visible pricing-unit text next to each value."*

> "690 characters, under the thousand-character limit, no human in the loop. That composer is
> `healing/composer.py` and it is the real one — the 503 blocks the call, not the composition."

---

## 3:30 — Verification: the four gates on the repair itself

**Say:**
> "Here's the part I actually care about. The heal comes back with a preview at Bright Data's
> approval gate. DriftWatch does not trust the heal's own success status. It replays that preview
> through the *same* contract engine it uses on live data — the identical function, all four gates."

**Do:** Go to `#/heal` → the **"Autonomous repair sequence"** strip:
`detect ✓ · diagnose ✓ · heal ✓ · verify ✓ 4/4 gates · approve ✓`.

For the per-gate detail on the *preview* — the four named gates with PASS/FAIL — use the terminal;
the strip shows the count, the API shows the names:

```bash
curl -s localhost:8000/api/heals | jq '.[0].verification | {passed, confidence, gates: [.gates[] | {gate, passed}]}'
```

(`scripts\heal_demo.ps1` prints exactly this as its Step 5.)

**Audience sees:** the preview payload with prices restored, and:

```
schema       PASS
invariants   PASS
semantics    PASS
continuity   PASS
composite    PASSED   confidence 1.0
```

> "Schema — is it the right shape. Invariants — are the values in range, are the enums valid, did
> the row count collapse. Semantics — does the unit text still mean what the contract asserts.
> Continuity — is this plausible against the last known good. A repair that produces beautiful
> garbage fails here, and there's a test that proves it does."

---

## 4:00 — Approval: the three-band policy

**Say:**
> "Approval is a policy, not a vibe. Confidence at or above 0.90 auto-approves. At or below 0.50
> it's auto-rejected and retried once with a refined prompt that names the specific failure.
> Anything in between goes to a human review queue — through the same approval API a human would
> have used. Nothing else in the system can approve a heal."

**Do:** Same `#/heal` page → scroll to **Heal history** and point at the top row. Also point at the
**Review queue (0)** heading above it: *"empty, because this one cleared the auto-approve band —
when it doesn't, that queue is where a human lands, with Approve and Reject buttons."*

**Audience sees:** the top row of the heal history table —

```
when        source             decision        by        version   MTTR
just now    nimbusai-pricing   auto_approved   machine   v2→v3     <measured, this run>
```

…and the tiles above: **repairs verified & approved**, **snapshots quarantined**, **credits spent**.
The MTTR tile is labelled *"seeded demo history is excluded"* — say that out loud; it means the
number on screen is a real measurement from this run, not a seeded constant.

> "And the version only moved because the re-run verified. That's the rollback story: a failed heal
> leaves the previous template pinned active and quarantines the interval."

---

## 4:15 — Recovery: re-run the same collector

**Say:**
> "Same collector id. New template version. Run it again against the redesigned page."

**Do:** Demo controls → leave NimbusAI on `v2 — overnight redesign (breaks template)` → click
**Apply & run all** again, then open `#/sources/nimbusai-pricing`.
(Terminal equivalent: `curl -X POST localhost:8000/api/run/nimbusai-pricing` — this is the run the
UI's "Apply & run all" fires.)

**Audience sees:** in the page header, the **same** collector id, now `template v3`; and the
**"Latest verified snapshot — contract-stamped"** table with all three models and all prices back.
The run returns drift class **0 — no change since the last published snapshot**. The pipeline is
quiet again.

Then `#/ledger`, one scroll:

```
run.started → run.diagnosing → heal.requested → heal.preview_verified
→ heal.auto_approved → run.rerunning → heal.rerun_verified → run.published
```

> "Every one of those is a machine decision, written down, with the confidence that produced it."

---

## 4:30 — Final result: data flowing, and the bill

**Say:**
> "Data's flowing again and nobody was paged. But repair isn't the whole job — sometimes the page
> didn't break, it changed *meaning*. Watch this one, because it's the case that has no other
> detector."

**Do:** Demo controls → NimbusAI → **`v3 — unit meaning silently changes`** → **Apply & run all**
→ `#/events` → open the new **Class 4 · Semantic** event.

**Audience sees:** every price numerically **unchanged** — `2.50`, `0.15`, `4.00` — and:

```
schema       PASS
invariants   PASS
semantics    FAIL   'USD per 1M tokens (input + output combined)' matches no anchor
continuity   PASS
```

with the **Blast radius** panel: **+$626/mo**, **9 call sites** across `README.md`,
`src/assistant.py`, `src/billing_guard.py`, `usage.yaml`, and a migration note. The snapshot is
quarantined and an alert fires.

> The cost delta and the call-site count are computed live from `fixtures/sample-repo` and the
> declared usage profile — read them off the screen rather than memorising them; they move if the
> fixture repo changes. Verified on this exact demo path (v2 healed → v3): **$626.0 / 9 sites**.

> "The scraper succeeded. The number is identical. The truth changed — and it's a $626-a-month
> difference across nine places in a codebase. Only a contract catches that."

---

## 4:50 — Close

**Say:**
> "The web changed overnight. DriftWatch noticed, composed its own repair, proved the fix against
> four gates before trusting it, approved it under an explicit policy, pinned the version, and
> priced the blast radius — before anyone's first coffee.
>
> **We didn't build another scraper. We built infrastructure that keeps scrapers alive.**"

---

## Reset between takes

The 4:30 beat leaves NimbusAI on `v3_semantic` and the source in REVIEW. Put the world back before
the next run-through:

```bash
curl -X POST localhost:8000/api/demo/state -H 'Content-Type: application/json' \
     -d '{"source_id":"nimbusai-pricing","variant":"v1_baseline"}'
```

For a genuinely clean take, restart the backend on a fresh database — the replay world tracks which
variants the template has already healed **in process memory**, so a second `v2_redesign` flip
against the same process will not break anything:

```bash
rm -f driftwatch.db driftwatch.db-* && py -3.12 backend/serve.py
```

`scripts\heal_demo.ps1` handles all of this for you: it uses a throwaway database, restores the
baseline variant in a `finally` block even when a step fails, and tells you explicitly if it
detects an already-healed world.

---

## Presenter's Q&A cheat sheet

| Question | Answer |
|---|---|
| "Is the Bright Data integration real?" | Yes. Auth, zones, Web Unlocker retrieval, `POST /dca/collector` (real `c_*` ids) and `discover` are all live and 200. Template generation is 403 and self-heal is 503 — both vendor-side, both documented verbatim in `docs/LIVE_VALIDATION.md`. |
| "So the heal is fake?" | The vendor *transport* is replayed. Prompt composition, 4-gate verification, the approval policy, version pinning and the audit ledger are the production code paths, exercised by `backend/tests/test_e2e_pipeline.py` and by `scripts\heal_demo.ps1`. |
| "Why 503 and not 403?" | Two different blockers. 403 on `automate_template` is permission-shaped. 503 on `refactor_template` is a global server-side feature disable — no token or plan change lifts it. |
| "Does it silently fall back to replay if live fails?" | No. `api/app.py` binds `LiveClient` or `ReplayClient` from `settings.mode` at startup. There is no fallback path, and `scripts\heal_demo.ps1` refuses to run at all unless `DW_MODE=replay`. |
| "What happens if the heal produces plausible garbage?" | Verification rejects it, the previous template stays pinned, and the interval is quarantined. `test_healing.py::test_garbage_preview_is_auto_rejected_never_trusted`. |
| "Can I run this myself?" | `py -3.12 backend/serve.py`, then `powershell -NoProfile -File scripts\heal_demo.ps1`. Fully offline; the script self-checks every step and exits non-zero on any deviation. |
