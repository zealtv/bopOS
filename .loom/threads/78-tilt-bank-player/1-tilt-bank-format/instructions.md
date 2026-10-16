# 1-tilt-bank-format

**Goal:** settle what a tilt bank is on disk, so Cayn can author one and the patch can load it.

Decide:

- **Delivery form.** The player streams **one interleaved N-channel WAV**, which keeps the angles in
  sync with a single `readsf~`. If Cayn finds 9 mono bounces easier from Logic, `sox -M` interleaves
  them before the file reaches the Pi.
- **Parameter file** next to the audio: a plain text format Pd's `text` object can read. Start with
  `width`, `centre_decay`, `max_angle`, `gain`, and a curve choice (equal-power or equal-gain).
- **Limits:** sample rate, bit depth, and the maximum channel count. `readsf~` is created with that
  many channels.
- **Naming:** follow the sample-bank rule — one lowercase token, no hyphen inside a name.
- **Loop seam:** the player crossfades at the loop point, so a bank needs a little material at each
  end that can overlap. Say how much.

Make one synthetic test bank (for example, 9 tones on a scale) so `2` can be built before Cayn
delivers real material.

**Done when** the format is written down in bopOS docs, a test bank exists, and Kite Choir has
passed it to Cayn as the tilt sample set format (brains stitch `composition-october-priorities`).
