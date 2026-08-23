# Prompt to paste into a Claude Code session with Claude-in-Chrome connected

Run this in a Claude Code session opened on the `D:\scrap_vulcan` folder, in an environment where the Claude-in-Chrome browser extension is installed and connected (same claude.ai account as that session).

---

Record a silent screen-capture GIF walkthrough of the DriftWatch app running locally, for a hackathon demo video. I (the user) will add narration audio separately in a video editor — you're only producing clean visual footage, no need to worry about audio.

**Read `submission/demo-video-script.md` first** — it's the authoritative shot list and timing, written for a 3-minute cap (the real hackathon submission form requires a YouTube link ≤3:00 covering: about the project, tech stack/architecture, demo, optional learning/growth). Follow its **On screen** column exactly, in order. Don't worry about matching its timestamps precisely — dwell 3–5 seconds longer than the script suggests on each screen so I have room to trim in editing; err toward more footage, not less.

## Setup

```bash
rm -f driftwatch.db driftwatch.db-*
python3 apps/engine/serve.py
```

Wait for it to report `Driftwatch engine starting on http://localhost:8000`. This gives a fresh, seeded demo world.

## Recording steps

1. Load the browser tools you need in one `ToolSearch` call: `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__gif_creator,mcp__claude-in-chrome__find`
2. `tabs_context_mcp` with `createIfEmpty: true`, then `tabs_create_mcp` for a fresh tab.
3. `navigate` to `http://localhost:8000` — this lands on `#/web`, "The Living Web."
4. `gif_creator` with `action: "start_recording"` on that tab, then immediately take a `computer` `screenshot` to capture the opening frame.
5. Walk through `submission/demo-video-script.md`'s **On screen** column, screen by screen, using `computer` (`left_click`, `wait`, `screenshot`) and `navigate` for hash-route changes. Key mechanics you'll need:
   - **Demo controls drawer**: click the element with id `demo-toggle` (bottom-left of the page) to open/close it. Inside, each source has a `<select data-source="...">` with options valued `v1_baseline` / `v2_redesign` / `v3_semantic` / `v4_material` / `v5_gone`, and a button `#demo-apply` labeled "Apply & run all" that applies every source's currently-selected variant and re-runs the whole pipeline. Use `find` with a query like `"NimbusAI variant dropdown"` if you need to locate exact coordinates.
   - **Demo sequence** (matches the script): open drawer → set NimbusAI's select to `v2 — overnight redesign (breaks template)` → click Apply & run all → wait for it to finish (a few seconds) → navigate to `#/heal` to show the healed result. Then open drawer again → set NimbusAI's select to `v3 — unit meaning silently changes` → Apply & run all → navigate to `#/events` → click into the new **Class 4 · Semantic** event (it'll be the most recent one) → this is the centerpiece shot, hold it for a full 10–15 seconds since narration covers a lot here → navigate to `#/ledger`.
   - Routes available via `navigate` (append the hash to `http://localhost:8000/`): `#/web`, `#/sources`, `#/sources/<id>`, `#/events`, `#/events/<id>`, `#/heal`, `#/ledger`.
6. Before the final screen, take one more `screenshot` (captures the closing frame), then `gif_creator` with `action: "stop_recording"`.
7. Export: `gif_creator` with `action: "export"`, `download: true`, a descriptive `filename` like `driftwatch-demo-raw.gif`, and in `options` set `showWatermark: false`, `showClickIndicators: false`, `showActionLabels: false`, `showDragPaths: false`, `showProgressBar: false` — I want clean raw footage with no overlays, since I'm dubbing narration over it myself.
8. Find where the browser downloaded the GIF (likely the user's default Downloads folder — check via a shell command), then copy it into `D:\scrap_vulcan\submission\driftwatch-demo-raw.gif` so it's alongside the script.
9. Close any tabs you created with `tabs_close_mcp`. Leave the `serve.py` process running (don't kill it) — I may want to re-record a segment.

## When done

Tell me: the final saved path of the GIF, its rough duration/frame count, and whether every beat in `demo-video-script.md` made it into the capture (flag anything that didn't render as expected, e.g. if the Class 4 event took a different event ID than expected — just click whatever the newest semantic-drift event is). Note that GIF is not the final submission format — I still need to convert it to video and merge audio in my own editor before uploading to YouTube; you don't need to do that conversion.
