# Judge Evaluation

[← Documentation index](../README.md) · [← USP & Novelty](../01_Product/USP_Novelty.md)

---

> **Standard applied.** The hackathon judges on six equal-weight criteria: **potential impact · creativity/innovation · technical excellence · use of Scraper Studio · reliability and self-healing · presentation.**
> Evidence: `SCRAPE_VERSE_MASTER_STRATEGY.md` — *"Judging (six criteria, equal weight): potential impact · creativity/innovation · technical excellence · use of Scraper Studio ('central to the project') · reliability and self-healing · presentation."*
>
> This document scores against those six as a **hostile but fair judge would**, not as the pre-build strategy document did. `SCRAPE_VERSE_MASTER_STRATEGY.md` self-scored a "Weighted Hackathon Winning Score" of **9.08/10** before a line of code existed — that number reflects concept quality, not build reality, and is not repeated here as a claim. What follows is scored against what the rest of this documentation set has actually verified.

## 1. Potential impact

**What a judge will credit.** The problem is real and specific, not generic: silent semantic drift (a price that "looks" unchanged while its unit definition shifts) breaks downstream systems in a way no structural monitor catches — argued concretely in [Problem Statement](../01_Product/Problem_Statement.md) and demonstrated end-to-end by the Class 4 catch. Impact is quantified in dollars, not just flagged: `impact/cost.py :: _unit_flip_delta` prices a change that has **no numeric delta at all**, which is the harder and more interesting half of the calculation — [USP & Novelty § D1](../01_Product/USP_Novelty.md#d1--change-priced-in-dollars).

**What a hostile judge will attack.** The dollar figure depends entirely on a hand-authored `usage.yaml` profile in a sample repo (`fixtures/sample-repo/`) — it has never been run against a real codebase's real usage data, so "we tell you it costs $626/month" is validated *arithmetic*, not a validated *estimate*. A judge who asks "would this work on my actual repo" gets an honest "the mechanism generalizes, the demo data doesn't" — see [Scope § Out of scope](../01_Product/Scope.md#out-of-scope--deliberate-non-goals) (AST-level call-graph analysis is explicitly a v1 non-goal; entity matching is literal substring/name matching, [`impact/scanner.py`](../03_Architecture/HLD.md)).

**Verdict:** Strong and honestly scoped. The impact claim survives scrutiny because it is narrow and mechanism-explained rather than broad and asserted.

## 2. Creativity / innovation

**What a judge will credit.** [USP & Novelty](../01_Product/USP_Novelty.md) is the rare self-assessment that survives being read adversarially, because it was written adversarially: it applies a three-part novelty test (prior art check, removal test, falsifiability) to every claimed contribution and **explicitly rejects** the claims that don't survive ("novel AI architecture," "AI-powered drift detection," "novel state machine" — all rejected in that document's own table). Two contributions pass all three tests: **N1** (semantic assertions over scraper-captured unit-context text — deleting `_gate_semantics` makes the headline failure case undetectable by every remaining gate) and **N2** (verification-before-approval on AI-generated repairs — deleting `verify_preview()` and trusting the heal's own status would let the system silently activate a wrong template).

**What a hostile judge will attack.** Six of the ten catalogued contributions are explicitly scored "not novel" by the project's own documentation (three-band confidence policy, entity-resolved diffing, protocol seam, zero-noise alerting, and others — [USP & Novelty § Summary](../01_Product/USP_Novelty.md#summary)). A judge who has seen confidence-banded automation before will correctly clock E2 as standard MLOps, not invention — and the documentation says so first, which is the right posture but does not manufacture novelty that isn't there.

**Verdict:** Two genuinely defensible novel mechanisms, both falsifiable by a named test, surrounded by honestly-labelled competent engineering. A judge who values *substance over breadth of claims* scores this well; a judge counting "novel things" on fingers scores it as "two."

## 3. Technical excellence

**What a judge will credit.** An explicit state machine for the pipeline (`RunState`, [`pipeline/runner.py`](../03_Architecture/LLD.md)) where every transition is audited; a four-gate weighted-confidence contract engine shared verbatim between fresh extractions and heal previews ("one definition of correctness everywhere in the system" — `contracts/engine.py` docstring); a `Provider` Protocol whose two methods both return `str`, making it *structurally impossible* for a language model to influence a decision ([ADR-006](../03_Architecture/ADRs/README.md#adr-006--llm-confined-to-prose-behind-a-protocol-defaulting-off)) — a property enforced by the type system, which is a materially stronger claim than "we tested that the LLM doesn't affect decisions." 23 tests pass, `ruff` is clean, CI is green on every push.

**What a hostile judge will attack.** Seven of twelve architecture decisions carry a documented rationale in the code itself — genuinely good for a 7-day build — but the other five are inferred, and two are outright weak: **authentication that exists but is off by default** ([ADR-009](../03_Architecture/ADRs/README.md#adr-009--no-authentication-in-the-reference-build) — mitigated 2026-08-22, still opt-in), and **unjustified three-band gate-weight constants with no sensitivity analysis** ([ADR-007](../03_Architecture/ADRs/README.md#adr-007--three-band-confidence-policy-with-fixed-thresholds), [USP & Novelty § E4](../01_Product/USP_Novelty.md#e4--weighted-confidence-with-partial-credit)). A judge who greps `errors.py` finds a carefully designed error taxonomy the pipeline doesn't use — it raises bare `ValueError` instead ([Engineering Gap Report G-07](Engineering_Gap_Report.md#ranked-gaps)). Three "the system survives failure" claims (`REL-001/002/003`) are `try`/`except` blocks never exercised by a test — see [Reliability & Failure Design § 3](../10_Operations/Reliability_and_Failure_Design.md#3-the-untested-reliability-finding).

**Verdict:** Genuinely strong core engineering (the pipeline, the contract engine, the LLM safety boundary) with real, cheaply-fixable gaps at the edges (auth, unjustified constants, untested handlers). A principal-engineer-level reviewer would approve the architecture and flag the same five things this documentation set already flags.

## 4. Use of Scraper Studio

**What a judge will credit.** Every documented CLI capability is load-bearing, not decorative: `create` for onboarding, `run` with `--version` for pinned rollback, `heal` fed a machine-composed prompt, the `awaiting_approval`/`preview_result`/`approve`/`--reject` gate driven by the confidence policy, and `discover --intent` for Class 5 relocation — see [`SCRAPER_STUDIO.md`](../../SCRAPER_STUDIO.md). This is the strongest possible reading of "central to the project": the product's entire thesis (an autonomous heal loop) is built by closing the human-shaped gap the vendor's own CLI leaves open, per the strategic framing in `SCRAPE_VERSE_MASTER_STRATEGY.md` — *"Bright Data ships heal-on-request with a human at both ends... a product that closes that loop autonomously is building exactly the thing Bright Data left room for."*

**What a hostile judge will attack — this is the single biggest risk in the submission.** [Risk Register R-21](../06_Security/Risk_Register.md) frames the question precisely: *"Judge asks 'show me a real collector ID that ran' — the honest answer is that none exists."* That is still true in the narrow sense that matters — no `collector_id` has ever *run* successfully — but it understates what's actually in the repo: `scripts/spike_out/*.json` holds a real, timestamped Day-0 spike transcript (dated the same day as this review) with two real vendor-issued `collector_id`s and three real vendor error responses — `create` failed `"Automation not allowed"`, `heal` failed `"Self healing tool is temporarily disabled"`, `approve` cascaded from there. No test touches `LiveClient` (verified: zero references anywhere in `backend/tests/`), and every pipeline claim above is proven against `ReplayClient` — a **faithful, behaviourally rich simulation** (154 lines modelling the approval gate, version pinning, and a sabotage hook, not a stub — [ADR-004](../03_Architecture/ADRs/README.md#adr-004--protocol-seam-for-bright-data-with-a-faithful-replay-implementation)), but a simulation nonetheless. The honest answer to "show me a real collector ID" is now stronger than "none exists": it's *"here are two, and here is the vendor's own error explaining why neither completed."* See [AI Architecture § Live-path validation status](../09_AI_ML/AI_Architecture.md#live-path-validation-status).

**Verdict:** The *design* of the Scraper Studio integration is excellent and arguably the project's best "Best Use of Bright Data" argument on paper. The *evidence* that it works against the real vendor is currently zero. This is the one gap that most directly threatens the criterion it's supposed to win — see [Risk Register § R-21 strategy note](../06_Security/Risk_Register.md).

## 5. Reliability and self-healing

**What a judge will credit.** This is the project's most rigorously tested claim. `test_garbage_preview_is_auto_rejected_never_trusted` proves the system refuses a repair it cannot independently verify — most self-healing demos show success; this one demonstrates a **refusal**, which is the harder and more convincing proof. Rollback has no dedicated code path to get wrong: it is the *absence* of a version bump ([ADR-008](../03_Architecture/ADRs/README.md#adr-008--version-pinning-as-the-rollback-mechanism)). The gray-band human-review path calls the identical approval API as the machine path (`decide_review()` and `run_heal()` both converge on `client.approve()` — [USP & Novelty § I1](../01_Product/USP_Novelty.md#i1--closing-a-deliberately-open-vendor-loop)), so there is no parallel "human version" of the approval logic that could silently diverge from the machine version.

**What a hostile judge will attack.** "Reliability" as a *system* property (not just the heal mechanism) is weaker than "self-healing" as a *feature*: `REL-001/002/003` are untested try/except blocks ([§3 above](#3-technical-excellence)), there is no retry/backoff on Bright Data calls despite the pre-kickoff spike observing real 503s (`GAP-09`), and a heal that fails verification twice quarantines silently rather than escalating to a human for a second look — [Model Limitations § 4](../09_AI_ML/Model_Limitations.md#4-a-heal-that-fails-twice-never-reaches-a-human). A judge probing "what happens when this breaks" beyond the demo's scripted variants will find real, if narrow, gaps.

**Verdict:** The self-healing mechanism itself is the project's most defensible technical claim, with a named test that proves the hard case. Reliability *around* that mechanism (retries, exercised failure handlers, escalation past two attempts) is the weakest supporting layer.

## 6. Presentation

**What a judge will credit.** The demo is scripted to a beat sheet with exact timings and API calls ([`DEMO.md`](../../DEMO.md)), runs fully offline against a self-hosted mirror with zero network dependency ([Risk Register R-25](../06_Security/Risk_Register.md)), and is deterministically reproducible via `POST /api/demo/state` — [User Personas § P4](../01_Product/User_Personas.md#p4--hackathon--technical-evaluator-has-10-minutes) exists specifically because this persona was designed for. The killer beat (Class 4 semantic catch: same `$2.50`, unit silently redefined) is the single strongest 15 seconds available to this project, and the demo leads with disclosure of the replay boundary rather than waiting to be asked — the stronger of the two postures identified in [Risk Register § R-21](../06_Security/Risk_Register.md#r-21-deserves-a-strategy-note).

**What a hostile judge will attack.** `/api/stats` reports `heal_mttr_seconds` as a plain mean over `heal_events.mttr_seconds`, which includes `seed.py`'s hardcoded `42.3` seeded rows with no visible marker distinguishing them from genuinely measured cycles — [Risk Register R-03](../06_Security/Risk_Register.md), scored **Critical on credibility rather than system impact**: *"a reviewer who greps `seed.py` finds a fabricated headline metric, and every other number in the documentation becomes suspect by association — including the ones that are honestly measured."* This is the single highest-leverage fix available before submission, precisely because presentation credibility is binary in a judge's mind: one caught fabrication recolors everything else.

**Verdict:** The demo mechanics and honesty-first framing are strong. One unlabelled seeded number sits directly behind the product's headline stat tile and is a live risk to the "this team is rigorous" impression the rest of the documentation set works hard to earn.

## Why we could win

1. Two falsifiable, genuinely novel mechanisms (N1, N2), each provable by naming a single test that fails if the property is removed — a rare property for a hackathon submission to have.
2. The reliability story and the product story are the same story: "the web changed" is both the operational failure and the product's signal, so the demo doesn't need two separate narratives.
3. A refusal-based proof (`test_garbage_preview_is_auto_rejected_never_trusted`) is more convincing than a success-based one, and almost no competing self-healing demo will show this.
4. The documentation itself is evidence of engineering maturity — every claim in this file links to a file, a test, or an explicit "unvalidated" label, which is a defensible answer to any "prove it" question a judge asks live.

## Why we could lose

1. **R-21** — no evidence of a real Scraper Studio call ever succeeding, on the exact criterion ("use of Scraper Studio") the vendor prize is named for. *(Still open as of 2026-08-22 — see item 2 in the table below; the evidence is now stronger than "none exists," but still no success.)*
2. ~~**R-03** — a fabricated headline metric sitting behind the dashboard's primary stat tile, discoverable with one `grep`.~~ **Closed 2026-08-22.**
3. ~~**No authentication** discoverable by any judge who reads `api/app.py` for five minutes~~ — **partially closed 2026-08-22**: an opt-in bearer-token gate now exists, but it is off by default, so a judge who reads the code still finds the *default* posture unauthenticated. The honest framing is now "we built the control, here's how to turn it on" rather than "nothing exists."
4. Six of ten catalogued "contributions" are the project's own documentation admitting they are not novel — a judge who reads only the pitch (not this documentation) might over-claim on the team's behalf and then be corrected by their own materials.

## Top improvements before submission

Ranked by judge-facing leverage, cross-referenced to [Engineering Gap Report § Roadmap](Engineering_Gap_Report.md#roadmap). **Status as of 2026-08-22:**

| # | Fix | Effort | Removes | Status |
|---|---|---|---|---|
| 1 | Exclude seeded MTTR rows from `/api/stats`, or label them visibly in the UI | 30 min | R-03, R-22 — the single highest-leverage credibility fix | ✅ **Done** |
| 2 | `bdata login` + re-run the Day-0 spike; capture one real transcript | ~30 min if account access is unblocked | R-01, R-21 — the largest single win if achievable at all | ⬜ **Still open** — a spike *was* run (`scripts/spike_out/`), and it failed at the vendor (`"Automation not allowed"` / `"Self healing tool is temporarily disabled"`), not in this code; a successful run is still outstanding |
| 3 | Bearer-token auth + bind `127.0.0.1` by default | ~1 h | R-02, downgrades T-01…T-06 | ✅ **Done** (opt-in via `DW_API_TOKEN`) |
| 4 | Validate a contract exists before `create_scraper()` in onboarding; return 422 otherwise | ~30 min | R-04, R-23 | ✅ **Done** |
| 5 | State the replay boundary proactively in the demo narration, before being asked | 0 (already the documented plan — [`DEMO.md`](../../DEMO.md)) | Reframes R-21 from a hidden gap to a disclosed, diagnosed limitation | ⬜ Narration decision, not a code change |

**Four of five items closed same-day (2026-08-22).** Item 2 remains the one item on this list not fully within engineering control — see [AI Architecture § Live-path validation status](../09_AI_ML/AI_Architecture.md#live-path-validation-status) for the real spike transcript and what a genuinely successful attempt would still require.

---

**Next:** [Production Readiness](Production_Readiness.md) · [Demo Runbook](Demo_Runbook.md)
