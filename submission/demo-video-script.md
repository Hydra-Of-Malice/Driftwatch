# Demo video script — DriftWatch (Spider Mode)

**Video:** `submission/driftwatch-demo.mp4` — 1920×1080 · H.264 · 30 fps · **2:56** · 5.8 MB · **silent**

This is a *voiceover script keyed to a finished cut*. The video is already edited to length: every
shot lasts exactly as long as the line spoken over it. Drop the MP4 on your timeline at 00:00,
record the **Say** column against the timecodes below, and the two line up with no trimming.

Total narration: **444 words ≈ 2:56 at a natural 150 wpm.** That is a
relaxed pace — do not rush. The hard cap is 3:00, so you have ~4 seconds of headroom, no more.

---


## About the project

| Time | On screen | Say |
|---|---|---|
| **0:00** | `#/web` — The Living Web, calm | "Every product depends on facts that live on somebody else's web page. A model's price per token. A rate limit. An API parameter. And those pages change without telling you." |
| **0:11** | `#/web`, graph hovered | "This is DriftWatch. It watches those pages — and when one changes, it doesn't just tell you that something changed. It tells you whether it's safe to ignore, or whether it just broke your bill." |

## Tech stack and architecture

| Time | On screen | Say |
|---|---|---|
| **0:25** | `#/sources` | "Under the hood it's Flask and SQLite. Nothing exotic. Each source is one Scraper Studio scraper, one semantic contract, and one change ledger." |
| **0:34** | `#/sources/nimbusai-pricing` — seismograph, verified snapshot | "Every page is watched by a scraper built in Bright Data's Scraper Studio, and every extraction has to earn its way to the dashboard." |
| **0:44** | Semantic contract card — the four gates | "It has to pass a contract first. Does the shape match? Do the values make sense? Does the meaning still hold? Is the change plausible against history? Four gates — fail any one and the data gets quarantined instead of published." |
| **1:00** | Demo controls drawer opens | "And when a redesign breaks the scraper outright, DriftWatch diagnoses what broke, writes the repair prompt itself, and sends it to Scraper Studio's heal — then refuses to trust the result." |

## Demo

| Time | On screen | Say |
|---|---|---|
| **1:12** | NimbusAI → v2 redesign, Apply & run all | "Let me show you. I'm simulating a page redesign landing overnight." |
| **1:16** | `#/heal` — detect, diagnose, heal, verify, approve · 4/4 gates | "That page changed shape completely — the old scraper would have returned nothing. Instead: detect, diagnose, heal, verify, approve. All four gates re-run green against the repaired output." |
| **1:27** | Heal history — v2→v3, auto_approved by machine | "Template version bumped, auto-approved by machine, and nobody had to notice. That's the autonomous part." |
| **1:33** | NimbusAI → v3 semantic, Apply & run all | "Now the failure mode that motivated this whole project. I'm changing something on the page that no selector-based scraper would ever catch." |
| **1:42** | `#/events` — new Class 4 at top of feed | "It comes back as a Class 4. Semantic drift. Critical." |
| **1:46** | Drift event — unit-context callout + gate verdict | "The price didn't move — it's still $2.50. What changed is the fine print underneath. The unit flipped from 'per million input tokens' to 'input and output combined.' Same number, completely different bill. And look at the verdict: schema passes, invariants pass. The extraction is technically perfect. Only the semantics gate catches it." |
| **2:07** | Blast radius — +$626/mo + call sites | "Because DriftWatch knows what this feeds into, it prices the change. Roughly six hundred dollars a month — and here's every line in the connected repo that assumed the old meaning." |
| **2:19** | Migration note | "It writes the migration note too." |
| **2:22** | `#/ledger` | "Every decision — the heal, the verification, the approval — lands in an append-only ledger. Not log lines that scroll away. Queryable history." |
| **2:31** | Ledger scrolled — the full autonomous chain | "Diagnose. Heal requested. Preview verified. Auto-approved. Re-run. Verified again. Published." |

## Learning and growth

| Time | On screen | Say |
|---|---|---|
| **2:35** | Back to `#/web` — close | "What I learned is that self-healing is easy to fake and hard to trust. The engineering was in refusing to trust the heal's own success report — proving it against the same contract that caught the break, every time. Built entirely on Bright Data's Scraper Studio, open source, repo linked below." |

| **2:56** | *(hold on `#/web`, fade)* | *(silence)* |

---

## Recording the voiceover

- **Watch the timecode, not the clock.** Each line is budgeted for the shot it sits on; if you
  finish a line early, let the silence sit rather than starting the next one over the wrong shot.
- The two longest lines — **1:46** (the semantic catch) and **2:35** (the close) — carry the most
  weight and have the most room. Slow down on those, not on the short ones.
- **1:12**, **1:42**, **2:19** and **2:31** are short lines over motion. Say them once and stop.
- Export at 1080p, H.264, and keep the video stream untouched — only add the audio track.

## Why the earlier draft didn't fit

The previous version of this script ran **535 words**. At a natural 150 wpm that is **3:34** —
35 seconds over the cap. It only fit 2:55 on paper by assuming ~183 wpm, which is too fast to
land a technical demo. This version is cut to 444 words and the video was re-timed to match it,
so the fit is real rather than aspirational.

## Hackathon requirements

- **≤3:00 YouTube video** covering *about the project · tech stack and architecture · demo ·
  learning and growth (optional)* — all four present, in that order, at **0:00 / 0:25 / 1:12 / 2:35**.
- **Judging (six criteria, equal weight):** potential impact · creativity/innovation · technical
  excellence · **use of Scraper Studio** · **reliability and self-healing** · presentation.
  Scraper Studio and self-healing land at **1:16–1:33** (heal sequence, 4/4 gates, version bump)
  and **2:31** (the machine-signed ledger chain); impact lands at **2:07** (+$626/mo blast radius).
- The demo block runs **1:12–2:35 (83s)** — the largest single section, matching the guidance that
  the demo is scored as hard as the code.
