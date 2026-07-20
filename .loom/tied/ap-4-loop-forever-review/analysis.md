# Is the per-step "loop forever" control needed? — No.

Bob's question (2026-07-20): the step can just be set to play again; is
there any reason to keep the "loop forever" checkbox?

## What the checkbox did

`#show-play-forever` set `play_count: null`. In the engine
(`show_engine.py _on_expiry`), `play_count is None` re-emits the step's
messages and re-arms the timer each cycle, never resolving then-actions.

## The equivalent without it

`play_count: 1` (or n) + then-action **Play again** (`play_again`,
already in the inspector's then-action vocabulary). `_begin`'s docstring
names `play_again` as sharing the exact `step_start` semantics: messages
re-emit, the timer re-arms, progress/armed visuals rerun identically.

Capability comparison, case by case:

- **Message emission per cycle** — identical (`_emit_messages` both
  paths; cue forward-sync applies equally since all cues forward-sync).
- **Stopping** — identical: transport stop or starting any other step
  (exclusive one-step playback) kills both forms. Loop-forever had no
  special stop affordance.
- **"After N cycles do X"** — only expressible with finite
  `play_count` + then-actions; loop-forever made then-actions dead
  config. play_again loses nothing here.
- **Iteration counter** — `play_count: null` increments `iteration`
  across cycles; `play_again` restarts at 1 each cycle. Cosmetic only:
  nothing user-facing renders the iteration number today.
- **duration 0 guard** — loop-forever with `duration_s == 0` was
  rejected by the model (busy loop). A `duration 0 + finite count +
  play_again` chain instead hits the engine's synchronous-resolution
  budget (`MAX_SYNCHRONOUS_RESOLUTIONS`) and stops with a warning — the
  pathological case stays bounded.

No capability gap found → per Bob's 2026-07-20 ruling, the control is
removed.

## What changed / compatibility

- Removed: the checkbox markup and its change handler (`show.js`). The
  "play n times" input no longer gets disabled.
- **Kept**: `play_count: null` stays legal in `show_model.py` and the
  engine's forever branch stays — existing show files load and play
  unchanged. A legacy forever step shows an empty play-count input with
  placeholder "∞ (legacy)"; typing a number converts it to a finite
  count. No silent rewrites of Bob's show files.
- Model/engine untouched; UI-only change.
