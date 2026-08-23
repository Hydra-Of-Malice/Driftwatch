# Submission form — pre-drafted answers

For https://forms.gle/iQf2SjHQViSJaRAv7. Fields I can't fill for you (need your actual info, or aren't determinable from the repo) are marked. The two open-text fields are drafted below, ready to paste — edit freely, these are a starting point grounded in what's actually verified in this repo, not marketing copy.

## Fields you fill in yourself

| Field | Note |
|---|---|
| Email | yours |
| Team name | yours |
| Name of the person submitting | yours |
| Track you are submitting for | Not determinable from the repo — the tracks are **Web-Slinger** (grand prize, "Best Use of Bright Data"), **Suit-Up** ("looks and feels finished"), **Spider-Sense** ("readable, structured, handled at edges"), **Daily Bugle** (LinkedIn post). DriftWatch's strongest natural fit is **Web-Slinger** — the entire thesis is closing the human-shaped loop Bright Data's own `heal` command leaves open (see `docs/11_Assessment/Judge_Evaluation.md` § Use of Scraper Studio). Check the form's actual options before picking; it may allow more than one. |
| GitHub link to project | `https://github.com/Hydra-Of-Malice/Driftwatch` |
| Deployed link to project | None exists — this runs locally only, no hosted deployment (see `docs/08_Deployment/Deployment_Architecture.md`). Leave blank or say so if the field is required; don't invent a URL. |
| YouTube video demo link | Fill in once you've recorded, edited, and uploaded (see `demo-video-script.md`) |

## What does your project do?

> DriftWatch turns the public pages your product silently depends on — model pricing, API docs, rate limits, vendor terms — into versioned data contracts that repair themselves when the underlying page changes, then tell you what the change actually means for your code and your bill.
>
> The failure mode it's built around is worse than a broken selector: extraction that succeeds and is still wrong. A provider can hold a price at $2.50 while quietly changing what that price applies to — say, from "per million input tokens" to "input and output combined." Every scraper still returns green. Every downstream number is now wrong, and nothing structural broke, so nothing structural can catch it.
>
> DriftWatch gates every extraction behind four checks — schema, data-quality invariants, a semantic-meaning check (the scraper is told to capture the unit text next to each value, and the contract asserts it still matches), and plausibility against history. Anything that fails a gate is quarantined, not published. When a page redesign breaks the scraper outright, DriftWatch diagnoses the failure, composes the repair prompt itself, sends it to Scraper Studio's heal command, and — critically — never trusts the heal's own success report. It re-runs the exact same four gates against the repaired output before approving anything into production. A repair that can't be re-proven stays rejected and the pipeline stays pinned to the last verified version.
>
> Every one of these decisions — detect, diagnose, heal, verify, approve — lands in an append-only audit ledger, machine and human decisions alike. 23 tests walk all five drift classes end to end.

## How did you use Scraper Studio in your project?

> Scraper Studio is the extraction and repair engine the whole product is built around, not a bolted-on data source:
>
> - **`scraper create`** (AI Flow) onboards every watched page — one custom Studio scraper per source, built from a natural-language description.
> - **`scraper run`** executes the scheduled pipeline, with `--version` pinning so rollback is just "don't advance the pointer" rather than a rollback operation that could itself be buggy.
> - **`scraper heal`** is driven autonomously: DriftWatch diagnoses exactly which fields broke and why, composes a heal prompt from that diagnosis (kept within Studio's 1000-character limit), and sends it — closing the loop that Bright Data's own CLI leaves for a human to close by hand.
> - The **`awaiting_approval` gate and `preview_result`** are never trusted at face value — the preview is re-evaluated against the full semantic contract, and only that independent verdict decides whether to call `scraper approve` or `--reject`.
> - **`discover --intent`** proposes relocation candidates when a watched page 404s (Class 5 / availability drift).
>
> The reference build ships in replay mode — a faithful fixture-and-mirror simulation of the same CLI envelope shapes, so the full break→heal→verify→approve story is reproducible in tests and on stage without depending on a live page misbehaving on cue. The live client (`DW_MODE=live`) is fully implemented behind the same interface; a real Day-0 spike against it is in `scripts/spike_out/`, and it hit vendor-side errors (`"Automation not allowed"`, `"Self healing tool is temporarily disabled"`) rather than a code defect — documented plainly in `docs/09_AI_ML/AI_Architecture.md` rather than glossed over.
