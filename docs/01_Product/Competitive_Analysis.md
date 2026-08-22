# Competitive Analysis

[← Documentation index](../README.md)

---

## Method and honesty note

This compares DriftWatch against **categories of approach**, characterised by their architecture and what they can detect in principle.

**No pricing, market share, or feature claims about specific commercial products are asserted here.** Such claims would require vendor-by-vendor verification this project has not performed, and stating them unverified would violate the documentation's evidence rules. Where a named product is mentioned, it is as a well-known example of a category, and only architectural properties inherent to that category are discussed.

## The discriminating test

Every comparison reduces to one question:

> A page keeps a price at `$2.50` and changes the unit from *per 1M input tokens* to *input + output combined*. Extraction succeeds. The value is unchanged. Does the system raise an alert?

| Category | Detects? | Why |
|---|---|---|
| Scraper health monitoring | ❌ | Every health metric is green; run succeeded, no nulls |
| Uptime / synthetic monitoring | ❌ | Page returns 200 |
| Page-diff / change detection | ⚠️ | Detects *a* change, cannot rank it above a footer edit |
| Schema validation | ❌ | `2.50` is a valid number in range |
| Data-quality frameworks | ⚠️ | Only if someone wrote a rule for this exact unit string |
| Self-healing scrapers | ❌ | Nothing broke; there is nothing to heal |
| **DriftWatch** | ✅ | Semantic gate asserts the unit text must match an anchor |

DriftWatch's answer is not cleverness — it is a **schema requirement**. The contract obliges the scraper to capture `unit_context` verbatim alongside the value, and asserts which phrases must appear in it. Without capturing that field, the check is impossible for anyone.
Evidence: `fixtures/contracts/nimbusai-pricing.yaml`, `contracts/engine.py :: _gate_semantics`

## Category comparison

### A. Scraper health monitoring
**Architecture:** Instrument runs; alert on failure rate, null rate, latency, volume.
**Catches:** Loud failure, reliably.
**Structurally cannot catch:** Any failure where the run succeeds and the data is well-formed.
**Overlap with DriftWatch:** Class 1 detection. DriftWatch additionally repairs and verifies.

### B. Page-diffing / change detection
**Architecture:** Snapshot rendered page or DOM; diff; alert on change.
**Catches:** Every change, including the unit flip.
**Limitation:** Cannot distinguish meaningful from cosmetic. A copyright-year update and a billing-unit redefinition are both "a change". Precision collapses, alert fatigue follows, and the important alert gets muted alongside the noise.
**Contrast:** DriftWatch diffs *extracted structured fields*, not pages, and classifies by cause. Classes 0–2 never alert.
Evidence: `drift/differ.py` operates on extraction payloads; `alerts.py` suppresses 0–2.

### C. Schema / type validation
**Architecture:** JSON Schema, Pydantic, dbt tests.
**Catches:** Shape violations, type errors, range violations.
**Structurally cannot catch:** Semantic change under a valid shape.
**Relationship:** This is **one of DriftWatch's four gates**, weighted 0.35. DriftWatch's claim is that shape validation alone is insufficient, not that it is wrong.

### D. Data-quality / observability frameworks
**Architecture:** Rule engines and statistical anomaly detection over warehouse tables.
**Catches:** Distribution shifts, freshness, volume anomalies, explicit rules.
**Limitation for this problem:** Operates on data already landed in the warehouse — after the wrong number was accepted. Statistical detection also cannot fire when the *value did not change*; a unit flip produces zero distributional signal.
**Contrast:** DriftWatch validates at extraction time and quarantines before publication. The wrong number never lands.

### E. Self-healing scrapers (including Scraper Studio unassisted)
**Architecture:** AI regenerates the extraction template from a natural-language description when it breaks.
**Catches:** Structural breaks — and repairs them, which is genuinely valuable.
**Two gaps DriftWatch addresses:**
1. **A human must drive the loop** — notice the break, write the prompt, review the preview, approve. DriftWatch automates all four.
2. **The repair is unverified.** The heal reports its own success. DriftWatch re-evaluates the preview against the full contract and lets only that verdict decide.
**Relationship:** Complementary, not competitive. Scraper Studio is a dependency; DriftWatch closes its loop.
Evidence: `healing/orchestrator.py`, `healing/verifier.py`

### F. Manual review
**Catches:** Everything, in principle. **Fails:** Does not scale; nobody re-reads a pricing page daily.

## Capability matrix

| Capability | A | B | C | D | E | DriftWatch |
|---|---|---|---|---|---|---|
| Detect extraction failure | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| Repair extraction failure | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Verify the repair** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Detect semantic drift** | ❌ | ⚠️ | ❌ | ❌ | ❌ | ✅ |
| Suppress cosmetic noise | ✅ | ❌ | ✅ | ⚠️ | n/a | ✅ |
| Prevent bad data publishing | ❌ | ❌ | ⚠️ | ❌ | ❌ | ✅ |
| Cost impact of a change | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Map change to call sites | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Audit automated decisions | ⚠️ | ❌ | ❌ | ⚠️ | ❌ | ✅ |
| **Authentication** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Production deployment story** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

The last two rows are included deliberately. Any of these categories, as a commercial product, beats DriftWatch on operational maturity. DriftWatch is a reference implementation of a detection and verification thesis, not a deployable service.

## Where DriftWatch is weaker

Stated plainly:

| Weakness | Detail |
|---|---|
| **Contracts are hand-written** | Categories A–D work out of the box. DriftWatch requires per-source YAML authoring — the highest adoption barrier |
| **Semantic gate needs an anchor field** | If a page prints no unit text near the value, Class 4 detection is impossible (Assumption A-1) |
| **Anchors are substring matches** | `_gate_semantics` lowercases and substring-matches. A page rephrasing the same meaning ("per million input tokens" vs "per 1M input tokens") false-positives unless the anchor list is maintained |
| **Impact scanning is literal** | No AST; misses aliased or dynamically constructed references |
| **Live path unproven** | The whole Scraper Studio integration is validated only in replay |
| **No operational maturity** | No auth, no containers, no migrations, no metrics |

## Positioning

DriftWatch is not "a better scraper" or "a monitoring dashboard". It is **a validation and verification layer** that sits between a scraping platform and its consumers, and its two defensible claims are narrow and testable:

1. Meaning can be made machine-checkable by capturing unit context and asserting anchors over it.
2. An automated repair must be re-proven against the contract that detected the break, or it is not trustworthy.

Both are backed by tests that fail if the property is removed.

---

**Next:** [USP & Novelty](USP_Novelty.md) — a stricter separation of what is genuinely novel
