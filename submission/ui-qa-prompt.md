# Prompt to paste into the Claude Code session with Claude-in-Chrome connected

Run this in the session on `D:\scrap_vulcan` that has browser control. Purpose: visually QA a new theming system (light/dark/spider themes) and UI polish pass I can't see myself — I have no browser access in my session and only verified it by curl/syntax-check, not by looking at it.

## Setup

The server is likely already running at `http://localhost:8000` (PID may vary — check with a quick request first). If it's not responding, start it fresh: `rm -f driftwatch.db driftwatch.db-* && python3 backend/serve.py`.

Load the browser tools you need in one `ToolSearch` call: `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__find`

Open a **fresh new tab** (not a reused one) and navigate to `http://localhost:8000` — a fresh tab sidesteps any browser cache serving an old version of the page.

## What changed, for context

`frontend/assets/{styles.css,app.js,viz.js}` and `frontend/index.html` were rewritten to add: three themes (light/dark/spider) switchable via a small pill control at the bottom of the left rail (sun/moon/spider icons), animated count-up stat tiles, empty states, severity-colored event cards, a hero visual treatment for the Class-4 semantic-drift moment on the event detail page, hand-drawn nav icons, and spider-theme-specific flourishes (web-line background texture, themed favicon, a "spider-sense" animation variant). None of this touched backend logic, data, or decisions — presentation only.

## What to check

1. **Theme switcher exists and works.** Screenshot the default (dark) view first. Click each of the three theme buttons in the rail (bottom-left, above "Demo controls") and screenshot after each. Confirm: the page actually re-colors, the active button gets a visual highlight, and the browser tab favicon changes per theme (zoom in on the tab if needed).
2. **Light theme readability.** This is the one most likely to have a contrast bug — check body text, muted labels, and especially the drift-class badges (colored pills with glyphs) are all legible against the white/off-white background, not washed out.
3. **Spider theme.** Confirm it reads as a *dashboard* (not a costume) — background texture should be barely-there, not distracting. Check the red/blue/purple palette doesn't clash or reduce legibility anywhere.
4. **Card titles didn't get flattened.** Go to `#/sources` — the source names (e.g. "NimbusAI — Platform Pricing") must render as normal-sized readable headings, NOT tiny uppercase gray text. (This was a caught-and-fixed bug — confirm the fix actually took.)
5. **The Living Web (`#/web`).** Check the center node has a slow breathing pulse (watch for a few seconds) and faint particles traveling along the lines to each source node. Check the stat tiles count up from 0 on page load (may need a reload to catch it — it's fast, ~650ms).
6. **The semantic-drift hero moment.** Use "Demo controls" (bottom-left) to set NimbusAI to "v3 — unit meaning silently changes" and Apply & run all, then go to `#/events` and open the new Class 4 · Semantic event. Confirm: a highlighted box shows the unit-context text before→after, and in the verification-verdict list the failed "semantics" gate has a visibly bigger, glowing dot compared to the other (passing) gates.
7. **Empty states don't look broken.** Click through the class-filter chips on `#/events` to a class with zero events — should show a friendly dashed-circle icon + message, not a blank gap.
8. **Console errors.** Use `read_console_messages` after navigating through a few views — flag any JS errors (there should be none).
9. **General polish.** Hover over a few source/event cards (should lift slightly with a shadow), and try a disabled-button state if convenient (e.g. click "Apply & run all" and screenshot mid-request — the button should look visibly disabled, not just unclickable).

## Report back

For each theme, one representative screenshot. Explicitly call out anything that looks broken, misaligned, low-contrast, or just off — don't just confirm the happy path. I'll fix whatever you find.
