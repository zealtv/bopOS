# ap-4 notes

Analysis in `analysis.md`: no capability gap — `play_count: null` is
fully expressible as a finite count + the existing **Play again**
then-action (same `_begin`/`step_start` semantics, same stop semantics,
strictly more expressive around "after N cycles do X"). Per Bob's
2026-07-20 ruling the checkbox was removed.

UI-only change in `show.js`: checkbox markup + change handler gone; the
play-count input is never disabled. `show_model.py` and
`show_engine.py` untouched — `play_count: null` remains legal, so
existing show files load and play unchanged; a legacy forever step shows
an "∞ (legacy)" placeholder and typing a number converts it. No silent
rewrites of persisted shows.

## Verify

`verify_loop_forever_removal.py` (house pattern): legacy show with
`play_count: null` loads; checkbox absent; placeholder present; input
enabled; the legacy forever step still loops past 2 cycles and stops
from the transport; a `play_again` self-loop loops and stops the same
way; typing a count persists `play_count: 3` to the show file; no
console errors.

Run: `~/.venvs/bopos/bin/python verify_loop_forever_removal.py` →
**All loop-forever removal checks passed** (10 checks), 2026-07-20.

For Bob: nothing here needs your attention — the analysis found no
reason to keep the toggle. If you ever want "loop forever" back it is
one then-action away (`Play again`), and legacy files never broke.
