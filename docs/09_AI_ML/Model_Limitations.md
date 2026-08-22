# Model Limitations

[← Documentation index](../README.md) · [← AI Architecture](AI_Architecture.md)

---

Stated plainly, in the order a reviewer would find them.

## 1. The system's detection ceiling is the hand-authored contract, not the model

Neither the vendor AI nor the internal AI decides what "correct" means — a human writes the `ContractSpec` YAML per source ([Scope § A-4](../01_Product/Scope.md#assumptions)). A page change that produces output passing all four gates because the contract simply never checked the field that changed will publish as Class 0 (no change) or Class 2 (benign), silently. The heal loop and the semantic gate are both *bounded by contract completeness*: they cannot catch what nobody thought to assert. This is not a defect in the AI components — it is a property of the architecture, and it means the product's real detection power is only as good as the contract author's judgement about what "meaning" to encode.

## 2. The semantic gate degrades to schema-only if anchor text disappears

The semantics gate ([`contracts/engine.py :: _gate_semantics`](../03_Architecture/HLD.md)) checks that anchor phrases appear in a sibling `unit_context` field scraped alongside each value. This depends on the page still printing that context text somewhere near the value ([Scope § A-1](../01_Product/Scope.md#assumptions)). A redesign that removes the unit text entirely — rather than changing it — leaves the semantics gate with nothing to check against, and the system silently loses its one mechanism for catching the "$2.50, meaning quietly redefined" case that motivates the whole product (see [Executive Summary](../EXECUTIVE_SUMMARY.md)). No test exercises this specific failure mode (anchor field present but empty/missing vs. anchor field absent from the schema).

## 3. Entity resolution depends on a stable identifier surviving the redesign

Diffing entity-resolves list items by `entity_key` ([Scope § A-2](../01_Product/Scope.md#assumptions)). If a redesign changes the identifying field itself (e.g. a model's `id` slug is renamed as part of the same redesign that changed its price), every entity in that list reads as one removal plus one addition rather than one field change. This produces false Class 3 noise in the best case and, more concerning, can *mask* a real change: an entity that is "removed" and a differently-keyed entity that is "added" in the same run are never diffed against each other, so a genuine price change riding along with a rename is never individually reported as a field-level change.

## 4. A heal that fails twice never reaches a human

Evidence: `healing/orchestrator.py :: run_heal`

The heal loop retries **exactly once** with a refined prompt after an auto-rejected first attempt (`for attempt in (1, 2)`). If the second attempt is also auto-rejected (confidence ≤ `auto_reject_threshold`), the loop exits, the heal event's status is already `"rejected"`, and `pipeline/runner.py :: _handle_structural` sends a critical alert and quarantines the source on its last good version. **The gray-band review queue is only reached if a single attempt lands in the gray band — a doubly-rejected heal is never placed there.** An operator sees the alert and the audit trail, but there is no in-product path to hand a *specific rejected heal* to a human for a second opinion; recovery means manually fixing the contract or the source outside the product. This is a real ceiling on the "autonomous heal loop" claim: it is autonomous up to two attempts, after which it is a dead end requiring out-of-band intervention, not an escalation.

## 5. Anthropic degradation is invisible in the audit ledger

Evidence: `llm/provider.py :: AnthropicProvider._complete`

Every failure mode of the Anthropic call — network error, auth failure, rate limit, a response-shape change, a timeout — is caught by one blanket `except Exception: return None`, and the caller silently falls back to `HeuristicProvider`'s deterministic template. Unlike the Slack alert failure path (`alerts.py`, which writes `db.audit("machine", "alert.slack_failed", ...)`), **no audit event is written when this fallback engages.** An operator watching the ledger cannot tell "this alert used model-quality prose" from "this alert silently degraded to a template because the API key expired." Combined with §7 below (no test exercises this path), a persistent Anthropic outage could go unnoticed indefinitely — the product keeps working, just with quieter prose, and nothing says so.

## 6. No cost or rate governance on the internal model call

Each drift event with a material or semantic classification issues one synchronous Anthropic call, uncapped in aggregate (only `max_tokens` per call is bounded — 120 or 400). There is no batching, no backoff on `429`, and no circuit breaker. A source whose page changes produce many simultaneous field-level drift events (e.g. a full catalog re-price) issues one call per event on the pipeline's own thread, each with a 30 s timeout ([HLD § Communication](../03_Architecture/HLD.md)). This has never been observed to matter because no run in this repository's history has produced that volume — it is genuinely untested at scale, not merely "unlikely to be a problem."

## 7. The vendor AI is fundamentally a black box, by design

DriftWatch has no visibility into the Scraper Studio model's training, versioning, or failure modes for `create`, `heal`, or `discover` — it only ever sees a JSON envelope. This is not a gap to be closed; it is the entire reason the confidence-band verification architecture exists ([ADR-004](../03_Architecture/ADRs/README.md#adr-004--protocol-seam-for-bright-data-with-a-faithful-replay-implementation), [ADR-007](../03_Architecture/ADRs/README.md#adr-007--three-band-confidence-policy-with-fixed-thresholds)). The honest limitation is narrower: the confidence bands that govern how much the vendor's output is trusted were never derived from an observed distribution of real vendor behaviour, because no real vendor call has ever been made — see [AI Architecture § Live-path validation status](AI_Architecture.md#live-path-validation-status). The three-band thresholds (`0.90` / `0.50`) are therefore calibrated against the *replay simulation's* behaviour, not the real model's.

## 8. Onboarding a genuinely new source does not currently produce a runnable pipeline

Evidence: `api/app.py :: onboard`, `contracts/engine.py :: load_spec`

`POST /api/onboard` calls the vendor's `create_scraper` (or its replay simulation) and inserts `sources`/`scrapers` rows, then immediately calls `run_source(source_id, deps)`. `run_source` begins with `load_spec(source_id, deps.contracts_dir)`, which reads `fixtures/contracts/<source_id>.yaml` from disk — a file that exists only for the two demo sources (`nimbusai-pricing`, `payflux-docs`). Onboarding never writes a contract: the AI Flow's generated schema is discarded after being reported in `ai_flow_steps`, not hardened into a `ContractSpec`. **A genuinely new `source_id` onboarded through this endpoint has no contract file on disk, and its immediate first run will fail** rather than silently degrade — this is the concrete mechanism behind [Gap Report G-05 / GAP-04](../11_Assessment/Engineering_Gap_Report.md). Framed as a model limitation rather than a code defect: the vendor's NL-to-schema output is never itself validated as "safe to run against" before the pipeline tries to use it, because nothing translates it into the contract format the pipeline actually reads.

## 9. No adversarial evaluation exists for either prompt surface

Neither the heal-prompt path nor the Anthropic-prompt path has a test that constructs an adversarial page payload (e.g. text designed to redirect the heal toward extracting different fields, or to alter alert sentiment) and asserts on the resulting behaviour. The risk is documented in depth — [Threat Model § T-08](../06_Security/Threat_Model.md#t-08-in-depth--the-ai-specific-threat-that-matters) — but "documented" and "tested" are different claims, and only the first is true here.

## 10. No generation-quality evaluation exists

There is no accuracy, groundedness, or hallucination-rate measurement for `AnthropicProvider`'s output — no eval set, no rubric, no human-rated sample. This is consistent with the system's own design intent (prose quality is explicitly out of the decision path — [ADR-006](../03_Architecture/ADRs/README.md#adr-006--llm-confined-to-prose-behind-a-protocol-defaulting-off)), so the absence is lower-stakes than it would be for a model whose output gated a decision, but it means no claim about *prose quality* — as opposed to *decision safety* — is backed by measurement in this build.

---

**Next:** [Observability](../10_Operations/Observability.md) · [Judge Evaluation](../11_Assessment/Judge_Evaluation.md)
