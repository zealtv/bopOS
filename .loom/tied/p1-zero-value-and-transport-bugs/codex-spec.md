# Task: fix four Show-tab UI defects in the bopOS dashboard

Repo: /Users/bob/repos/bopOS. All changes are in `dashboard/static/js/show.js`,
`dashboard/static/css/style.css`, and one new verify script. Python server code
needs no changes. Never touch any `.pd` file.

## Background

The Show tab (`dashboard/static/js/show.js`) renders a step list from a
WebSocket-broadcast document (`show`) and playback state (`show_playback`).
All edits round-trip: the client sends a WS message, the server broadcasts the
updated document, and `render()` rebuilds the DOM. `ws` is a tiny pub/sub
wrapper (`dashboard/static/js/ws.js`).

## Fix 1 — parameter value 0 falls through to the default

`renderParamBuilder` (show.js ~line 514) computes
`const value = argValue(message.args?.[0]) || declaration.default || "";`
A stored value of `0` is falsy, so the input re-renders showing the
declaration default instead of 0. Note the helper `argValue` returns
`arg?.value ?? ""` — it coalesces missing to `""`, so it cannot distinguish
"no arg" from a stored empty string; read the raw `message.args?.[0]?.value`
and use nullish coalescing: stored `?? declaration.default ?? ""`.

Then audit every `||` fallback in show.js applied to a value that can
legitimately be `0` or `""` and convert those to `??` where wrong (leave `||`
where the operand genuinely can't be a meaningful falsy value — e.g. string
addresses). Also grep `dashboard/static/js/facilitator.js` and
`dashboard/static/js/dashboard.js` for the same `value || default` pattern on
live-control/parameter values; fix any true instances and list in your report
each site you changed and each candidate you inspected and left alone, with
one-line reasons.

## Fix 2 — transport clicks lost during the WS round-trip

The three per-step transport buttons (`stepTransport`, show.js ~263) render
from the last broadcast state. Clicking play then immediately clicking again
sends `step_start` twice, because the button still carries the stale action
until the `show_playback` broadcast lands.

Fix with optimistic local state, entirely client-side, in `sendTransport`
(show.js ~587): before `ws.send`, update the local `playback.steps` to the
intended post-verb state and call `render()`. Mapping:

- `step_start` → `{state: "playing", iteration: 1, remaining_s: null}`
  (remaining unknown until the server reports; `remainingSeconds` already
  handles non-finite by showing the step duration)
- `step_stop` → delete the uid's entry (renders as stopped)
- `step_pause` → compute the currently displayed remaining via
  `remainingSeconds(uid)` first, then set
  `{state: "paused", remaining_s: thatValue}` preserving other fields
- `step_resume` → `{state: "playing"}` preserving `remaining_s`, and set
  `playbackAt = performance.now()` so the countdown resumes from there
- `stop_all_steps` → `playback = {steps: {}}`

The server's next `show_playback` broadcast overwrites this (that handler
already replaces `playback` wholesale and resets `playbackAt`) — that stays
the source of truth. Keep the countdown-timer start/stop logic working; it is
fine for the optimistic render not to start the interval timer.

Result: a rapid play→stop double click leaves the step stopped, because the
second click hits a button already rendered as Stop.

## Fix 3 — "trigger next" glyph illegible

CSS only (`dashboard/static/css/style.css`, the `.show-glyph-next` rules
inside the one-line show section around line 50). The current glyph is a tiny
8px triangle with a 2.5px bar — operators mistake it for the play triangle.
Redraw it as a clearly legible skip-to-next icon (`▶▶` or `▶|`) at the same
button size (28×26px): larger triangle(s), thicker bar, visually distinct
from `.show-glyph-play` at a glance. Keep the drawing technique consistent
with the neighbouring glyph rules (borders/pseudo-elements, currentColor).

## Fix 4 — step title shifts when transport buttons appear

Stopped steps render one transport button; playing steps render three, which
reflows `.show-step-row` and moves the title. Reserve the three-button worst
case: give `.show-step-transport` a fixed width (3×28px buttons + 2×5px gaps
= 94px; keep `display:flex`). The alias column must not move between stopped
and playing.

