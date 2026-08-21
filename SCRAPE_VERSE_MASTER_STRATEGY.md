# INTO THE SCRAPE-VERSE — MASTER WINNING STRATEGY
**WeMakeDevs × Bright Data · August 17–23, 2026 · Prepared August 9, 2026**

> Strategy only. No implementation code, no repository, no build commands. One concept gets approved before anything is built.

---

## Research grounding (verified August 9, 2026)

Facts confirmed from the hackathon site and the Bright Data CLI repository, which shape everything below:

- **Core challenge, verbatim:** "Build self-healing web scrapers." This means *every serious team will attempt self-healing*. Self-healing is the entry ticket, not the win condition. The win condition is what the healed data makes possible.
- **Eligibility:** scrapers must **originate from Scraper Studio**; teams of 1–4; public web data only (no login-protected, paywalled, private, or restricted data); AI coding tools allowed with disclosure and demonstrated understanding.
- **Judging (six criteria, equal weight):** potential impact · creativity/innovation · technical excellence · use of Scraper Studio ("central to the project") · reliability and self-healing · presentation.
- **Prizes:** Web-Slinger grand prize (NVIDIA DGX Spark or $5,000, "Best Use of Bright Data") · Suit-Up (iPad per member, "looks and feels finished") · Spider-Sense (Keychron per member, "readable, structured, handled at edges") · $5,000 in Bright Data credits for top teams.
- **Organizer-suggested categories (we must NOT simply reproduce these):** price/inventory intelligence, documentation-to-RAG, competitive intelligence monitoring, market research platforms, developer trend analysis, scraper health monitoring.
- **The decisive CLI fact:** Bright Data's self-healing loop is *human-shaped by design*. `scraper heal` requires a human to (a) notice the scraper broke, (b) write a ≤1,000-character prompt describing what's wrong, and (c) review a `preview_result` at an `awaiting_approval` gate before committing via `scraper approve` (or `--reject`). Runs can pin a `--version`. Creation (`scraper create`) is natural-language via AI Flow (3 concurrent jobs/account), returns a stable `collector_id` and a `view_url`. Free tier: 5,000 credits/month, 1 credit per page load across scrape/search/pipelines/Studio. Also available: `discover` (AI-ranked web discovery with `--intent`), `search` (SERP), `pipelines` (40+ platform extractors), `browser` (remote browser automation), `skill` and `add mcp` (coding-agent integration).

**The strategic opening:** Bright Data ships *heal-on-request with a human at both ends*. A product that closes that loop autonomously — detects breakage via contracts, composes the heal prompt from the failing fields, replays the preview against the contract, and calls approve/reject with an audit trail, escalating to humans only at low confidence — is building exactly the thing Bright Data left room for. That is what "Best Use of Bright Data" looks like.

---

# 1 · EXECUTIVE RECOMMENDATION

**Build Driftwatch: a dependency drift sentinel for the pages your stack silently depends on.**

Every production system depends on facts that live only on unversioned public web pages: model pricing and rate limits on AI-provider pages, API parameters and deprecation notices in vendor docs, plan limits on SaaS pricing pages. Those pages change without announcements, and the change *is* the incident — cost spikes, broken integrations, violated assumptions. Driftwatch turns those pages into **versioned, validated, structured contracts**: Scraper Studio extracts them, a Semantic Contract Engine validates every extraction, a drift taxonomy classifies every change (structural vs. benign vs. material vs. semantic vs. availability), an autonomous heal orchestrator detects breakage, writes the heal prompt, verifies the preview against the contract, and approves or rejects it — and an Impact Graph maps every confirmed material change onto the user's actual codebase and bill: *"this change touches 3 files, 7 call sites, and costs you ≈$412/month starting September 1."*

Why this wins over the other 11 candidates evaluated below:

1. **The reliability story and the product story are the same story.** For most ideas, self-healing is plumbing that keeps a dashboard fresh. Here, "the web changed" is simultaneously the operational problem (scraper breaks → heal) and the product's core signal (dependency changed → alert with blast radius). Judges see one coherent thesis instead of a scraper stapled to an app.
2. **Deepest possible Scraper Studio integration.** It exercises the *entire* lifecycle programmatically — create (NL), run (with version pinning), heal (auto-composed prompts), the approval gate (auto-approve on verified confidence, reject on failed verification, human queue in between), plus `discover` for relocating moved pages. It closes the loop Bright Data intentionally leaves open, which is the strongest "Best Use of Bright Data" argument available.
3. **The judges personally feel the pain.** WeMakeDevs judges are developers; every one of them has been burned by a silent model deprecation, a quiet rate-limit change, or an unannounced docs edit. Demo empathy is the hidden judging multiplier.
4. **It demonstrates the hardest and most memorable failure class:** extraction that *succeeds* while the meaning changes (price still "$0.002" — but now per 1M tokens instead of per 1K). No heal button catches that; only a semantic contract does. That single demo beat separates us from every "we call heal when it 404s" team.
5. **It is honest-demo-able in 2 minutes and buildable in 7 days** with a disciplined scope: 4–6 monitored sources across two verticals (AI-provider pages + payments/vendor docs), one sample codebase for blast radius, one controlled mirror for the live break-and-heal moment, plus a week of *real* catches accumulated by soaking from Day 2.

Finalists behind it: **TermShift** (SaaS pricing/terms semantic drift for procurement) and **RegRadar** (regulatory change intelligence). Both strong; both lose to Driftwatch on judge empathy, demo speed, or feasibility. Full reasoning in §6. The meta-concept **Datalock** (data contracts as a standalone devtool) scored second on paper and is deliberately *merged into* Driftwatch as its engine rather than shipped as a standalone product — rationale in §5.

Weighted Hackathon Winning Score: **Driftwatch 9.08 / 10** (next best standalone: 8.35). Scoring model and all twelve concepts follow.

---

# 2 · THE TWELVE CANDIDATE CONCEPTS

Weighted scores use the formula defined in §4. Every concept is deliberately a *distinct product thesis*, none a reproduction of the organizers' six suggested categories.

---

## Idea 1 — **Driftwatch** · Dependency Drift Sentinel — ★ RECOMMENDED

**A. Name:** Driftwatch
**B. Thesis:** The public web pages your stack depends on — model pricing, API docs, rate limits, plan terms — are unversioned contracts; Driftwatch gives them a validated changelog, a self-healing pipeline, and a blast-radius analysis of what each change costs *you*.
**C. User/problem:** Engineering and platform teams discover upstream changes (model deprecations, price restructures, parameter renames, limit changes) only when production breaks or the invoice arrives. There is no push channel; the page just changes.
**D. Why it matters:** The API economy runs on documentation pages as de-facto contracts. In the AI era this worsened: providers reprice, deprecate, and re-scope limits monthly. The cost of "found out late" is measured in outages and real dollars.
**E. Target users:** Backend/platform engineers, AI engineers, DevOps/SRE, engineering managers, FinOps.
**F. Public data collected:** AI-provider model/pricing/rate-limit/deprecation pages; public API reference and changelog pages of payments/cloud/SaaS vendors; status/announcement pages. All public, no logins.
**G. Why Bright Data is essential:** These pages are JS-heavy, bot-protected, geo-variant, and constantly redesigned. Reliable longitudinal capture needs unblocking infrastructure plus a scraper that can be *regenerated when the page mutates* — exactly Scraper Studio + heal. Without self-healing, a week-old monitor is already rotting.
**H. Scraper Studio usage:** Every source is onboarded by generating a custom Studio scraper from a natural-language description (AI Agent flow → `collector_id`); runs are scheduled via the CLI/API with version pinning; extraction schema comes from the Studio-generated schema, then hardened into a semantic contract.
**I. Self-healing:** Contract validation fails or degrades → orchestrator auto-composes the heal prompt from the exact failing fields ("`price_per_1m_tokens` returns null; previously a number like 2.50 in the pricing table") → `scraper heal` → preview replayed against the contract → auto-`approve` above confidence threshold, reject and retry below it, human review queue in the gray zone → post-approval verification run → ledger entry.
**J. Website changes:** Structural drift → heal path above, invisible to the end user except as a green "self-healed" event. Page moved/removed → availability drift; `discover` with intent ("official pricing page for X") proposes relocation candidates for approval.
**K. Extraction succeeds but meaning changes:** The signature case. Semantic assertions bound to each field ("monthly USD per 1M input tokens, for the Pro tier") are checked by invariants (units, ranges, continuity vs. last-known-good) plus an LLM adjudicator comparing old/new values *with page context*. Unit flips, scope changes ("per minute" → "per day"), and tier redefinitions are caught as **semantic drift**, not silently ingested.
**L. Structured output powers:** The Change Ledger (append-only, versioned history per source), diff timelines, alerts, and the Impact Graph (change → affected files/call sites in a connected repo → cost/behavior delta).
**M. AI capabilities:** NL scraper creation; contract auto-drafting from the first snapshot; drift classification; heal-prompt composition; semantic adjudication; migration-note and cost-delta generation.
**N. Novelty:** Nobody treats *web pages as versioned dependencies with semantic contracts and blast radius*. Diff-watchers exist (visual/pixel or raw-text); none produce validated structured deltas mapped to your codebase and bill.
**O. Alternatives:** Visualping/Distill/ChangeTower (pixel/text diff, no structure, no semantics, no impact); vendor changelogs (voluntary, late, incomplete); status pages (outages only); API-diff tools like oasdiff (require the vendor to publish OpenAPI — most of these facts never appear in a spec).
**P. Why better:** Structured + validated + semantic + personalized impact, on top of infrastructure that survives redesigns. Competitors tell you "pixels changed"; Driftwatch tells you "your September bill grows $412 and here are the 7 call sites."
**Q. Architecture:** Next.js UI · single Python API+scheduler service · Postgres ledger · Bright Data (Studio create/run/heal/approve, discover) · LLM layer for classify/adjudicate/compose · full detail in §9.
**R. Data model:** sources, contracts (versioned), scrapers (collector_id, version), runs, snapshots, drift_events (taxonomy class, severity, confidence), heal_events (trigger, prompt, preview verdict, approval), impacts, alerts, audit ledger — §9.
**S. Main screens:** The Living Web (radial dependency map), Source Seismograph (per-source timeline), Drift Event (before/after semantic diff), Heal Center (pipeline health + review queue), Impact view (blast radius + $ delta), Ledger — §12.
**T. Strongest 2-min demo:** Onboard a source live in ~30s → overnight redesign (controlled mirror) breaks extraction → detection, auto-heal, verified auto-approve on screen → second event where extraction *succeeds* but the unit changed → semantic gate catches it → blast radius + cost delta + Slack alert → week-of-real-catches reel. Full script in §10.
**U. Wow moment:** The pipeline notices its own breakage, writes its own heal prompt, verifies Bright Data's fix against the contract, approves it, and *then* tells you the page change costs you $412/month — all inside 40 seconds, no human touched it.
**V. Realistic in 7 days:** 4–6 sources, 2 verticals, full autonomous heal loop, semantic gates, one connected sample repo for impact, 6 polished screens, Slack alerts, soak-collected real events.
**W. Must NOT build:** Multi-tenant auth/billing, arbitrary-repo language coverage (one sample repo), full OpenAPI diffing, RAG chat over docs, >6 sources, mobile, historical backfill.
**X. Technical risks:** Heal quality/latency unknown until Day-0 spike; AI Flow 3-job cap; LLM misclassification (mitigated by golden sets + thresholds + human queue); live-demo dependency on external services (mitigated by mirror + recorded fallback).
**Y. Judging risks:** Could be mistaken for "docs-to-RAG" or "scraper health monitoring" if pitched lazily — the pitch must lead with *change intelligence and impact*, never with scraping; demo must stay non-technical for the first 60 seconds.
**Z. Judging-criteria fit:** Impact: every dev team, quantified in dollars (9). Creativity: pages-as-versioned-dependencies + semantic contracts (8.5–9). Technical: state-machine pipeline, verification gates, impact graph (9). Studio use: entire lifecycle, programmatic, load-bearing (9.5). Self-healing: autonomous, verified, audited, with rollback (9.5). Presentation: developer-judge empathy + a live heal + a semantic catch (9.5).

