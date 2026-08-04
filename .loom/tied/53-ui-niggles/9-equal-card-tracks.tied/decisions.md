# Decisions

- Both surfaces now use CSS Grid rather than Flexbox. A grid column has one
  width shared by every row, so an incomplete final row cannot grow its cards
  independently.
- Each host publishes `--target-grid-max` from its current rendered card count:
  `count × 560px + gaps`. The grid uses the smaller of that cap and the
  available width. This preserves the 560px ceiling for sparse sets while
  allowing equal tracks to flex down toward 340px as columns wrap.
- Control owns the cap for its authored outer card set. `ControlColumn` owns it
  only for Remote's derived inner card set; single-target Control instances
  clear the inner value.
- The shared target-card face retains the 560px component ceiling. Its old flex
  declaration was removed because grid items no longer use flex sizing.