## Verify script (new)

Write
`.loom/threads/15-show-polish/p1-zero-value-and-transport-bugs.stitching/verify_show_polish_bugs.py`.
Copy the house pattern from
`.loom/tied/6b-show-management/verify_show_management.py` — repo root by
marker (walk up to `tools/simfleet.py`), random loopback ports, real
`dashboard/server.py` + `tools/simfleet.py`, headless Chromium via Playwright
sync API, teardown in `finally`, `check()` result lines, exit 1 on failure.
Reuse its fixture (one step with a `/p/gain` message, manifest default 0.4).

Checks, in order:

1. **Zero value sticks.** Open the Show tab, click the message pill
   (`[data-show-message-focus]`), fill `#show-param-value` with `0`, dispatch
   a change (Playwright `fill` + `blur`, or `press("Tab")`). Wait for the
   round-trip, then assert `#show-wire-preview` text contains `f:0` and the
   re-rendered `#show-param-value` input value is `"0"` (not `0.4`).
2. **Rapid play→stop.** Click the step's play button, then immediately (no
   waits) click the first transport button again. Assert the playing
   indicator (`#show-playing-indicator`) reads `0 playing` after the
   round-trip, sleep 1s, assert it still reads `0 playing`.
3. **Optimistic render.** Fresh: click play once; without waiting for any
   broadcast the first transport button's `data-show-action` should already
   be `step_stop` (assert immediately after the click). Then stop the step.
4. **Title stability.** With the step stopped, `window.scrollTo(0,0)` and
   read the bounding-box x of `.show-step-alias`; start the step, wait for
   `show-step-playing` class, scroll to 0,0 again, re-read; assert identical
   x. Stop the step.
5. **Next control present and distinct.** While playing, assert the
   `[data-show-action="step_trigger_next"]` button exists and that the
   computed size of its glyph (`.show-glyph-next`, including pseudo-element
   technique — just assert the element's bounding box is at least 10px wide)
   differs from the play glyph's drawing (assert its class list differs and
   width ≥ 10). Keep this check simple.
6. **No page errors** (collect `pageerror`).

Playwright gotchas (learned in this repo): `inner_text` applies CSS
`text-transform`, lowercase before matching capitalized text; clicking can
auto-scroll — `window.scrollTo(0,0)` and re-read boxes before comparing
positions; install exactly one type-aware dialog handler (prompt→accept with
text, else accept); `page.wait_for_function(expr, arg=value)` — the argument
is keyword-only.

Run it with `~/.venvs/bopos/bin/python` (has playwright + chromium
installed). Do not use system pip.

## Acceptance checks (run these; all must pass)

```sh
~/.venvs/bopos/bin/python .loom/threads/15-show-polish/p1-zero-value-and-transport-bugs.stitching/verify_show_polish_bugs.py
~/.venvs/bopos/bin/python .loom/tied/4-tab-ui/verify_show_tab.py
~/.venvs/bopos/bin/python .loom/tied/5-inspector/verify_show_inspector.py
~/.venvs/bopos/bin/python .loom/tied/5b-compact-rows/verify_show_compact.py
~/.venvs/bopos/bin/python .loom/tied/5c-target-model-and-picker/verify_show_targets.py
~/.venvs/bopos/bin/python .loom/tied/6-message-editing/verify_show_editing.py
~/.venvs/bopos/bin/python .loom/tied/6b-show-management/verify_show_management.py
```

Each prints `0 failure(s)` and exits 0. If a tied verify fails because a
selector/layout legitimately moved under fixes 3/4, amend that tied script
minimally and record the amendment in your report; if it fails for any other
reason, treat it as a regression in your change and fix the change, not the
test.

Do not commit. When done, write a report to
`.loom/threads/15-show-polish/p1-zero-value-and-transport-bugs.stitching/codex-report.md`:
what you changed (per fix), the `||`→`??` audit table, verify results, any
tied-verify amendments, and anything you could not do. If you could not
complete the task, say so explicitly.
