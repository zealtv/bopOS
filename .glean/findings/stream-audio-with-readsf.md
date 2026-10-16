# Stream audio from the SD card with readsf~; don't load it into RAM

Play sound files in bopOS by streaming them with `readsf~` and hiding loop points and switches with short, subtle fades. Don't load audio into arrays with `soundfiler`.

## Why

Bob, 2026-10-16: *"I want to avoid loading in to ram. Would prefer adding subtle fades and using
readsf~. This is the strategy throughout."* He said this while reviewing the tilt-bank design
(`78-tilt-bank-player`), after a proposal to play from RAM for gapless loops. The ruling covers all
of bopOS, not only tilt banks.

How it's applied:

- **Looping:** `readsf~` doesn't loop seamlessly, so run two players and crossfade between them at
  the loop point, or fade out and back in.
- **Channel count:** `readsf~` fixes its channel count when it's created. Create it with the most
  channels a file may have, and use `soundfiler` with no arrays to read only the header. That reads
  the file's real channel count without loading any audio.
- **Budget:** the cost moves to SD reads and the number of streams open at once, so measure both on
  the Pi.

## Associations

- [[hardware-claims]]
