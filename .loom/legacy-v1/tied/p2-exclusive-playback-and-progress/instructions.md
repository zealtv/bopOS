# p2-exclusive-playback-and-progress

Engine semantics + the two playback visualisations.

1. **Exclusive playback.** Only one step in the column may be playing (or
   paused) at a time. Starting a step — by click, by then-action, or by
   the p3 global transport later — stops the currently playing step first,
   in the engine (`show_engine.py`), not the UI. Then-action chains
   (next/previous/goto/any/other) already move focus from one step to the
   next; the rule closes the "manually start a second step while one
   plays" hole. Keep the data model single-column-agnostic: exclusivity is
   an engine policy, not a schema change. `stop_all_steps` and the playing
   indicator simplify accordingly (at most one entry) but the wire/WS
   `show_playback` shape stays a map — don't break tied verifies'
   expectations more than the rule itself requires.
2. **Progress-meter fill.** A playing step's row fills left-to-right like
   a progress bar as its current iteration elapses (use the existing
   `remaining_s`/duration data the countdown already interpolates
   client-side; CSS width on a row-background layer, cheap at 500 ms tick
   granularity, no per-frame JS). Paused freezes the fill.
3. **Armed blink-pulse.** When a step is the pending target of a
   then-action (the step that will fire next — engine must expose the
   armed uid in `show_playback`), its row shows a subtle blink-pulse
   ("ready to fire"). Subtle: opacity/border pulse consistent with the
   dark theme, no layout movement. Random then-actions (any/other/multi)
   arm at resolution time — the engine already resolves the choice when
   the action fires, so armed state only exists once known; do not
   pre-resolve early just to show a pulse (that would change random
   semantics). Document in the worklog what the engine exposes and when.

Verify: `verify_show_exclusive.py` (house pattern, simfleet): starting
step B while A plays stops A (engine snapshot + UI both agree); a
then-action hop keeps exactly one playing; progress fill width grows
between two samples of a playing step; armed row carries the pulse class
when a finite-duration step points at it. Re-run tied 3-playback-engine
and amend its multi-playing assumptions if any (log it).
