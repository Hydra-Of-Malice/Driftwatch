# Problem Statement

[← Documentation index](../README.md)

---

## 1. The dependency nobody versions

Modern software depends on facts published on web pages controlled by other organisations:

- model prices and billing units (`$2.50 per 1M input tokens`)
- rate limits and quota tiers
- API parameter names, defaults, and deprecation notices
- vendor terms, SLAs, regional availability

These are **dependencies with no version number, no changelog, no deprecation window, and no notification channel**. A package manager tells you when `requests` changes. Nothing tells you when a pricing page changes.

## 2. Two failure modes

### 2.1 Loud failure — the page breaks the scraper

A site is redesigned. Class names change. Selectors stop matching. Extraction returns null or empty.

This is the failure the industry already understands. It is detectable by definition: the pipeline visibly stops producing data. The cost is maintenance toil — someone must notice, find the new selector, and ship a fix.

### 2.2 Silent failure — the scraper breaks the truth

This is the failure DriftWatch is built for.

> A provider keeps the displayed price at **$2.50** and changes the unit beneath it from *per 1M input tokens* to *per 1M input + output tokens combined*.

Trace what every layer observes:

| Layer | Observation | Correct? |
|---|---|---|
| HTTP fetch | 200 OK | ✅ |
| Selector | matches, returns `"$2.50"` | ✅ |
| Type coercion | parses to `2.50` | ✅ |
| Schema validation | `number`, in range | ✅ |
| Null/coverage checks | all fields present | ✅ |
| Monitoring dashboard | green | ✅ |
| **The number's meaning** | **changed** | ❌ |

Every structural check passes because nothing structural broke. The data is well-formed, plausible, complete — and wrong. Downstream cost models, billing forecasts, and pricing pages silently inherit the error.

**The critical property: no amount of selector robustness detects this.** Self-healing scrapers make loud failure cheaper; they do nothing for silent failure, because there is nothing to heal. The template is working correctly. The world changed.

## 3. Why existing approaches are insufficient

| Approach | What it catches | What it misses |
|---|---|---|
| Scraper health monitoring (null rates, run success) | Loud failure | Silent failure entirely — every metric is green |
| Page-diffing / visual change detection | Any pixel or DOM change | Drowns in noise; cannot distinguish a copyright-year edit from a unit redefinition |
| Schema validation (JSON Schema, Pydantic) | Shape violations | A correctly-shaped number whose meaning changed |
| Self-healing scrapers | Structural breaks | Semantic drift, and the repair itself is unverified |
| Manual review | In principle everything | Does not scale; nobody re-reads a pricing page daily |

The gap is a validation layer that checks **meaning**, and a repair layer whose output is **proven** rather than assumed.

## 4. The second problem: unverified repair

Bright Data Scraper Studio can repair a broken scraper from a natural-language description. Its `heal` command deliberately stops at an approval gate, expecting a human to:

1. notice the scraper broke
2. write a prompt describing what is wrong
3. review the preview output
4. approve or reject

Steps 1–3 are exactly the toil the feature was meant to remove, and step 4 carries a subtler risk: **a repair that reports success is not necessarily correct.** An AI-regenerated template can produce well-formed output that satisfies its own success criteria while extracting the wrong field, the wrong row, or a stale cached value.

Approving on the heal's own say-so replaces one silent failure with another.

## 5. Who this affects

| Affected party | Consequence |
|---|---|
| Teams building on paid model APIs | Cost forecasts drift; overspend discovered at invoice time |
| Price/market intelligence products | Customer-facing numbers wrong, with no internal signal |
| Data engineering teams | Maintenance toil; loss of trust in pipeline dashboards |
| Anyone running scheduled scrapers | Green dashboards that cannot be trusted |

## 6. Magnitude

**No market-size or incident-frequency figures are asserted in this documentation.**

The project has not conducted primary research, and citing third-party market estimates here would not be independently verifiable by a reviewer. Any quantification of "how often does semantic drift occur in the wild" would require a longitudinal study against real public pages that **has not been performed**.

**RECOMMENDED** — the credible way to establish magnitude: run DriftWatch against 20–50 real public pricing and documentation pages for 30 days and report observed drift events by class. This is a measurement the architecture already supports (the audit ledger records every classification); it has simply not been run.

What *is* demonstrable without market data is that the failure mode is real and undetectable by conventional means — which the semantic gate test proves directly.
Evidence: `apps/engine/tests/test_contracts.py::test_semantic_drift_fails_only_the_semantics_gate`

## 7. Requirements this generates

| Need | Requirement |
|---|---|
| Detect meaning change under a passing schema | [FR-004](../02_Requirements/SRS.md#fr-004) |
| Never serve unvalidated data downstream | [FR-011](../02_Requirements/SRS.md#fr-011) |
| Repair structural breaks without a human | [FR-013](../02_Requirements/SRS.md#fr-013) |
| Prove a repair before accepting it | [FR-016](../02_Requirements/SRS.md#fr-016) |
| Quantify what a change costs | [FR-021](../02_Requirements/SRS.md#fr-021) |
| Make every automated decision auditable | [FR-026](../02_Requirements/SRS.md#fr-026) |

---

**Next:** [Project Vision](Project_Vision.md) · [Competitive Analysis](Competitive_Analysis.md) · [USP & Novelty](USP_Novelty.md)
