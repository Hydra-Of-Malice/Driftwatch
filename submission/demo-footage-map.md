# Demo footage — files and specs

Two files, both **silent, no overlays, no cursor**, both captured in **Spider Mode** against a
freshly seeded local instance.

| File | Duration | Use |
|---|---|---|
| **`driftwatch-demo.mp4`** | **2:56** · 5.8 MB | **The one to publish.** Already cut to length and timed to the narration in [demo-video-script.md](demo-video-script.md). |
| `driftwatch-demo-raw.mp4` | 4:03 · 7.1 MB | Uncut take, longer dwells. Only needed to re-cut a shot differently. |

Both: 1920×1080 · H.264 High · yuv420p · 30 fps · no audio track.

## How the cut was made

The raw take is 243s, of which only **34s is actual motion** (page transitions and scrolls) — the
other 209s is static dwell. The cut resamples *only* the static dwell inside each shot, leaving every
transition and scroll at its original pacing. So each shot lasts exactly as long as the line spoken
over it, and nothing looks sped up or clipped.

Word budget drove the timing: 444 words ÷ 150 wpm = 2:56. Beat durations are proportional to their
word counts, floored so no shot is shorter than its own motion plus a beat of breathing room.

## Capture setup

Playwright-driven Chromium, viewport 1536×864 at device-scale-factor 1.25 (renders 1920×1080 with
the layout at a comfortable reading size — at a raw 1920 viewport the app leaves ~30% dead space).
Spider Mode is set via `localStorage['dw-theme'] = 'spider'` in an init script so the page boots into
the theme with no flash of dark.

Frames are captured as PNG and encoded straight to H.264 — the source is never a video, so there is
no generation loss.

## Re-recording

Scripts live in this session's scratchpad: `record.py` (capture), `build_mp4.py` (raw encode),
`build_cut.py` (the timed cut), `gen_cue.py` (the published cue sheet). To redo a take:

```bash
rm -f driftwatch.db driftwatch.db-* && python backend/serve.py
```

then re-run `record.py`, `build_mp4.py`, `build_cut.py`. Event IDs are deterministic off a clean
seed — the semantic-drift event lands as **#6** every time.