**Weighted score: 9.08**

---

## Idea 2 — **TermShift** · SaaS Pricing & Terms Drift Intelligence

**A. Name:** TermShift
**B. Thesis:** The commercial terms of your vendor stack — prices, billing units, plan limits, overage rules — drift silently on public pages; TermShift captures them as structured, validated term-sheets and flags *material* changes with financial impact.
**C. User/problem:** Procurement, finance, and founders find out about vendor repricing at renewal or on the invoice. "Same $29" can hide per-seat→per-user redefinitions, usage-cap cuts, or annual-only switches.
**D. Why it matters:** SaaS spend is a top-3 operating cost; repricing waves are constant; nobody reads 40 vendors' pricing pages monthly.
**E. Target users:** Procurement/FinOps, CFO office, founders, VC portfolio ops.
**F. Data:** Public pricing pages, plan-comparison tables, published limits/fair-use pages of ~30–50 SaaS vendors.
**G. Bright Data essential:** Pricing pages are the most redesign-prone pages on the commercial web (A/B tests, region variants, experiments) — the harshest self-healing environment; geo-targeted scraping (`--country`) also reveals regional price discrimination, a Bright Data-only trick.
**H. Studio usage:** One NL-created Studio scraper per vendor pricing page producing a normalized term-sheet schema (plans[], price, unit, period, limits[], overage).
**I. Self-healing:** Same autonomous detect→compose→heal→verify→approve loop as Driftwatch (shared engine).
**J. Site changes:** A/B variants detected via repeated sampling; redesigns healed; moved pages rediscovered.
**K. Meaning changes:** The category's showcase: "$29/user/mo" → "$29/seat/mo (min 5 seats)" extracts identically at the price node — invariants on unit+minimums plus LLM adjudication catch it.
**L. Output powers:** Vendor term-sheet ledger, renewal-prep briefs, portfolio-wide spend-delta estimates, "regional arbitrage" views.
**M. AI:** Term normalization across wildly different page vocabularies; materiality classification; renewal-brief generation.
**N. Novelty:** Price trackers watch SKUs; nobody ships *contractual-semantics drift* for B2B SaaS as structured events.
**O. Alternatives:** Vendr/Tropic (human-sourced benchmarks, not live monitoring), visual diff tools, spreadsheets.
**P. Better because:** Continuous, structured, semantic, and quantified against *your* seat counts.
**Q. Architecture:** Identical engine to Driftwatch, different contract library + UI vocabulary.
**R. Data model:** vendors, term_sheets (versioned), plans, limits, drift_events, impact (seat-count × delta).
**S. Screens:** Vendor grid, term-sheet diff view, renewal calendar with drift annotations, spend-delta dashboard.
**T. Demo:** Onboard a vendor live → staged repricing on mirror → heal → semantic catch on unit redefinition → "your 40-seat plan grows $3,840/yr" alert.
**U. Wow:** Same-price-different-meaning caught live, priced against your seats.
**V. 7-day scope:** 10–15 vendors, term-sheet contracts, heal loop, renewal dashboard.
**W. Don't build:** Negotiation benchmarks, contract-document parsing, procurement workflow.
**X. Tech risks:** Pricing-page A/B noise creates false drift (needs multi-sample consensus — extra work); geo variants complicate "truth."
**Y. Judging risks:** Reads adjacent to the organizers' "price intelligence" category unless the *semantic/terms* framing lands; buyer pain is real but *judges are not the buyer* — less demo empathy from a developer panel.
**Z. Criteria fit:** Impact 8 (real dollars, narrower audience), Creativity 7.5, Technical 8, Studio 9, Healing 9 (brutal page class = great story), Presentation 8.5.

**Weighted score: 8.35**

---

## Idea 3 — **RegRadar** · Regulatory Change Intelligence

**A. Name:** RegRadar
**B. Thesis:** Regulators publish rule changes as edits to ugly public pages; RegRadar turns selected regulatory domains (e.g., data-privacy guidance, import tariffs, medical-device notices) into a validated, diffed, plain-language change feed with applicability tags.
**C. User/problem:** Compliance teams and SMBs learn about changed guidance late, from consultants or fines; primary sources are unreadable and unannounced.
**D. Why it matters:** Highest raw stakes of any candidate — legal exposure, tariffs, safety.
**E. Users:** Compliance officers, trade/logistics SMBs, legal-tech, journalists.
**F. Data:** Public regulator pages: guidance documents, fee schedules, tariff tables, enforcement notices (all public by law).
**G. Bright Data essential:** Government sites are archaic, structurally inconsistent, and change layout without notice — self-healing gold; geo-access sometimes matters.
**H. Studio usage:** NL-created scrapers per regulator section; schemas per document type (notice, fee table, guidance rev).
**I–J. Healing/changes:** Same shared engine; government redesigns are rare but catastrophic when they happen — heal + `discover` relocation both showcased.
**K. Meaning drift:** Critical and subtle: "guidance updated" vs. "page reorganized"; effective-date semantics; the adjudicator must separate *regulatory* change from *editorial* change — genuinely hard, genuinely valuable.
**L. Output powers:** Change feed with severity + applicability ("affects importers of X"), deadline calendar, diffed clause view.
**M. AI:** Plain-language summarization of legalese diffs; applicability classification; effective-date extraction.
**N. Novelty:** Compliance-alert vendors exist but are human-curated, expensive, enterprise-only; a self-healing primary-source engine is new.
**O. Alternatives:** Thomson Reuters/LexisNexis alerts (curated, $$$), agency mailing lists (spotty), consultants.
**P. Better:** Minutes-latency, primary-source, affordable, structured.
**Q–R.** Shared engine; entities: regulators, documents, clauses, revisions, drift_events, applicability tags.
**S. Screens:** Regulator map, document timeline, clause diff with plain-language sidebar, deadline calendar.
**T. Demo:** Watch a tariff-fee table; staged change on mirror; heal; semantic catch ("fee unchanged but scope of applicable goods expanded"); alert with affected-category list.
**U. Wow:** Legalese diff → one-sentence "what changed for you," with the pipeline having healed itself en route.
**V. 7-day scope:** 1–2 regulatory domains, 5–8 sources, feed + diff view.
**W. Don't build:** Multi-jurisdiction coverage, legal-advice framing, full document OCR pipelines.
**X. Tech risks:** Highest source difficulty (PDF-embedded tables, glacial servers); real drift unlikely to occur naturally during the week → demo leans almost fully on staged changes.
**Y. Judging risks:** Developer judges respect it but don't *feel* it; "is this legal advice?" questions; drier demo.
**Z. Fit:** Impact 9.5 (best of all twelve), Creativity 7.5, Technical 8.5, Studio 8.5, Healing 9, Presentation 7.

**Weighted score: 8.30**

---

## Idea 4 — **ShrinkRay** · Listing-Integrity & Shrinkflation Observatory

