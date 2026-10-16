# 3-tilt-bank-pi-budget

**Goal:** know what streaming tilt banks costs on a Pi 3A+ running the real fleet image, alongside the
Stage 1 backing track.

Measure:

- Pd CPU with a bank playing, including the moment two players overlap during a loop crossfade, at
  the default and a faster tilt poll rate.
- SD reads with the most streams that can be open at once: the tilt bank's two players plus the
  backing track. Watch for underruns (`readsf~` buffer size is a knob).
- Temperature over a long run.

**Done when** the numbers are written here, and they show the worst case of streams open at once
runs all day without dropouts.
