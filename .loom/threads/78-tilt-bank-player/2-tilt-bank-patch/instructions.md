# 2-tilt-bank-patch

**Goal:** a Pd abstraction that plays a tilt bank from tilt.

- Stream the bank (format from `1`) with `readsf~`, as the Kite Choir Glean finding
  `stream-kite-choir-audio-with-readsf` says. Start from `bop.stream~`. Read the channel count from the file header (`soundfiler` with no
  arrays) and read the parameter file.
- Loop with two players and a subtle crossfade at the loop point. Use the same fade for bank switches.
  Start each spool at a random offset.
- Map tilt to a position across the channels with a per-unit zero and the bank's `max_angle`, then
  set each channel's gain from `width` and the crossfade curve. Smooth the gains with `line~`.
- Fade the centre channel out by `centre_decay`.
- Boot into a default bank with no network. A `/spoolsynth/play <bank>` cue switches banks.
- Try a faster tilt poll than the 10 Hz default and note whether it plays better.

Out of scope for this stitch: the per-angle attack envelope and the dynamic filter.

**Done when** the test bank plays from tilt on a spool, the loop seam and bank switches are inaudible
or acceptably soft, there is no zipper noise, and Bob has played it.
