# AI Usage Disclosure

[← Documentation index](README.md)

---

> Required by the *Into the Scrape-Verse* rules: *"AI coding assistants are allowed, but their use must be disclosed."* This page states what was used, when, and for what — evidenced by git history and this repository's own commit trail, not asserted from memory.

## What was used

| Tool | Role | Evidence |
|---|---|---|
| **Claude Code** (Anthropic, `claude-sonnet-5`) | Primary development assistant for the majority of this repository's history: engineering fixes, the full `docs/` engineering documentation set (sections 01–11), security/reliability hardening, and this disclosure page itself | `git log` — every commit from `ddfe0b7` (2026-08-21) onward |
| **T3 Code** | Used for earlier project scaffolding | `git log` — checkpoint commits `4e60827`, `976638c` (2026-08-10), authored `T3 Code <t3code@users.noreply.github.com>` |

Both are AI coding agents operating with repository write access, not autocomplete-only tools — disclosed at that level of involvement rather than understated.

## What AI did, concretely

This session (2026-08-22), working with Claude Code, directly:

- Investigated the actual codebase (pipeline, contracts, healing, API, tests) rather than generating documentation from filenames alone, and wrote the engineering documentation set under `docs/08_Deployment` through `docs/11_Assessment` — each claim cited to a file, function, or test.
- Found and corrected an overclaim already present in `docs/09_AI_ML/AI_Architecture.md` — an earlier pass had stated no live Bright Data evidence existed; `scripts/spike_out/*.json` shows it does, just as a recorded failure. That correction is preserved in the doc and in this repository's commit history rather than silently edited away.
- Implemented and tested five concrete engineering fixes: opt-in bearer-token auth, a `127.0.0.1` default bind, a `heal_events.seeded` column so `/api/stats` stops blending a fabricated demo constant into a measured average, contract-existence validation on `POST /api/onboard`, and SQLite hardening (`busy_timeout`, 8 indexes). Verified against a running server (`curl` against live endpoints), not just against the test suite.
- Ran the full test suite (`python -m unittest discover`, 23/23 passing) after every code change in this session before committing.
- Then propagated every status change back through ~26 already-written documents so the documentation set doesn't go stale relative to the code — updating scores, tables, and diagrams rather than leaving contradictions for a reviewer to find.

## What this means for judging

This is disclosed at face value: a substantial share of this repository's code, fixes, and documentation were produced with AI coding assistance across multiple sessions, under human direction and review at each step (this document, the fixes it describes, and the documentation set were all reviewed and committed by the repository owner, not auto-merged). The engineering judgment calls — what to prioritize under the submission deadline, which gaps to leave open and why, how to score production readiness — are recorded throughout `docs/11_Assessment/` with reasoning attached, so a judge can evaluate the *reasoning*, not just take the disclosure on faith.

**What AI did not do:** invent the project's core thesis unsupervised, fabricate test results or performance numbers (the documentation set's evidence conventions — `IMPLEMENTED` / `VALIDATED` / `NOT IMPLEMENTED` / `UNVALIDATED` — exist specifically to prevent that), or silently hide known limitations. Where a claim couldn't be verified against the running code, it is labeled as such rather than presented as fact — see [`docs/README.md` § Evidence & Status Conventions](README.md#evidence--status-conventions).

---

**Next:** [Executive Summary](EXECUTIVE_SUMMARY.md) · [Judge Evaluation](11_Assessment/Judge_Evaluation.md)
