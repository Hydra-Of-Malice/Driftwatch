# LinkedIn post — final, ready to paste (2026-08-22)

Finalized from `linkedin-post.md`'s Option A (recommended there: honest, doesn't name the Bright Data outage publicly while tagging them as sponsor — your call to change if you'd rather run Option B or C from that file). Only change from the draft: day count updated for today.

---

## Image to attach

**`driftwatch_ui_semantic_event.png`** (repo root). This is the strongest single frame you have: schema ✓, invariants ✓, **semantics ✕** — same $2.50 price, meaning silently redefined, `+$626/mo` blast radius, 9 call sites. It's the one screenshot that makes the whole pitch legible without reading a word of the post.

**Do not use `driftwatch_ui_livingweb.png` or `driftwatch_ui_healcenter.png` as-is** — both display "42.3s heal MTTR" as a headline stat tile, which is a seeded/fabricated value (fixed in the code today, but the screenshots predate the fix and still show it). If you want either of those views for a future post, re-take them against the current build — a fresh capture now shows the real measured behavior instead.

---

## The post

Spent this week building for the Into the Scrape-Verse Hackathon (Aug 17–23), run by WeMakeDevs with Bright Data.

The thing I keep coming back to is how quietly scrapers fail. A site renames one class, the extraction returns nothing, and the pipeline keeps running as though everything is fine. You usually find out days later, from data that was never there.

I'm building DriftWatch. It turns the public pages your product quietly depends on — model pricing, API docs, rate limits, vendor terms — into versioned data contracts that repair themselves when the page changes, and then tell you what the change means for your code and your bill.

But the failure I ended up designing around is worse than a broken selector: extraction that succeeds and is still wrong. A provider holds the headline price at $2.50 and changes the unit underneath it from per-1M-input-tokens to input and output combined. Every scraper returns green. Every number downstream is now wrong. Nothing about the page structure broke, so no selector can catch it. Only a contract that pins meaning can.

So nothing reaches analytics until it clears four gates — shape, invariants, unit anchors, and continuity against history. Fail one and the snapshot is quarantined instead of served. The dashboard cannot lie.

What changed my thinking was Bright Data's Scraper Studio heal loop. You describe the field you want in plain language once, and when the structure shifts the extraction gets rebuilt from that description rather than from a selector you go and rewrite by hand. But the loop has a human at both ends — someone has to notice the break, write the heal prompt, review the preview, approve it. DriftWatch is that human, formalized: it detects the drift, composes the heal prompt from its own diagnosis, then re-proves the healed output against the full contract before it calls approve. A heal that reports success is never trusted. It passes the same gates as everything else, or it gets rejected and the pipeline stays pinned to the last good version.

I built the whole loop against recorded envelopes and a controlled mirror site — baseline, overnight redesign, silent unit flip, real price change, 404 — so the break-and-heal path is reproducible in tests and on stage instead of depending on a live page misbehaving on cue. 23 tests walk all five drift classes end to end. The live client sits behind one env var.

The other detail worth mentioning is that the whole workflow stays in the terminal, inside Claude Code. No dashboard, no proxy rotation, no retry logic to maintain.

That combination matters more than it first sounds. Reliable data pipelines usually fail at the maintenance layer, not the build layer, and this moves the maintenance somewhere it can be automated.

One day left before submissions close.

Repo: https://github.com/Hydra-Of-Malice/Driftwatch

#WebScraping #AI #Automation #DataEngineering #BrightData #ScraperStudio #SelfHealing #Hackathon #GenAI #WeMakeDevs

---

## Tags & mentions — for reach, not automatic from this file

LinkedIn only creates a real, clickable @mention when you type `@` in the composer itself and pick the entity from its own dropdown — pasting a name as plain text (even `@Bright Data`) does **not** tag anyone or notify them. Do this manually after pasting the post:

| Priority | Who | Why |
|---|---|---|
| **High** | **Bright Data** (company page) | You're using their product as the core of the submission and tagging them as sponsor — tagged posts about their product are the ones most likely to get reshared by their account, which is the single biggest reach lever available here |
| **High** | **WeMakeDevs** (organizer) | Hackathon organizers routinely reshare/engage with tagged submission posts during the event window — you're posting during the window (closes tomorrow) |
| **Optional** | Any specific judge or organizer contact you've actually spoken with | Only tag people you have a real interaction with — tagging strangers reads as spam and can hurt rather than help |
| **Optional** | **Anthropic** / **Claude Code**, if their pages support it | You disclose Claude Code usage in the post body already (required by the hackathon's AI-disclosure rule); an actual tag adds a second discovery path if the page exists and allows it |

**On hashtag count:** the 10 tags above are already in the post. LinkedIn's own guidance and most practitioner data point to **3–5 highly relevant tags outperforming 10+** for algorithmic reach — a wall of tags can read as keyword-stuffing. If you want to optimize rather than maximize, trim to: `#BrightData #ScraperStudio #WeMakeDevs #AI #DataEngineering`. Full list is left in the post above so you can decide; either works, this is a judgment call, not a correctness issue.

**Post timing:** LinkedIn engagement is meaningfully higher Tuesday–Thursday, 8–10am in your audience's timezone, if you have any flexibility before the deadline.
