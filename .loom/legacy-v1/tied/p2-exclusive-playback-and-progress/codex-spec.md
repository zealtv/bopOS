# Task: exclusive playback, progress fill, armed pulse (bopOS Show tab)

Repo: /Users/bob/repos/bopOS. Files: `dashboard/show_engine.py`,
`dashboard/static/js/show.js`, `dashboard/static/css/style.css`, one new
verify script. Never touch `.pd` files.

## Background

`dashboard/show_engine.py` is an asyncio state machine driving the Show tab's
steps; `dashboard/static/js/show.js` renders from its `show_playback`
broadcasts (`{"steps": {uid: {state, iteration, remaining_s, ...}}}`).
Every step start — manual, or any then-action — funnels through
`ShowEngine._begin`.

## Change 1 — exclusive playback (engine policy, no schema change)

Only one step may be playing **or paused** at a time. Implement in
`ShowEngine._begin`: before installing `self.playback[uid]`, stop (via
`_stop_step`) every other uid currently in `self.playback`. That single hook
covers manual `step_start`, and all then-action transitions. Do not change
the show document schema or the `show_playback` wire shape (still a map).
`stop_all_steps` and the playing indicator need no code change — they just
naturally see at most one entry.

Note `_transition` calls `_stop_step(old)` then `_begin(new)` — after your
change the extra sweep in `_begin` must be a no-op there, not a bug (it
stops nothing because old is already gone).

## Change 2 — armed uid in the snapshot (engine)

The "armed" step is the step that will fire next, when that is knowable
without pre-resolving randomness:

- In `snapshot()`, compute a top-level `"armed": <uid or None>` field
  (additive to the payload; keep `"steps"` unchanged).
- Armed is computed only when there is exactly one active (playing or
  paused) step. Look at its `then_actions`:
  - zero actions → implicit stop → armed None.
  - exactly one action → deterministic kinds resolve to a concrete uid:
    `next_step` / `previous_step` (adjacent step uid), `next_section` /
    `previous_section` (that section's first uid), `goto` (its
    `target_uid` if it still exists, else None), `play_again` (the step's
    own uid). `any_in_section` / `other_in_section` → None (random resolves
    only at fire time; never pre-resolve — it would change random
    semantics).
  - multiple actions → None (the engine picks randomly at fire time).
- Recompute fresh on every snapshot (the document may have been edited);
  no caching.

## Change 3 — progress-meter fill (client + CSS)

A playing step's row fills left-to-right as its current iteration elapses.

- show.js already interpolates `remaining_s` client-side
  (`remainingSeconds`) on a 500 ms re-render tick. In `stepRow`, compute
  `fraction = 1 - remaining / duration_s` (clamp 0..1; only when remaining
  is non-null and `duration_s > 0`) and render a fill layer inside the row,
  e.g. `<div class="show-step-progress" style="width:NN%"></div>`.
- CSS: `.show-step-row` gets `position:relative`; the fill layer is
  absolutely positioned (inset top/left/bottom 0), behind the row content
  (`z-index` or source order + row children `position:relative`), a subtle
  green-tinted translucent fill consistent with the dark theme. Paused
  keeps the frozen width (remainingSeconds already freezes for paused —
  tint amber to match the paused accent if trivial). No layout movement.
- Edit the existing one-line show CSS block in place, matching its
  minified idiom. Do not add `!important` layers.

## Change 4 — armed blink-pulse (client + CSS)

When `playback.armed === step.uid`, `stepRow` adds class
`show-step-armed`. CSS: a subtle repeating opacity/border pulse
(~1.5–2 s cycle, keyframes animating border-color or box-shadow opacity)
— "ready to fire", no layout movement, dark-theme consistent. A step that
is both active and armed (play_again) keeps its normal active styling with
the pulse on top.

## Verify script (new)

`.loom/threads/15-show-polish/p2-exclusive-playback-and-progress.stitching/verify_show_exclusive.py`
— house pattern; copy
`.loom/tied/p1-zero-value-and-transport-bugs/verify_show_polish_bugs.py`
for the harness shape (repo root by marker, random ports, real server +
tools/simfleet.py, headless Chromium, teardown, `check()` lines, exit 1 on
failure). Fixture: three steps A, B, C where A's single then-action is
`goto` → C, all with duration_s ≥ 4 so timers don't fire mid-assert; plus a
two-step section if convenient.

Checks:

1. **Exclusivity, manual**: start A, wait playing; start B; assert A's row
   is stopped and B playing (UI), and via a second sample after 500 ms that
   exactly one row has the active class.
2. **Exclusivity, then-action hop**: use `step_trigger_next` on a playing
   step whose action is goto → C; assert exactly one playing (C).
3. **Progress fill grows**: with a step playing, sample the
   `.show-step-progress` width twice ~1.2 s apart; assert the second is
   strictly larger, and that pausing freezes it (two more samples equal).
4. **Armed pulse**: while A (goto→C) plays, assert C's row has
   `show-step-armed`; stop A, assert the class is gone. Also assert a step
   with two then-actions arms nothing.
5. **No page errors.**

## Acceptance checks (run these; all must pass)

```sh
~/.venvs/bopos/bin/python .loom/threads/15-show-polish/p2-exclusive-playback-and-progress.stitching/verify_show_exclusive.py
~/.venvs/bopos/bin/python .loom/tied/3-playback-engine/verify_show_engine.py
~/.venvs/bopos/bin/python .loom/tied/p1-zero-value-and-transport-bugs/verify_show_polish_bugs.py
~/.venvs/bopos/bin/python .loom/tied/4-tab-ui/verify_show_tab.py
~/.venvs/bopos/bin/python .loom/tied/5-inspector/verify_show_inspector.py
~/.venvs/bopos/bin/python .loom/tied/5b-compact-rows/verify_show_compact.py
~/.venvs/bopos/bin/python .loom/tied/5c-target-model-and-picker/verify_show_targets.py
~/.venvs/bopos/bin/python .loom/tied/6-message-editing/verify_show_editing.py
~/.venvs/bopos/bin/python .loom/tied/6b-show-management/verify_show_management.py
```

The tied `3-playback-engine` suite may legitimately assume multiple steps
can play at once — that assumption is exactly what this stitch retires.
Amend such assertions minimally to the exclusive rule and record every
amendment in your report. Any other failure is a regression in your change:
fix the change, not the test.

Do not commit. Write a report to
`.loom/threads/15-show-polish/p2-exclusive-playback-and-progress.stitching/codex-report.md`:
what changed per change-number, what `snapshot()` now exposes and when,
tied-verify amendments, verify output, anything not done. If you could not
complete the task, say so explicitly.

Do not run loom.sh, tie, claim, or otherwise touch .loom state — the orchestrator manages the loom. Work only the files this spec names.