**A. Name:** ShrinkRay
**B. Thesis:** "Same price" is not "same product": ShrinkRay watches retail listings for quantity, size, and spec downgrades — semantic drift as a consumer-protection product.
**C. Problem:** Shrinkflation and spec-swaps (net weight 500g→450g, warranty 2y→1y, "cotton"→"cotton-blend") are invisible at the price tag.
**D. Matters:** Consumer trust + genuine media resonance; regulators in several countries now require shrinkflation disclosure.
**E. Users:** Consumer media, watchdog orgs, deal communities, curious shoppers.
**F. Data:** Public product listing pages (title, price, pack size, specs) across a curated basket of ~50 products.
**G. Bright Data:** Retail sites are the most anti-bot-protected class on the web — unblocking is non-negotiable; layout churn is constant → healing.
**H. Studio:** NL-created per-retailer scrapers normalizing to product contracts (price, quantity, unit_price, key specs).
**I–J.** Shared healing engine; retailer template changes are frequent → lots of authentic heal events during a one-week soak.
**K. Meaning drift:** *Is* the product: price node identical, quantity node shrinks — unit-price invariant fires.
**L. Powers:** Unit-price history, "shrink events" feed, basket report card, shareable change cards.
**M. AI:** Spec normalization; shrink-vs-reformulation classification; report generation.
**N. Novelty:** Price trackers watch price; nobody tracks *value density* as structured events.
**O. Alternatives:** CamelCamelCamel/Keepa (price only), news anecdotes.
**P. Better:** Systematic, evidence-grade (before/after snapshots), cross-retailer.
**Q–R.** Shared engine; entities: products, listings, snapshots, shrink_events.
**S. Screens:** Basket grid, unit-price timeline, shrink-event card (before/after photos + fields), leaderboard of offenders.
**T. Demo:** Live basket → staged quantity change on mirror → heal → unit-price invariant fires → shareable "shrink card" generated.
**U. Wow:** "The price didn't change. The chips did." — before/after card.
**V. 7 days:** 50-product basket, 3–4 retailers, events feed, cards.
**W. Don't:** Full category coverage, mobile app, user accounts.
**X. Tech risks:** Retailer blocking hardest here (though that flatters Bright Data); product-page variance high.
**Y. Judging risks:** Collides head-on with organizers' "price and inventory intelligence" category; reads consumer-cute rather than deep; technical ceiling lower.
**Z. Fit:** Impact 7, Creativity 8, Technical 7.5, Studio 8, Healing 8.5, Presentation 9+ (most memorable single beat of all twelve).

**Weighted score: 8.03**

---

## Idea 5 — **TenderGraph** · Public Procurement Radar

