# DriftWatch — LinkedIn post (Into the Scrape-Verse, Aug 17–23 2026)

Draft written 2026-08-21, two days before submissions close.

---

## Read this before posting

Your draft has a placeholder: *"[What happened when I tested it: what broke, what came back after healing, how long it took.]"*

**I could not fill that in truthfully.** The only live Bright Data evidence in the repo is `driftwatch/scripts/spike_out/`, and all three envelopes are failures:

| File | `status` | `error` |
|---|---|---|
| `create.json` | `ai_trigger_failed` | `Automation not allowed` |
| `heal.json` | `heal_trigger_failed` | **`Self healing tool is temporarily disabled`** |
| `approve.json` | `resume_failed` | `Automation not found` |

`completed_steps` is `[]` in all three. `run1.json` and `run2.json` were never written — the spike died at step 3 of 5. There is no `driftwatch.db`, no logs, and the "live evidence to capture" checklist at `docs/SCRAPER_STUDIO.md:55-59` is still three unchecked boxes.

So a sentence like *"the heal came back in 42 seconds"* would be inventing a result. Two figures in particular are **not measurements**:

- **42s MTTR** → `seed.py:145`, hardcoded `"mttr_seconds": 42.3`, sitting next to `"seeded": True`
- **+$626/month** → a fixture value from the mirror world, not a real finding

I also **cut** this line from your draft: *"the Collector ID it returns is already a live endpoint, so there is no deployment step at all."* Your spike did return a collector ID (`c_msqexhu61uaxbv00x4`), but with `ai_trigger_failed` and no completed steps it is not a working endpoint. That claim is contradicted by your own evidence.

**If you have since gotten a live heal to run, send me the envelopes and I'll swap the real numbers in.** Otherwise use Option A below, which is honest and — I'd argue — a better story anyway.

---

## The post (ready to paste)

Spent this week building for the Into the Scrape-Verse Hackathon (Aug 17–23), run by WeMakeDevs with Bright Data.

The thing I keep coming back to is how quietly scrapers fail. A site renames one class, the extraction returns nothing, and the pipeline keeps running as though everything is fine. You usually find out days later, from data that was never there.

I'm building DriftWatch. It turns the public pages your product quietly depends on — model pricing, API docs, rate limits, vendor terms — into versioned data contracts that repair themselves when the page changes, and then tell you what the change means for your code and your bill.

But the failure I ended up designing around is worse than a broken selector: extraction that succeeds and is still wrong. A provider holds the headline price at $2.50 and changes the unit underneath it from per-1M-input-tokens to input and output combined. Every scraper returns green. Every number downstream is now wrong. Nothing about the page structure broke, so no selector can catch it. Only a contract that pins meaning can.

So nothing reaches analytics until it clears four gates — shape, invariants, unit anchors, and continuity against history. Fail one and the snapshot is quarantined instead of served. The dashboard cannot lie.

What changed my thinking was Bright Data's Scraper Studio heal loop. You describe the field you want in plain language once, and when the structure shifts the extraction gets rebuilt from that description rather than from a selector you go and rewrite by hand. But the loop has a human at both ends — someone has to notice the break, write the heal prompt, review the preview, approve it. DriftWatch is that human, formalized: it detects the drift, composes the heal prompt from its own diagnosis, then re-proves the healed output against the full contract before it calls approve. A heal that reports success is never trusted. It passes the same gates as everything else, or it gets rejected and the pipeline stays pinned to the last good version.

I built the whole loop against recorded envelopes and a controlled mirror site — baseline, overnight redesign, silent unit flip, real price change, 404 — so the break-and-heal path is reproducible in tests and on stage instead of depending on a live page misbehaving on cue. 23 tests walk all five drift classes end to end. The live client sits behind one env var.

The other detail worth mentioning is that the whole workflow stays in the terminal, inside Claude Code. No dashboard, no proxy rotation, no retry logic to maintain.

That combination matters more than it first sounds. Reliable data pipelines usually fail at the maintenance layer, not the build layer, and this moves the maintenance somewhere it can be automated.

Two days left before submissions close.

Repo: https://github.com/Hydra-Of-Malice/Driftwatch

#WebScraping #AI #Automation #DataEngineering #BrightData #ScraperStudio #SelfHealing #Hackathon #GenAI #WeMakeDevs

---

## Options for the test paragraph

Paragraph 7 is the one that replaced your placeholder. Three ways to play it:

### Option A — reproducibility as a design choice (used above, recommended)

> I built the whole loop against recorded envelopes and a controlled mirror site — baseline, overnight redesign, silent unit flip, real price change, 404 — so the break-and-heal path is reproducible in tests and on stage instead of depending on a live page misbehaving on cue. 23 tests walk all five drift classes end to end. The live client sits behind one env var.

Fully accurate, doesn't name the outage, reads as rigor. Safe to post today.

### Option B — name the outage

> My day-0 spike against the live CLI came back `Self healing tool is temporarily disabled`, so I built the loop against recorded envelopes and a controlled mirror site instead — baseline, overnight redesign, silent unit flip, real price change, 404. Less glamorous, but it means the break-and-heal path is reproducible on demand rather than dependent on a good day. The live client sits behind one env var.

Also true, and engineers tend to respect it. **But you're tagging Bright Data and they're the sponsor** — a public "your tool was down" is a judgment call about the room, not about accuracy. Your call, not mine.

### Option C — if you land a real live heal before the 23rd

Replace paragraph 7 with the actual run: what you broke, what the preview returned, the real MTTR from `heal_events`. Send me `heal.json` and `approve.json` from a successful run and I'll write it. Strongest version if you can get it — but only if it actually happens.

---

## Smaller edits, and why

| Change | Reason |
|---|---|
| Named the project **DriftWatch**, added the one-line what-it-does | Fills your `[What I'm building]` placeholder |
| `[Claude Code / Cursor / Codex]` → **Claude Code** | Matches `docs/AI_USAGE.md`, and it's what you built in |
| `[Repo goes up with submission / link]` → **the live link** | Repo went public today at `76a7d15` |
| Added the Class-4 unit-flip paragraph | Most distinctive idea in the project; the draft buried it |
| Cut "Collector ID is already a live endpoint" | Contradicted by `create.json` — see warning above |
| Kept the `$2.50` unit-flip example | Illustrates the mechanism; not presented as a measured finding |

## Every factual claim, and where it comes from

- DriftWatch / contracts / repair themselves → `driftwatch/README.md`
- Four gates: shape, invariants, unit anchors, continuity → `README.md`, `contracts/`
- Five drift classes → `README.md` taxonomy table
- Verify-before-approve, reject → stay pinned → `README.md` reliability guarantees, `healing/verifier.py`
- 23 tests, all five classes E2E → `docs/AI_USAGE.md`
- Mirror variants baseline → redesign → semantic → material, plus 404 → `mirror/`, `docs/DEMO.md`
- Live client behind one env var (`DW_MODE=live`) → `docs/SCRAPER_STUDIO.md`
- Hackathon dates, WeMakeDevs × Bright Data → `README.md`
