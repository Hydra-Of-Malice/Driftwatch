# USP & Novelty — a rigorous assessment

[← Documentation index](../README.md)

---

Combining existing technologies is not novelty. This document applies a deliberately hostile standard and separates what is genuinely new from what is competent assembly. Several claims a pitch might make are **explicitly rejected below.**

---

## Test applied

For each claimed contribution:

1. Does prior art exist for this exact mechanism?
2. If removed, does the system lose a capability nothing else provides?
3. Is the claim falsifiable by a test?

Only contributions passing all three are called novel.

---

## Genuine technical novelty

### N1 — Meaning as a machine-checkable contract clause
**Claim:** A data contract can assert *semantic* validity by requiring the extractor to capture the unit/scope text printed adjacent to a value, then asserting anchor phrases over that text.

**Prior art check.** JSON Schema validates shape. Data-quality frameworks validate distributions and explicit rules. Neither has a notion of "this number means USD per 1M *input* tokens, and here is the page evidence." Semantic-web approaches (RDF, schema.org) annotate meaning but require publisher cooperation — the publisher is precisely the uncooperative party here.

**Removal test.** Delete `_gate_semantics` and the `$2.50` unit flip becomes undetectable by every remaining mechanism. Schema passes, invariants pass, continuity passes (the value did not move).

**Falsifiable.** `test_semantic_drift_fails_only_the_semantics_gate` asserts schema ✅ / semantics ❌ on the same payload.

**Verdict: genuinely novel as an engineering mechanism.** The insight is that meaning becomes checkable if you make the extractor capture its own evidence, converting an unanswerable question into a substring assertion.

**Honest limits:** substring matching is brittle to rephrasing; requires the page to print unit text at all; anchor lists need maintenance.

---

### N2 — Verification-before-approval on AI-generated repair
**Claim:** An AI-generated repair must be re-proven against the same contract that detected the break, and the repair's self-reported success must never be the approval criterion.

**Prior art check.** Self-healing scrapers exist and are commercially available. What is not standard is treating the repair as an **untrusted claim** and gating it on independent re-verification. The industry norm is that a heal reporting success is accepted, optionally with a human eyeballing a preview.

**Removal test.** Delete `verify_preview()` and approve on `status == "awaiting_approval"`. The system still "self-heals" — and silently activates templates that extract the wrong field, having only moved the failure downstream.

**Falsifiable.** `test_garbage_preview_is_auto_rejected_never_trusted` sabotages the preview and asserts the version does **not** advance.

**Verdict: genuinely novel as applied to AI-generated scrapers.** The underlying pattern (verify before commit) is old and borrowed from deployment engineering — which strengthens rather than weakens it. Applying `verify → gate → rollback` to AI-generated extraction templates is, as far as this project's research found, not standard practice.

---

## Engineering novelty — sound but not new

### E1 — Five-class drift taxonomy with epistemic precedence
Ordering by *what you can still trust* rather than severity is a genuinely good design decision: availability > structural > semantic > material > benign. If the page cannot be fetched, nothing else is knowable; if extraction is broken, values cannot be trusted; if meaning shifted, the value is untrustworthy even though it parsed.

**Verdict: not novel — well-executed.** Taxonomies of change are common. The classification *criteria* are the interesting part, and they depend on N1.
Evidence: `drift/classifier.py`; six tests

### E2 — Three-band confidence policy
Auto-approve ≥ 0.90, auto-reject ≤ 0.50, human review in between.
**Verdict: not novel.** Confidence-banded automation is standard in ML ops. Competent, correctly implemented, unremarkable.

### E3 — Entity-resolved diffing
Matching list items by entity key rather than index, so reordering is not a change.
**Verdict: not novel.** Standard practice in diffing. Necessary — index-based diffing would make every redesign look like a total rewrite — but not a contribution.

### E4 — Weighted confidence with partial credit
Per-gate scores weighted 0.35/0.25/0.25/0.15, with partial credit for non-schema gates.
**Verdict: not novel, and arguably under-justified.** The weights are unexplained constants with no sensitivity analysis. See [Gap Report G-08](../11_Assessment/Engineering_Gap_Report.md).

---

## Integration novelty

### I1 — Closing a deliberately open vendor loop
Scraper Studio's `heal` stops at an approval gate expecting a human. DriftWatch supplies detection, prompt composition, verification, and decision — then calls the *same* approval API for both machine and human decisions.

**Verdict: modest but real.** The interesting property is that the human path is not a parallel implementation; `decide_review()` and `run_heal()` converge on `client.approve()`. That is good design, not invention.

### I2 — Protocol seam with deterministic offline implementation
`BrightDataClient` as a `typing.Protocol` with `ReplayClient` and `LiveClient`.
**Verdict: not novel — textbook dependency inversion.** Worth noting because the offline implementation is faithful (it models the approval gate, version pinning, and outdated-template behaviour) rather than a stub. That makes the test suite meaningful.
Evidence: `brightdata/replay.py` — 154 lines modelling world state, not a mock

---

## Product differentiation

### D1 — Change priced in dollars
Attaching `cost_delta_monthly` to a drift event, including for unit flips where no price number moved.
**Verdict: differentiating, not novel.** The `_unit_flip_delta` calculation is the interesting half — it prices a change that has no numeric delta at all.

### D2 — Zero-noise alerting as an enforced invariant
Classes 0–2 return before any write, not by configuration.
**Verdict: not novel; disciplined.**

---

## Claims explicitly rejected

A pitch might assert these. They do not survive scrutiny, and are recorded here so nobody repeats them.

| Rejected claim | Why it fails |
|---|---|
| "Novel AI architecture" | No model is trained, fine-tuned, or architecturally modified. The LLM seam generates prose and is optional |
| "Novel use of LLMs for classification" | Classification is deterministic rule evaluation. The LLM never classifies anything |
| "AI-powered drift detection" | Detection is JSON Schema + range checks + substring matching + arithmetic. No AI involved |
| "Production-grade reliability" | No auth, no containers, no migrations, no metrics, single SQLite file |
| "Scalable architecture" | Single process, single SQLite writer, in-process scheduler. Untested beyond 2 sources |
| "Proven self-healing" | Proven **in replay**. The live path has never completed a successful run |
| "Novel state machine" | Explicit state machines are decades old |
| "Innovative audit ledger" | Append-only event logging is standard |

---

## Summary

| Contribution | Category | Verdict |
|---|---|---|
| N1 Semantic contracts with unit anchors | Technical | **Genuinely novel** |
| N2 Verification-before-approval on AI repair | Technical | **Genuinely novel in application** |
| E1 Five-class taxonomy | Engineering | Sound, not novel |
| E2 Three-band policy | Engineering | Standard |
| E3 Entity-resolved diffing | Engineering | Standard, necessary |
| E4 Weighted confidence | Engineering | Standard, under-justified |
| I1 Closing the vendor loop | Integration | Modest, real |
| I2 Protocol seam | Integration | Textbook, well-executed |
| D1 Dollar-denominated impact | Product | Differentiating |
| D2 Zero-noise alerting | Product | Disciplined |

**Two genuine contributions, both falsifiable by a test that fails if the property is removed.** Everything else is competent engineering, and the documentation says so.

Honest framing for a judge: the value is not that DriftWatch invented many things. It is that it identified a real undetectable failure mode, built a mechanism that detects it, and refused to trust its own repairs — then wrote the tests that prove both.

---

**Next:** [SRS](../02_Requirements/SRS.md) · [Judge Evaluation](../11_Assessment/Judge_Evaluation.md)