**A. Name:** TenderGraph
**B. Thesis:** Government tender portals are fragmented and unreadable; TenderGraph normalizes them into structured, entity-resolved opportunities matched to a company profile.
**C. Problem:** SMBs miss winnable public contracts because discovery means manually checking dozens of hostile portals.
**D. Matters:** Public procurement is ~12–15% of GDP in most economies; SMB participation is a policy goal everywhere.
**E. Users:** SMB owners, bid consultants, civic-tech.
**F. Data:** Public tender listings: title, buyer, category, value, deadlines, documents (public by mandate).
**G. Bright Data:** Portals are the ugliest HTML in production anywhere; layouts differ per ministry and mutate — healing is survival, not a feature.
**H. Studio:** One NL-created scraper per portal → normalized tender contract.
**I–J.** Shared engine; portal redesigns are common enough to demo authentically.
**K. Meaning drift:** Deadline format changes, value stated ex/inc tax, category recodings — materially dangerous, adjudicator catches.
**L. Powers:** Matched-opportunity feed, deadline calendar, buyer history graph.
**M. AI:** Category normalization, match scoring vs. company profile, bid-brief generation.
**N. Novelty:** Aggregators exist per-country and are paid/enterprise; a self-healing open pipeline with entity resolution across portals is fresh.
**O. Alternatives:** TendersInfo/BidNet/etc. (paywalled, stale), portal emails.
**P. Better:** Fresh, matched, free-tier-friendly, resilient.
**Q–R.** Shared engine; entities: portals, tenders, buyers, matches.
**S. Screens:** Match feed, tender detail with diff history, calendar, buyer profiles.
**T. Demo:** Profile in → matched tenders out → staged portal redesign → heal → "deadline moved up 10 days" alert.
**U. Wow:** "This ₹80-lakh tender matches you; deadline moved yesterday; portal changed layout last night and the pipeline healed itself."
**V. 7 days:** 2–3 portals, matching, calendar.
**W. Don't:** Bid submission, document parsing, all-portal coverage.
**X. Tech risks:** Highest source hostility + variance; some portals gate documents behind registration (must stay on public listings only); CAPTCHAs may fight even Bright Data at scale.
**Y. Judging risks:** Regional (judges may not know the portals); demo drier; feasibility doubts show.
**Z. Fit:** Impact 9, Creativity 7, Technical 8, Studio 8.25, Healing 8.5, Presentation ~6.8, Feasibility 5.5 (worst of the finalists' rivals).

**Weighted score: 7.83**

---

## Idea 6 — **CiteGuard** · Research Citation Integrity Monitor

**A. Name:** CiteGuard
**B. Thesis:** Retracted and corrected papers keep being cited as if valid; CiteGuard watches public retraction/correction pages and alerts anyone whose bibliography just went stale.
**C. Problem:** Researchers unknowingly cite retracted work; journals publish corrections nobody sees.
**D. Matters:** Scientific-integrity crisis is real and press-visible.
**E. Users:** Researchers, journal editors, science journalists, universities.
**F. Data:** Public retraction notices, publisher correction pages, preprint status pages.
**G. Bright Data:** Publisher pages vary wildly and are semi-protected; longitudinal watching needs healing.
**H. Studio:** Scrapers per publisher notice-format → retraction contract (DOI, reason, date, scope).
**I–K.** Shared engine; semantic subtlety: "correction" vs "expression of concern" vs "retraction" — taxonomy matters and the adjudicator earns its keep.
**L. Powers:** Bibliography checker (paste a .bib → verdicts), watchlists, alert feed.
**M. AI:** Notice classification, scope extraction, plain-language "what this retraction means."
**N. Novelty:** Retraction Watch exists as *journalism*; a structured self-healing pipeline + personal bibliography mapping is new.
**O. Alternatives:** Retraction Watch database (manual, lagging), Crossref metadata (incomplete for reasons/scope).
**P. Better:** Fresh, structured, personalized to your citations.
**Q–R.** Shared engine; entities: papers, notices, bibliographies, matches.
**S. Screens:** Bibliography report card, notice feed, paper timeline.
**T. Demo:** Paste bibliography → 2 flagged; staged notice change → heal → new flag propagates to the bibliography.
**U. Wow:** "Your literature review cites a paper retracted 9 days ago."
**V. 7 days:** 3–4 publishers, .bib matching, feed.
**X. Tech risks:** Sparse natural change during hackathon week; DOI entity-resolution edge cases; source list curation is real work.
**Y. Judging risks:** Niche empathy; impact real but slow-burn; demo depends fully on staging.
**Z. Fit:** Impact 8.5, Creativity 8.5, Technical 7.5, Studio 7.25, Healing 7, Presentation 7.3.

**Weighted score: 7.58**

---

## Idea 7 — **StackSignal** · Startup Strategy Inference Engine

**A. Name:** StackSignal
**B. Thesis:** A company's public exhaust — careers pages, changelogs, pricing, blog cadence — leaks its strategy; StackSignal converts that exhaust into structured signals and *inferences* ("moving upmarket," "pivoting to agents") with evidence chains.
**C. Problem:** Founders/investors track competitors by rumor and screenshots.
**D. Matters:** Strategy surprise is expensive; the signals are public and ignored.
**E. Users:** Founders, VCs, product managers, BD teams.
**F. Data:** Careers pages (roles, counts, locations), changelogs, pricing tiers, blog/press pages of chosen companies.
**G. Bright Data:** Careers/changelog pages churn constantly (ATS widgets, redesigns) — healing keeps the longitudinal series alive, which is the whole value.
**H. Studio:** Per-page-type NL scrapers (careers contract, changelog contract, pricing contract).
**I–K.** Shared engine; semantic drift example: role titled "ML Engineer" recategorized under new team names — entity resolution across renames.
**L. Powers:** Signal timeline per company, inference cards with evidence, weekly brief.
**M. AI:** Signal extraction → multi-signal inference with confidence + evidence citations (the differentiator vs. dumb trackers).
**N. Novelty:** Trackers list changes; StackSignal argues *conclusions* with cited evidence.
**O. Alternatives:** Klue/Crayon (enterprise CI, human-curated), Google Alerts.
**P. Better:** Evidence-chained inference, live, affordable.
**X. Tech risks:** Inference quality is hard to validate in 7 days; hallucinated strategy claims would be embarrassing in front of judges.
**Y. Judging risks:** Sits closest to the organizers' "competitive intelligence monitoring" category of any candidate; the inference layer must carry the whole novelty burden.
**Z. Fit:** Impact 7.5, Creativity 7, Technical 7.5, Studio 8, Healing 8, AI 8.5, Presentation 7.5.

**Weighted score: 7.63**

---

## Idea 8 — **DepPulse** · OSS Dependency-Health Radar

**A. Name:** DepPulse
**B. Thesis:** Open-source abandonment is gradual and public; DepPulse scores maintenance risk of your dependencies from public repo/docs/release signals before you adopt or while you depend.
**C–E.** Problem: teams adopt dying libraries; users: engineers, security teams.
**F. Data:** Public repo pages, release/changelog pages, docs staleness, issue-velocity signals.
**G. Bright Data — the fatal flaw:** Most of this data has *official APIs* (GitHub REST/GraphQL, registries). Judges will ask "why scrape?" and the honest answer is "we shouldn't." Only docs-staleness and off-platform signals genuinely need scraping.
**H–M.** Shared engine mechanics apply, but Studio would be decorative — disqualifying under "central to the project."
**N–P.** Novel-ish scoring, but deps.dev / Snyk Advisor / Libraries.io already occupy the space.
**X–Y. Risks:** "Why not the API?" is unanswerable; alternatives are strong incumbents.
**Z. Fit:** Impact 8, Creativity 7.5, Technical 8, **Studio centrality 6.5**, Healing 7.5, Presentation 7.2.

**Weighted score: 7.40**

---

## Idea 9 — **LookaLens** · Brand-Impersonation Watch (public data only)

**A. Name:** LookaLens
**B. Thesis:** Fake storefronts and lookalike sites clone brands in public; LookaLens discovers candidates (search + discover), fingerprints their public pages structurally and visually, and produces evidence-grade impersonation reports.
**C–E.** Problem: brand/phishing abuse; users: brand-protection teams, SMB founders.
**F. Data:** Public pages of suspected lookalikes (typosquat permutations, marketplace clones), the brand's own public pages as reference.
**G. Bright Data:** Cloaked sites serve different content to different IPs/geos — Bright Data's geo/residential unblocking is uniquely suited; `discover`/`search` for candidate generation.
**H. Studio:** Scrapers extract page fingerprints (logo refs, titles, checkout wording) → similarity contracts.
**I–K. The structural weakness:** Self-healing exists but is *not load-bearing* — adversaries don't "drift," they evade; the hackathon's core axis (site changes → heal → continuity) is peripheral here.
**L–N.** Powers takedown-evidence reports; novel in the open-tool space.
**X. Tech risks:** Perceptual/DOM similarity in 7 days is real work; false accusations are hazardous.
**Y. Judging risks:** Weak self-healing story on the criterion that defines the event; ethical edge-cases.
**Z. Fit:** Impact 8, Creativity 8, Technical 8.5, Studio 7.25, **Healing 6**, Presentation 8.
 
**Weighted score: 7.53**

---

## Idea 10 — **CivicScope** · Municipal Decisions Intelligence

**A. Name:** CivicScope
**B. Thesis:** Council agendas, minutes, and permit filings are public but unreadable; CivicScope turns selected municipalities' pages into a structured civic feed ("what your city decided this week").
**C–E.** Users: journalists, civic groups, residents, real-estate.
**F. Data:** Public agendas/minutes/permit registers.
**G. Bright Data:** Municipal sites = archaic, fragile, redesign-prone → authentic healing showcase.
**H–K.** Shared engine; semantic drift: agenda item renumbering, "approved" vs "deferred" status vocabularies.
**L–N.** Powers digest feeds; novelty moderate (Councilmatic-style projects exist, US-centric, brittle).
**X. Risks:** Per-city source work is heavy; PDFs everywhere (OCR scope creep).
**Y. Risks:** Demo is worthy-but-dry for a developer judging panel; impact diffuse.
**Z. Fit:** Impact 8.5, Creativity 7, Technical 7.5, Studio 8.5, Healing 9, Presentation 6.3.

**Weighted score: 7.75**

---

## Idea 11 — **MedShelf** · Essential-Medicine Price & Availability Monitor

**A. Name:** MedShelf
**B. Thesis:** Prices and availability of essential medicines vary wildly across public pharmacy sites; MedShelf monitors a fixed essential-medicines basket for price dispersion and stockouts as a public-interest observatory.
**C–E.** Users: patients, journalists, health NGOs.
**F. Data:** Public pharmacy listing pages for a curated medicine basket.
**G. Bright Data:** Pharmacy platforms are bot-protected and layout-churning; geo matters.
**H–K.** Shared engine; semantic drift: pack-size and formulation changes masquerading as price stability (shrinkflation's medical cousin).
**L–N.** Powers dispersion maps, stockout alerts; strong public-interest narrative, especially for an India-based team demoing local reality.
**X. Risks:** Medical-adjacent framing needs care (information, not advice); availability ground-truth is noisy.
**Y. Risks:** To judges it *reads* as a price tracker with a halo — collides with the organizers' price-intelligence category and with the elimination rule against simple price trackers, however unfairly.
**Z. Fit:** Impact 9, Creativity 6.5, Technical 6.5, Studio 8, Healing 8, Presentation 7.3.

**Weighted score: 7.58**

---

## Idea 12 — **Datalock** · Data Contracts for the Living Web (meta-concept)

**A. Name:** Datalock
**B. Thesis:** A developer tool where any Studio scraper gets a *semantic data contract*; Datalock continuously validates extractions, classifies drift, orchestrates heal-verify-approve autonomously, and gives every scraped dataset a trust score and audit ledger.
**C–E.** Users: every team running scrapers in production; data engineers.
**F. Data:** Whatever its users scrape (domain-agnostic).
**G–J. Bright Data fit:** The deepest possible — it is *purely* the closing of Bright Data's human-shaped loop; every CLI capability is load-bearing.
**K.** Semantic contracts are its entire identity.
**L–N.** Powers trust-scored datasets; genuinely novel (semantic contract testing for scraped data doesn't exist as a product).
**O–P.** Alternatives: Great Expectations/Soda (warehouse data-quality, no web/heal awareness), Monte Carlo (enterprise observability) — none touch scraper repair.
**Q–V.** Engine identical to §9 (it *is* §9); demo must invent a use case anyway.
**X. Tech risks:** Low — smallest surface of all twelve.
**Y. Judging risks — decisive:** (1) It collides with the organizers' listed "scraper health monitoring" category and the elimination rule against scraper-monitoring dashboards; (2) an abstract infra demo forces judges to imagine the value ("so what do I *see*?"), and 2-minute abstract demos lose to concrete ones; (3) impact scores require a story about someone's Tuesday, which Datalock can only tell through a borrowed vertical.
**Z. Fit:** Impact 8, Creativity 8.5, Technical 9, Studio 9.5, Healing 9.5, Presentation 6.8.

**Weighted score: 8.53** — second-highest on paper. **Resolution: merged into Driftwatch** as its engine (§5 explains why it must not ship standalone).

---

# 3 · COMPARISON MATRIX

All dimensions scored 1–10. (Imp = impact, Nov = novelty, Tech = technical depth, BDI = Bright Data integration, Stu = Scraper Studio centrality, Heal = self-healing depth, AI = AI value, UI = UI potential, Demo = demo potential, Feas = 7-day feasibility, Comm = commercial potential, Mem = judge memorability.)

| # | Concept | Imp | Nov | Tech | BDI | Stu | Heal | AI | UI | Demo | Feas | Comm | Mem | **Weighted** |
|---|---------|-----|-----|------|-----|-----|------|----|----|------|------|------|-----|--------------|
| 1 | **Driftwatch** | 9 | 8.5 | 9 | 9.5 | 9.5 | 9.5 | 9 | 9 | 9.5 | 8 | 8.5 | 9 | **9.08** |
| 12 | Datalock (merged → 1) | 8 | 8.5 | 9 | 9.5 | 9.5 | 9.5 | 8 | 7 | 6.5 | 7 | 8 | 7 | **8.53** |
| 2 | **TermShift** | 8 | 7.5 | 8 | 9 | 9 | 9 | 8 | 8.5 | 8.5 | 8.5 | 8.5 | 8 | **8.35** |
| 3 | **RegRadar** | 9.5 | 7.5 | 8.5 | 8.5 | 8.5 | 9 | 8.5 | 7.5 | 7 | 6.5 | 8 | 7.5 | **8.30** |
| 4 | ShrinkRay | 7 | 8 | 7.5 | 8 | 8 | 8.5 | 7 | 8 | 9.5 | 8.5 | 7 | 9.5 | **8.03** |
| 5 | TenderGraph | 9 | 7 | 8 | 8.5 | 8 | 8.5 | 8 | 7 | 6.5 | 5.5 | 8.5 | 7 | **7.83** |
| 10 | CivicScope | 8.5 | 7 | 7.5 | 8.5 | 8.5 | 9 | 7.5 | 6.5 | 6 | 6 | 6 | 6.5 | **7.75** |
| 7 | StackSignal | 7.5 | 7 | 7.5 | 8 | 8 | 8 | 8.5 | 8 | 7.5 | 8 | 8 | 7 | **7.63** |
| 6 | CiteGuard | 8.5 | 8.5 | 7.5 | 7.5 | 7 | 7 | 8 | 7 | 7 | 6 | 6.5 | 8 | **7.58** |
| 11 | MedShelf | 9 | 6.5 | 6.5 | 8 | 8 | 8 | 6.5 | 7 | 7.5 | 7.5 | 6.5 | 7.5 | **7.58** |
| 9 | LookaLens | 8 | 8 | 8.5 | 8 | 6.5 | 6 | 7.5 | 7.5 | 8 | 6 | 8 | 8.5 | **7.53** |
| 8 | DepPulse | 8 | 7.5 | 8 | 6.5 | 6.5 | 7.5 | 8 | 7.5 | 7 | 7.5 | 7 | 7 | **7.40** |

---

# 4 · SCORING MODEL AND EXPLANATIONS

**Weighted Hackathon Winning Score** = 15% Impact + 15% Creativity + 15% Technical excellence + 20% Bright Data integration + 15% Self-healing/reliability + 15% Presentation + 5% Feasibility.

Mapping from the 12 raw dimensions to the 7 weighted terms (stated so the math is auditable): Impact ← Imp · Creativity ← Nov · Technical ← Tech (AI value informs it qualitatively) · Bright Data ← mean(BDI, Stu) · Self-healing ← Heal · Presentation ← mean(Demo, UI, Mem) · Feasibility ← Feas. Comm is reported but unweighted (judges don't score revenue).

Per-concept rationale (drivers of each score):

1. **Driftwatch 9.08.** Only concept where every weighted term is ≥8: universal developer pain priced in dollars (Imp 9); "web pages as versioned dependencies with semantic contracts" is a reframe, not a feature (Nov 8.5); state-machine pipeline + verification gates + impact graph is real engineering (Tech 9); the entire Studio lifecycle — create, run with version pinning, heal with auto-composed prompts, the approval gate driven programmatically, discover for relocation — is load-bearing (BDI/Stu 9.5); healing is autonomous, *verified, and audited* with rollback, beyond anyone's heal-button (Heal 9.5); demo has a live self-repair *and* a semantic catch *and* a dollar figure (Demo 9.5, Mem 9); feasibility is the only sub-9 area because the heal-orchestration spike must land in Day 0–1 (Feas 8).
2. **Datalock 8.53.** Maximum marks where Bright Data is concerned (9.5/9.5/9.5) and the smallest build; collapses on Presentation (6.8 blend) because abstract infrastructure cannot produce a 2-minute "someone's Tuesday" story, and on judging risk because "scraper health monitoring" appears verbatim in the organizers' suggested list — the elimination rules below apply. Its engine survives inside Driftwatch.
3. **TermShift 8.35.** Brutal, redesign-happy pricing pages make the best healing environment (Heal 9); geo-variant pricing is a Bright Data-exclusive trick (BDI 9); loses ground on developer-judge empathy (procurement pain, not their pain) and novelty (elevated, but adjacent to price tracking in a judge's first 10 seconds).
4. **RegRadar 8.30.** Best impact of all twelve (9.5) and a serious healing story; drops on Feasibility 6.5 (hostile PDFs, glacial servers, sparse natural drift during the week) and Presentation ~7.3 (worthy but dry for this panel).
5. **ShrinkRay 8.03.** The single most memorable demo beat ("the price didn't change; the chips did" — Mem 9.5) but the shallowest technical ceiling of the top half (Tech 7.5), consumer-cute impact (7), and a head-on collision with the organizers' price-intelligence category.
6. **TenderGraph 7.83.** Impact 9 and real commercial legs, destroyed by Feas 5.5 — the most hostile, most variable sources of any candidate, with CAPTCHA and registration-gating risks that could burn three of seven days.
7. **CivicScope 7.75.** Authentic healing showcase (municipal sites, Heal 9) but a diffuse-impact, dry-demo profile (Presentation 6.3) and heavy per-city source labor.
8. **StackSignal 7.63.** The AI-inference layer is its whole novelty (AI 8.5) and also its risk — unvalidatable strategy claims in front of judges; closest of all twelve to the organizers' "competitive intelligence monitoring."
9. **CiteGuard 7.58.** Beautiful mission, high novelty (8.5); but Studio centrality only 7–7.5 (notice pages are simple; the hard work is entity resolution), sparse in-week change, and niche judge empathy.
10. **MedShelf 7.58.** Highest humanitarian impact (9) but reads as a price tracker with a halo to a skimming judge; lowest technical-depth score of the viable set (6.5).
11. **LookaLens 7.53.** Great Bright Data *unblocking* story (cloaked sites, geo-variant serving) but self-healing — the event's defining axis — is peripheral (6): adversaries evade, they don't drift.
12. **DepPulse 7.40.** Killed by one honest question: "why not the GitHub API?" Studio centrality 6.5 is disqualifying for a hackathon whose fourth criterion is Studio centrality.

---

# 5 · ELIMINATION ROUND

Applying the rejection rules aggressively. Nine concepts eliminated (one by merger), three advance.

- **DepPulse — ELIMINATED (rule: Bright Data superficial).** Official APIs serve most of its data; Scraper Studio would be decorative. Criterion 4 ("central to the project") cannot be satisfied honestly. No pitch fix survives the "why scrape an API?" question.
- **LookaLens — ELIMINATED (rule: cannot demonstrate self-healing meaningfully).** Its adversaries evade rather than drift; the heal loop is peripheral to the product's actual hard problems (similarity fingerprinting, evidence standards). On a 15%-weighted self-healing criterion, it forfeits the event's center of gravity. Ethical/false-accusation hazards add judging risk.
- **CivicScope — ELIMINATED (rules: demo weakness + dataset difficulty).** Worthy, but per-city source labor and PDF-heavy agendas threaten the 7-day budget, and a developer judging panel won't *feel* zoning minutes in two minutes. Presentation 6.3 with equal-weight judging is fatal.
- **MedShelf — ELIMINATED (rules: reads as simple price tracker + organizer-category collision).** However unfair, a skimming judge pattern-matches it to "price tracking" (explicitly on the organizers' suggested list, and on our own reject list). The elevation (formulation/pack-size semantics) is real but too subtle to survive a 2-minute read. Impact alone doesn't outweigh four mediocre criteria.
- **CiteGuard — ELIMINATED (rules: difficult dataset + demo depends entirely on staging).** Retraction notices barely change during any given week, so every demo beat must be simulated; curated publisher sources are real acquisition work; Studio centrality is middling because notice pages are structurally simple. Keep as a future side project — it deserves to exist.
- **StackSignal — ELIMINATED (rules: LLM-wrapper novelty + competitor-tracker adjacency).** Strip the inference layer and it's a competitor tracker (organizer-listed category, our reject list); keep the inference layer and the novelty rests on claims we cannot validate in seven days, with hallucination risk live on stage.
- **TenderGraph — ELIMINATED (rules: difficult-to-obtain data + 7-day demonstrability).** Source hostility (per-ministry layouts, CAPTCHAs, registration-gated documents) makes it the likeliest candidate to consume the week fighting portals instead of building product. The strongest "revisit after the hackathon as a real company" idea of the batch.
- **ShrinkRay — ELIMINATED at the final cut (rules: organizer-category collision + shallow technical ceiling).** It out-demos everything except Driftwatch, and its semantic-drift beat is superb — but "price and inventory intelligence" is the first organizer-suggested category, the technical ceiling is the lowest of the top five, and impact reads consumer-cute. Its best asset (the unit-price semantic catch) is *inherited by Driftwatch* in generalized form. Honorable mention; would be our pick for a consumer-facing event.
- **Datalock — MERGED, not shipped standalone (rules: scraper-monitoring-dashboard pattern + abstract demo).** Second-highest score on paper, and everything in it is correct — as an *engine*. Standalone, it (a) collides verbatim with the organizers' "scraper health monitoring" category and our own reject rule, (b) forces a 2-minute abstract infra demo where judges must imagine a user, and (c) caps Impact at "helps people who already run scrapers." Inside Driftwatch, every Datalock capability (contracts, gates, trust scores, audit ledger) becomes visible product surface with a concrete story. This merger is the strategy: *ship the infrastructure judges' hearts want, wearing the product judges' brains can score.*

**Advancing: Driftwatch, TermShift, RegRadar.**

---

# 6 · TOP THREE FINALISTS

## Finalist 1 — Driftwatch (Dependency Drift Sentinel)

**WHY THIS COULD WIN.** It is the only candidate that maximizes all six equally-weighted criteria at once; its weakest criterion (feasibility-driven technical risk) is addressable in Day 0. The self-healing criterion is not satisfied but *starred*: autonomous detection → machine-composed heal prompts → contract-verified approval → rollback → audit, demonstrated live.
**WHY JUDGES WOULD REMEMBER IT.** Two images: the Living Web trembling when a dependency shifts, and the moment the pipeline catches a price whose *unit* changed while every selector still returned green. "The scraper worked perfectly and was completely wrong" is a sentence judges will repeat to each other.
**WHY BRIGHT DATA WOULD CARE.** It is a working demonstration of what their heal/approve API enables when the human is lifted out of the loop — effectively a reference architecture for "Scraper Studio in autonomous production." It uses create, run, versions, heal, approve/reject, discover, search, the CLI's JSON envelopes, and the free-tier budget model, all load-bearing. It makes their newest, least-known capability (heal's approval gate) the star.
**WHY USERS WOULD CARE.** Every engineering team depends on facts that live on third-party pages. Driftwatch converts "we found out from the invoice" into "we knew in 9 minutes, with the diff, the affected call sites, and the dollar figure."
**WHY TECHNICALLY IMPRESSIVE.** A typed extraction state machine (scheduled → scraped → validated → classified → healed → verified → published/quarantined), a five-class drift taxonomy, semantic contracts with invariants + LLM adjudication + golden tests, verified self-repair with rollback via version pinning, and a code-impact graph — none of which is a wrapper around anything.
**WHY THE DEMO WOULD BE COMPELLING.** It contains an on-screen autonomous repair with a verdict, a semantic near-miss no other team will even attempt, and ends on a dollar number in a Slack message. Every beat is show-don't-tell; §10 scripts it to the second.
**WHAT COMPETING TEAMS ARE LIKELY TO BUILD.** Price trackers, job/travel aggregators, docs-RAG chatbots, news-sentiment dashboards, and "monitoring dashboards that call heal on error." Most will treat heal as a button and demo happy paths.
**HOW WE DIFFERENTIATE.** We demo the *unhappy* paths as the product: breakage, ambiguity, semantic betrayal — each resolved autonomously and audited. Against docs-RAG entries: we produce *validated structured deltas with impact*, not chat. Against monitoring entries: our monitoring is invisible plumbing under a product with a user story and a dollar sign.

## Finalist 2 — TermShift (SaaS Pricing & Terms Drift)

**WHY IT COULD WIN.** The healing environment is the most authentic (pricing pages mutate weekly), Bright Data's geo capability yields a demo trick nobody else has (same page, three countries, three prices), and financial impact is legible to any judge.
**WHY REMEMBERED.** "Your vendor changed what a 'seat' means and your bill grew $3,840" — a semantic catch with a receipt.
**WHY BRIGHT DATA CARES.** Pricing pages are their canonical hard target (anti-bot, A/B tests, geo variants); a term-sheet engine shows Studio surviving the harshest page class.
**WHY USERS CARE.** SaaS spend is universal; renewal surprises are hated; nobody has live terms monitoring.
**WHY TECHNICAL.** Same engine as Driftwatch plus term normalization across heterogeneous page vocabularies and A/B-consensus sampling (multi-fetch voting to separate experiments from real change) — a subtle, impressive problem.
**WHY THE DEMO COMPELS.** Live geo-price comparison, then a staged unit-redefinition caught semantically, priced against seat count.
**WHAT COMPETITORS BUILD.** Straight price trackers — which is exactly the danger: a skimming judge may file TermShift next to them.
**DIFFERENTIATION.** Terms-and-meaning, not prices; procurement briefs, not charts. But this must be *argued*, whereas Driftwatch's difference is *visible* — the decisive gap between the two.

## Finalist 3 — RegRadar (Regulatory Change Intelligence)

**WHY IT COULD WIN.** If a judge weighs raw societal impact above all else, RegRadar is unbeatable in this field (9.5); the self-healing story on decrepit government sites is authentic; compliance is a real industry with real budgets.
**WHY REMEMBERED.** "The tariff table changed Tuesday; importers found out here first, in plain language."
**WHY BRIGHT DATA CARES.** Government pages are a showcase for resilience on the web's worst HTML, and RegRadar's clause-level diffs demonstrate Studio output feeding serious downstream analysis.
**WHY USERS CARE.** Fines and missed deadlines are existential for SMBs; existing alert services are enterprise-priced and human-lagged.
**WHY TECHNICAL.** Clause-level diffing of legalese, effective-date semantics, applicability classification — hard NLP with real stakes.
**WHY THE DEMO COMPELS.** A legalese diff collapsing into one plain sentence with a deadline — strong, but it requires narration, and (since regulators won't oblige during our week) every beat rides on staged changes.
**WHAT COMPETITORS BUILD.** Almost nobody — differentiation is easy; the risk is *resonance*, not overlap.
**DIFFERENTIATION VS. OUR OWN #1.** RegRadar beats Driftwatch on impact and loses on the other five criteria for this specific panel: developer judges feel API drift personally, RegRadar's sources are the most likely to burn build days, and its demo needs explanation where Driftwatch's needs only eyes.

---

# 7 · RECOMMENDED #1 CONCEPT — DRIFTWATCH

**Product:** Driftwatch — the dependency drift sentinel.
**Category:** Developer intelligence / reliability-powered change intelligence (deliberately none of the organizers' six suggested categories).
**Thesis (one breath):** The pages your stack depends on are unversioned contracts; Driftwatch watches them with self-healing Scraper Studio pipelines, validates every extraction against semantic contracts, classifies every change, repairs itself when sites shift, verifies its own repairs, and tells you what each real change means for your code and your bill.

**Launch verticals (hackathon scope):**
1. **AI-provider drift** — model pricing, rate limits, deprecation notices, model availability across 3–4 providers. Timeliest possible demo material; the judges' own daily pain; changes genuinely occur weekly in this vertical, so the week-long soak will harvest *real* catches.
2. **Vendor API docs drift** — one payments-grade provider's public API reference/changelog (parameters, required fields, deprecations), feeding the blast-radius demo against a sample codebase.

**The five-class drift taxonomy (the conceptual spine, one slide, judges get it instantly):**
- **Class 1 · Structural drift** — page shape changed, meaning intact → auto-heal, verify, approve; user sees a green "self-healed" pulse, nothing more.
- **Class 2 · Benign content drift** — copyedits, cosmetic wording → ledger only, no noise.
- **Class 3 · Material change** — the signal: a price, limit, parameter, or deprecation actually changed → alert + impact analysis.
- **Class 4 · Semantic drift** — extraction still "succeeds" while meaning shifts (unit flips, scope changes, tier redefinitions) → contract assertions + adjudicator catch what selectors cannot.
- **Class 5 · Availability drift** — page moved/removed/blocked → `discover`-powered relocation proposals with approval.

**Positioning line for judges:** *Most teams will detect Class 1. Driftwatch is a product about Classes 3, 4, and 5 — with Class 1 handled so well you never see it.*

---

# 8 · WHY DRIFTWATCH CAN WIN

1. **Criterion coverage without trade-offs.** Scored honestly against all six equal-weight criteria it has no hole: the impact story is universal and quantified; the creative reframe (pages as versioned dependencies) is original; the engineering is real; Studio is not just used but *completed*; reliability is the product; the demo is visual and visceral.
2. **It answers the hackathon's own question better than the hackathon asked it.** The brief says "build self-healing scrapers." Driftwatch's answer: "self-healing is necessary but insufficient — here is self-healing you can *trust*, because every repair is verified against a contract of meaning, and here is why that unlocks a product." Judges reward teams that see past the brief.
3. **The Bright Data alignment is structural, not performative.** The heal/approve API with its `awaiting_approval` gate and `preview_result` is *begging* for an orchestrator; we build exactly that. Their engineers on the panel will recognize their own roadmap.
4. **Judge empathy.** Every judge has been burned by silent upstream change. The demo's dollar figure lands on someone who has personally paid it.
5. **Anti-fragile demo plan.** Real soak-collected catches + a controlled mirror for the live break + pre-recorded fallback: the demo cannot be killed by a slow third party on demo day.
6. **Track leverage.** The same build honestly contests Suit-Up (the Living Web + seismograph interface, §12) and Spider-Sense (typed state-machine architecture with golden tests, §9), while the merged Datalock engine anchors "Best Use of Bright Data." One build, four prize surfaces.

---

# 9 · COMPLETE PRODUCT ARCHITECTURE

Principle: **two deployables, one database, zero microservices.** Everything below is buildable by a 1–4 person team in seven days.

## 9.1 System overview

- **Frontend:** Next.js (TypeScript, App Router) + Tailwind + shadcn/ui; SVG/canvas for the Living Web and seismograph visualizations; server-sent events or polling for live pipeline states (no websocket infra).
- **Backend:** one Python service (FastAPI, Python 3.12, Pydantic v2) hosting the REST API, the scheduler (APScheduler in-process — a deliberate, documented simplicity choice), and the pipeline state machine. No queue system: a jobs table in Postgres provides durability, retries, and observability, and doubles as product UI data.
- **Database:** Postgres (hosted, e.g. Supabase free tier). JSONB for snapshots/extractions; append-only tables for ledger and audit events.
- **Bright Data integration layer:** a single typed client module wrapping Scraper Studio create / run (with `--version` pinning) / heal / approve-reject, plus discover and search — invoked via the official CLI's JSON envelopes and/or the underlying REST endpoints, with the 3-concurrent-AI-Flow cap respected by an internal semaphore, retry/backoff on 429s, and every request/response persisted to the audit ledger. MCP registration (`add mcp`) kept as an optional demo garnish, not a dependency.
- **LLM layer:** Anthropic Claude with four narrowly-scoped, JSON-schema-validated functions: (1) contract drafting from first snapshot, (2) drift classification into the five-class taxonomy, (3) heal-prompt composition (≤1,000 chars, includes failing fields + last-known-good examples), (4) semantic adjudication and migration-note/cost-delta generation. Temperature 0, cached by content hash, golden-tested.
- **Alerting:** in-app alert center + one outbound Slack webhook (demo-visible).
- **Auth:** none for the hackathon (single-tenant demo instance) — stated explicitly in the README as a scoping decision, which reads as maturity, not omission.
- **Deployment:** Vercel (frontend) + Railway/Fly.io (backend+scheduler) + Supabase (Postgres). One-command local run via docker-compose for judges.
- **Observability:** structured JSON logs (request IDs, pipeline-run IDs); the run ledger itself surfaced in the UI (observability *is* product surface); Bright Data credit spend surfaced via the CLI's budget capability on the Heal Center screen.
- **Testing:** golden-fixture tests for every validation gate and LLM function (recorded snapshots in-repo); state-machine transition tests; one end-to-end "mirror site" test that breaks a page and asserts the full detect→heal→verify→approve path.

## 9.2 The extraction pipeline as a state machine

Every scheduled run moves through explicit, persisted states:

SCHEDULED → SCRAPING → VALIDATING → (ok) PUBLISHED → DIFFING → CLASSIFYING → (Class 3/4) IMPACT → ALERTING
  · VALIDATING → (contract failure) DIAGNOSING → HEALING → VERIFYING → (pass) APPROVING → RE-RUNNING → PUBLISHED
  · VERIFYING → (fail) REJECTING → RETRY (≤2, prompt refined) → (still failing) QUARANTINED + REVIEW_QUEUE
  · SCRAPING → (fetch dead / 404 / relocated) RELOCATING (discover) → REVIEW_QUEUE

Every transition writes an audit event. QUARANTINED snapshots are never served to analytics or alerts — downstream consumers only ever see contract-passing data. This one property ("the dashboard cannot lie") is the reliability thesis in a sentence.

## 9.3 Reliability architecture — self-healing that is more than a button

Mapping every required capability to a concrete mechanism:

- **Schema validation:** every extraction validated against the source's versioned contract (required fields, types, nullability) the moment it lands.
- **Missing-field detection:** field-level presence/coverage tracking across runs; a field that was 100%-present for a week and is suddenly null is a structural-drift tripwire even when the run "succeeds."
- **Extraction confidence:** per-run score composed of schema pass rate, field coverage vs. trailing baseline, value-plausibility checks, and (when invoked) adjudicator confidence; displayed everywhere data is displayed.
- **Structural drift detection:** run failure, schema failure, or coverage collapse → Class 1 diagnosis with the exact failing fields identified.
- **Semantic drift detection:** contract assertions per field (unit, currency, period, scope, tier — e.g. "USD per 1M input tokens, Pro tier, monthly billing") checked by invariants plus LLM adjudication of old-vs-new values *with surrounding page context*; catches unit flips and definition changes that selectors cannot see.
- **Data-quality validation:** type/range/enum invariants (a rate limit is a positive integer; a price is a plausible currency amount; an endpoint count doesn't drop 80% in a day).
- **Duplicate detection:** content-hash short-circuit (unchanged page → Class 0, one ledger line, no LLM spend).
- **Anomaly detection:** z-scores on numeric fields vs. trailing history; cardinality-shift alarms on list fields (models[], endpoints[], plans[]).
- **Scraper repair:** auto-composed heal prompt (failing fields + expected shapes + last-known-good examples + page-change hints) → `scraper heal`.
- **Repair verification:** the `preview_result` from the approval gate is replayed against the *full* contract (schema + invariants + continuity vs. last-known-good) before any approval; a heal that "works" but returns implausible values is rejected.
- **Rollback:** scraper versions pinned per run; on failed verification the pipeline rejects the fix, continues on the last approved version, and quarantines the interval; the ledger shows exactly which version produced every snapshot.
- **Human approval where confidence is low:** three-band policy — high confidence auto-approves, low confidence auto-rejects and retries with a refined prompt, the gray band lands in the in-app Review Queue with a side-by-side (old extraction / new preview / page diff) and one-click approve/reject that drives the same Bright Data approval API.
- **Audit history:** append-only ledger of every run, validation verdict, diagnosis, heal prompt, preview verdict, approval decision (and by whom — machine or human), version change, and alert. The judge-facing answer to *"did the scraper recover the correct information?"* is: **a healed scraper's output is never trusted; it is re-proven against the contract of meaning, and the proof is on the audit screen.**

## 9.4 Competitive moat — value Bright Data does not provide

1. **The Semantic Contract Engine** — machine-checkable *meaning* (units, scopes, tiers, periods) layered on Studio's structural schemas; the difference between "extraction succeeded" and "the fact is still true."
2. **The five-class drift taxonomy + autonomous heal orchestration** — Bright Data provides heal-on-request with a human writing the prompt and reviewing the preview; Driftwatch supplies the noticing, the diagnosis, the prompt, the verification, the approval policy, the rollback, and the audit.
3. **The Change Ledger** — longitudinal, validated, versioned history of each dependency with entity resolution across redesigns (the "gpt-5-mini" row survives three page redesigns as one entity). Bright Data sells extraction; the ledger is memory.
4. **The Impact Graph** — mapping confirmed changes onto the user's codebase (call sites, files) and bill (usage × price delta), turning "the page changed" into "here is your exposure."
5. **Decision-grade alerting** — alerts carry the diff, the class, the confidence, the affected code, the dollar figure, and the suggested migration note; zero-noise policy (Classes 0–2 never alert).

## 9.5 Core data model

sources (id, name, vertical, url, schedule, status) · contracts (id, source_id, version, json_schema, invariants[], semantic_assertions[], created_from) · scrapers (id, source_id, collector_id, active_version, status) · runs (id, source_id, scraper_version, state, timings, credits_spent, confidence) · snapshots (id, run_id, content_hash, payload_jsonb, contract_verdict, quarantined) · drift_events (id, source_id, class 1–5, severity, confidence, before_ref, after_ref, field_paths[], summary) · heal_events (id, source_id, trigger_event, composed_prompt, preview_payload, verification_verdict, decision auto/human, decided_by, version_before/after) · impact_reports (id, drift_event_id, repo_ref, affected_files[], call_sites[], cost_delta_monthly, migration_note) · alerts (id, drift_event_id, channel, payload, delivered_at) · audit_events (append-only: actor, action, refs, payload, ts).

## 9.6 Spider-Sense plan — repository and code quality

- **Monorepo:** apps/web (Next.js UI) · apps/engine (FastAPI service: api/, scheduler/, pipeline/ with one module per state, contracts/, drift/, healing/, impact/, brightdata/ client, llm/ functions) · packages/shared (JSON schemas + TS types generated from Pydantic models — one source of truth) · fixtures/ (golden snapshots, recorded Bright Data envelopes, sample repo for impact analysis) · mirror/ (the controlled demo site + its "redesign" variants) · docs/ (architecture diagram, Scraper Studio usage writeup with collector IDs and heal transcripts, demo script).
- **Interfaces & boundaries:** the Bright Data client, LLM functions, contract engine, and pipeline are separate modules with typed interfaces; the pipeline depends on abstractions, so every stage is testable with fixtures and the whole system runs offline in "replay mode" (also the demo-day safety net).
- **Error handling:** typed error taxonomy (FetchError, ContractViolation, HealRejected, BudgetExceeded…) mapped to pipeline states — no bare exceptions crossing module boundaries; every failure path lands in a visible state, never a silent log line.
- **Typing:** strict mypy + Pydantic v2 on the engine; strict TypeScript on the web app; generated types shared.
- **Configuration:** single typed settings module from environment; .env.example committed; zero secrets in repo.
- **Testing strategy:** unit tests on gates/invariants/state transitions; golden tests on all four LLM functions (recorded inputs → expected structured outputs); one E2E mirror-break test; CI runs lint + typecheck + tests on every push.
- **Documentation:** README (see §14 structure), ARCHITECTURE.md with the state-machine diagram, SCRAPER_STUDIO.md with the full lifecycle evidence, DEMO.md with the reproducible 10-minute judge walkthrough.
- **Sample data & reproducibility:** committed sample outputs (JSON) per source; seed script loading a week of ledger history so judges see a living product instantly; one-command demo bootstrap.
- **AI-tool disclosure:** a candid AI_USAGE.md (which agents, for what, how verified) — required by the rules and a trust signal for Spider-Sense.

---

# 10 · THE KILLER DEMO — 2:00, SCRIPTED TO THE SECOND

Format: one continuous screen recording, narrated; no slides after the first frame. The live break runs against our controlled mirror of a real pricing page — *announced honestly on screen* ("simulated overnight redesign — same pipeline, real Bright Data heal"), which reads as engineering rigor, not sleight of hand. Real soak-collected catches close the demo so judges see the system worked in the wild, unstaged.

- **0:00–0:10 · Hook (Beat: intent).** Black screen, one line: *"Everything your product depends on is written on pages that can change tonight."* Cut to the Living Web — a radial map of a stack's page-dependencies, all strands calm.
- **0:10–0:35 · Onboard live (Beats: create scraper, run, structured data).** Narrator types a URL + one sentence: "Watch this provider's pricing page — models, price per 1M tokens, rate limits." On screen: Scraper Studio AI Flow generating (progress states visible), a `collector_id` appearing, first run, and a **structured, contract-stamped snapshot** materializing as a new strand on the Web. Caption: "Scraper Studio wrote the scraper. Driftwatch wrote the contract."
- **0:35–0:50 · The overnight break (Beats: site changes, extraction breaks, failure detected).** Time-lapse dial to "overnight." The mirror redesigns (table → cards). The strand's seismograph spikes red: *Class 1 — structural drift. `price_per_1m` null, field coverage 41%.* Snapshot auto-quarantined — the dashboard visibly refuses to update rather than showing wrong data.
- **0:50–1:10 · Autonomous repair (Beats: self-healing triggered, extraction repaired, data validated).** The Heal Center shows, in sequence, with no human input: the machine-composed heal prompt (visible on screen, referencing the exact failing fields) → Bright Data heal running → `preview_result` returned → verification gates ticking green one by one (schema ✓ invariants ✓ continuity ✓ adjudicator ✓ confidence 0.96) → **auto-approved**, version v3→v4, re-run, strand returns to green. Elapsed on a visible stopwatch: ~40 seconds. Caption: *"No human noticed. None needed to."*
- **1:10–1:30 · The catch selectors can't make (Beats: meaning changes, semantic correctness checked).** Second event fires on a *different* source: every field extracted, schema green — but the contract flags **Class 4 — semantic drift**: *"price unchanged at $2.50 — unit changed from 'per 1M input tokens' to 'per 1M tokens (input+output)'."* Side-by-side page context highlighted. Caption: *"The scraper succeeded. The truth changed. Only a contract catches that."*
- **1:30–1:50 · From change to consequence (Beats: repaired data powers the product, actionable insight).** The drift event opens its Impact Graph: sample repo scanned → 3 files, 7 call sites on the affected model → usage profile applied → **"≈ +$412/month from September 1"** → generated migration note → a Slack alert lands on screen carrying diff, class, confidence, and the dollar figure.
- **1:50–2:00 · Proof it's real, then the line.** Rapid montage: the week's Change Ledger with *N real drift events caught in the wild* (dated, sourced, one highlighted genuine catch), heal MTTR and verification pass-rate stats, credits spent. Final card: *"The web changed overnight. Driftwatch noticed, healed its own pipeline, proved the fix, and priced the impact — before your first coffee."*

All thirteen required beats are present: intent (0:10) · scraper created (0:15) · Studio runs it (0:25) · structured data (0:30) · site changes (0:38) · extraction breaks (0:42) · failure detected (0:45) · self-healing triggered (0:52) · repaired (1:00) · validated (1:05) · semantic check (1:10–1:30) · powers product feature (1:30) · actionable insight (1:42).

---

# 11 · 7-DAY BUILD STRATEGY (with real dates)

**Pre-kickoff window — Aug 9–16 ("Day 0").** Allowed: planning, design, accounts, learning the tools. (Verify in the WeMakeDevs Discord whether project *code* must start at kickoff; the plan below assumes yes and keeps Day 0 code-free except throwaway spikes on toy pages.)
- Create Bright Data account(s); confirm the 5,000-credit budget; run the CLI end-to-end on a *toy page*: create → run → deliberately break the toy page → heal → inspect `preview_result` → approve — this spike is the single highest-value hour of preparation and de-risks the whole concept.
- Finalize the source shortlist (4–6 pages across the two verticals) and draft each contract's semantic assertions on paper.
- Design: moodboard, palette, the Living Web and seismograph sketches, screen wireframes.
- Write the repo conventions doc, the state-machine diagram, this scope contract (Must/Won't), and the demo script skeleton. Prepare the mirror-site plan (snapshot of a real pricing page + one "redesigned" variant + one "semantic-drift" variant).
- Team roles (if >1): Engine owner · UI owner · Data/contracts owner · Demo/docs owner (roles combine downward for smaller teams).

**Day 1 — Mon Aug 17 · Skeleton + first blood.** Repo scaffold, CI, DB schema migrated, typed Bright Data client with recorded envelopes, and the happy path end-to-end for ONE source: NL create in Studio → run → snapshot stored → shown raw in a bare UI. Milestone: structured data flows through our pipes.
**Day 2 — Tue Aug 18 · Contracts + scheduler + start the soak.** Contract engine v1 (schema + invariants + verdicts), scheduler with jobs table, content-hash short-circuit, ledger writes. Onboard all 4–6 real sources and **begin continuous monitoring — every real drift caught between now and Sunday is demo ammunition.** Milestone: the soak is live.
**Day 3 — Wed Aug 19 · The heal loop.** Diagnosis (failing-field identification), heal-prompt composer, heal → preview verification against contract → approve/reject policy with the three confidence bands, version pinning + rollback, quarantine, Review Queue API. E2E mirror-break test passing. Milestone: **the machine repairs itself and proves it** — the hackathon is effectively won or lost today.
**Day 4 — Thu Aug 20 · Meaning + consequence.** Semantic assertions + adjudicator + continuity/anomaly checks (Class 4 detection); drift classifier across all five classes; Impact Graph on the committed sample repo (static scan for model IDs/endpoints → call sites; usage profile → cost delta); migration-note generation; Slack alerts. Milestone: the semantic catch and the dollar figure both work.
**Day 5 — Fri Aug 21 · The product face.** Full UI build: Living Web, seismographs, drift-event view with before/after diff, Heal Center with live gate animation, Review Queue, Ledger; SSE-driven live states; the heal-replay scrubber; empty/loading/error states. Mirror variants wired to a rehearsal switch. Milestone: it looks finished (Suit-Up bar).
**Day 6 — Sat Aug 22 · Harden + narrate.** Golden tests green; seed script + replay mode; README/ARCHITECTURE/SCRAPER_STUDIO/AI_USAGE docs with heal transcripts and collector IDs; harvest and curate the soak's real catches; record demo dry-runs ×3; fix what the recordings expose. Milestone: submission-ready a day early.
**Day 7 — Sun Aug 23 · Ship.** Fresh soak stats into the ledger, final 2-minute video recorded in the morning (backup take kept), sample outputs committed, repo cleaned, submission form completed hours before the deadline. Buffer, not building.

**Priority order if time collapses (minimum winning product first):** heal loop with verification (Day 3) > semantic catch (Day 4 morning) > core UI (Day 5) > Impact Graph > ledger polish > Slack > replay scrubber > MCP garnish. The first three alone still beat the field.

---

# 12 · UI PLAN — SUIT-UP TRACK

**Design language:** dark, calm, observatory-grade — deep neutral background, high-contrast typography (Inter/Geist), one restrained accent per drift class (Class 1 amber · 3 red · 4 violet · 5 slate; green reserved exclusively for "verified"), generous whitespace, zero chart-junk; motion used only to encode state change. It should feel like mission control for the web you depend on, not a hackathon dashboard.

**Navigation (left rail, 6 items):** Web · Sources · Events · Heal Center · Impact · Ledger (+ Settings).

- **The Living Web (home / signature screen):** your dependencies as a radial web — each strand a monitored page, node size = dependency weight, strand pulse = last activity. Calm = truth holding. When drift lands, a ripple travels the strand and the affected node glows in its class color; healed strands re-knit with a brief green shimmer. This is the screen judges remember.
- **Source Seismograph (source detail):** horizontal timeline per source — flat baseline with event pulses; hovering scrubs history; annotations for version changes (v3→v4) and heal events; confidence band drawn under the baseline.
- **Drift Event view:** split-pane before/after — left: rendered page regions highlighted; right: structured diff at field level with class badge, severity, confidence dial, and the contract clause that fired; one-line plain-language summary on top.
- **Heal Center:** live pipeline states as a vertical gate sequence (detect → diagnose → heal → verify → approve), each gate animating pass/fail in real time; the machine-composed heal prompt shown verbatim; Bright Data credits widget; heal MTTR and verification pass-rate stats; the **Review Queue** for gray-band cases with side-by-side approve/reject.
- **Impact view:** repo panel (files/call-sites highlighted) → usage profile → cost-delta counter that counts up to its figure; generated migration note with copy button.
- **Ledger:** the audit trail as a first-class screen — filterable by source/class/actor (machine vs. human), every entry expandable to raw evidence (snapshots, prompts, previews, verdicts).
- **Alerts/Settings:** thresholds per class, Slack webhook, schedule controls.
- **Confidence indicators everywhere:** every number in the product carries its verification state (verified green tick · quarantined slate hatch) — the "this dashboard cannot lie" property made visible.

**Signature interaction (the one judges will remember): the Heal Replay scrubber.** On any healed event, a scrubber replays the entire incident as motion — page breaks, strand ripples red, prompt composes itself character-by-character, gates flip green, version ticks, strand re-knits — in 8 seconds, loopable. It compresses the whole product thesis into one replayable gesture and gives the demo video its money shot.

---

# 13 · TECHNICAL RISKS (and mitigations)

1. **Heal quality/latency is unknown until tried** — the concept's load-bearing wall. Mitigation: Day-0 toy-page spike; mirror-based rehearsal; `--auto-approve` never used raw (verification gates always between heal and approve); pre-healed scraper versions staged as demo fallback; recorded envelopes for replay mode.
2. **AI Flow concurrency cap (3 jobs) + 429s.** Internal semaphore + backoff; scraper creation is an onboarding-time event, not a hot path.
3. **Credit budget (5,000/mo, 1/page-load).** Soak math: 6 sources × hourly × 6 days ≈ 864 loads + dev/testing overhead ≈ comfortably within budget; content-hash short-circuit avoids LLM spend, hourly cadence avoids credit spend; budget widget keeps it visible (and demos nicely).
4. **LLM misclassification (false drift / missed drift).** Golden test set per class built Day 3–4; conservative thresholds (uncertain → Review Queue, never silent); adjudicator sees page context, not just values; humans remain the gray-band backstop — which is product, not weakness.
5. **Demo-day dependency on live third parties.** Mirror site for the break; replay mode for total-outage; the final video recorded Day 7 morning with a backup take; nothing in the 2 minutes requires a slow external site to cooperate live.
6. **Source pages fight back (blocking, geo-variance, A/B noise).** That's the Bright Data sales pitch working in our favor; multi-sample consensus for A/B noise; source shortlist pre-validated on Day 0 with two spares.
7. **Scope creep** — the classic killer. The Won't-build list (§2, Idea 1, W) is a signed contract; Day-6 submission-ready target creates a full buffer day.

---

# 14 · JUDGING STRATEGY

**Map every criterion to evidence a judge can verify in minutes:**
- *Impact* → the dollar-figure alert + one-paragraph problem statement with named, universal user; real soak catches prove it's not hypothetical.
- *Creativity* → "pages as versioned dependencies with semantic contracts" + the five-class taxonomy slide; explicitly contrast with the organizers' suggested categories to show we went past the brief.
- *Technical excellence* → ARCHITECTURE.md state-machine diagram, typed modules, golden tests, CI badge — visible within 60 seconds of opening the repo.
- *Use of Scraper Studio* → SCRAPER_STUDIO.md with the complete lifecycle evidence: collector IDs, creation transcripts, heal prompts, preview verdicts, approval decisions, version history, view-URL screenshots. No judge should have to *hunt* for Studio centrality.
- *Reliability & self-healing* → the Ledger screen + the E2E mirror-break test + the three-band approval policy + rollback; the sentence to land: "healed output is never trusted, it is re-proven."
- *Presentation* → the 2-minute script (§10), the 10-minute reproducible judge walkthrough (DEMO.md), the Heal Replay gif at the top of the README.

**Anticipated rival archetypes and our contrast line:** price/deal trackers ("they show numbers; we prove numbers"), docs-RAG chatbots ("they answer questions about pages; we guarantee facts from pages"), monitoring dashboards ("they watch scrapers; we watch the *world* and the scraper-watching is invisible"), news/sentiment aggregators ("they summarize; we detect, verify, and price change").

**Submission checklist:** public repo · README with hero gif + problem + architecture + Studio section · example structured outputs committed · 2-minute video · AI_USAGE.md disclosure · Discord/form submission hours early · every rule (public data only, Studio-originated scrapers) explicitly evidenced.

---

# 15 · FINAL PRODUCT PITCH

- **Name:** **Driftwatch** *(alternates if desired: Vigil, Strand, Seismo)*
- **Tagline:** *The web your stack depends on has no changelog. Now it does.*
- **One-sentence pitch:** Driftwatch turns the public pages your product silently depends on — model pricing, API docs, rate limits, vendor terms — into versioned, validated data contracts that repair themselves when sites change and tell you what every real change costs you.
- **30-second pitch:** "Your stack depends on facts that live on other people's web pages: what a model costs, what a parameter requires, what a rate limit allows. Those pages change without warning, and you find out from an outage or an invoice. Driftwatch watches those pages with self-healing Scraper Studio pipelines, validates every extraction against a contract of *meaning*, and when something really changes, tells you in minutes — with the diff, the affected code, and the dollar figure. When the page breaks our scraper instead, Driftwatch notices, writes its own repair prompt, verifies Bright Data's fix, and approves it — no human required, every step audited."
- **60-second pitch:** the 30-second pitch, plus: "Under the hood is a five-class drift taxonomy. Structural drift — the page moved its furniture — is healed autonomously and verified before approval, with rollback if the proof fails. Semantic drift is the dangerous one: the scraper still returns green while the *meaning* shifts — a price that stayed $2.50 but switched from per-million-input-tokens to input-plus-output. Selectors can't see that; our semantic contracts do. Every event lands in an append-only change ledger, and our Impact Graph maps it onto your actual codebase and usage: three files, seven call sites, $412 a month. We built this on the full Scraper Studio lifecycle — create, run, heal, approve — closing the loop Bright Data's API deliberately leaves open for a human. Driftwatch is that human, formalized, verified, and audited."
- **README opening:** *"At 2:07 a.m., a provider quietly edited one line on a pricing page. No announcement, no email, no API version bump. Every scraper watching it kept returning green. Every one of them was now wrong. Driftwatch exists for that moment."*
- **Demo opening line:** *"Everything your product depends on is written on pages that can change tonight. Watch what happens when one does."*
- **Final demo line:** *"The web changed overnight. Driftwatch noticed, healed its own pipeline, proved the fix, and priced the impact — before your first coffee."*

---

## Appendix A · Rule-compliance checklist (as designed)

Public data only (docs/pricing/public references; no logins, no paywalls) ✓ · Scrapers originate in Scraper Studio, custom-created per source (library scrapers alone insufficient — not used as the core) ✓ · Studio central to the project (criterion 4) ✓ · Public repo, README, example structured output, demo video, Studio-usage explanation ✓ · AI-tool usage disclosed and understood ✓ · Team 1–4 ✓ · Verify pre-kickoff code policy in Discord before writing any product code before Aug 17.

## Appendix B · Key facts this strategy relies on (verified Aug 9, 2026)

Hackathon: Aug 17–23, 2026; six equal judging criteria; prizes as listed in §Research. Bright Data CLI: `scraper create <url> <description>` (AI Flow, 3 concurrent, `collector_id`, `view_url`) · `scraper run` (sync/async/batch, `--version`) · `scraper heal <id> "<prompt≤1000>"` → `awaiting_approval` gate with `preview_result` + `diff_summary` · `scraper approve [--reject]` · `discover --intent` · `search` · `pipelines` (40+ types) · `browser` (session automation) · `skill`, `add mcp` (Claude Code/Cursor/Codex) · free tier 5,000 credits/month, 1 credit/page load, renews on the 1st, no rollover.

---

*End of strategy. Awaiting concept approval before any implementation prompt, code, or repository work begins.*



