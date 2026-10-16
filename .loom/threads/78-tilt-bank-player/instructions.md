# 78-tilt-bank-player

**Goal:** a spool's tilt sound is a **tilt bank**: one looping multichannel sound, one channel per
tilt angle, crossfaded by the tilt sensor and shaped by a few parameters. Changing the sound means
loading a different bank, not editing the patch. This is the engine for Kite Choir's
`spoolsynth` track and for its Stage 1 standalone tilt spools (no network).

**Status:** new (2026-10-16). Bob's idea, not yet ratified as the design. `1` is ready.
Kite Choir acceptance: brains stitch
`autonomous-fallback-composition/standalone-tilt-spoolsynth`.

## Bob, 2026-10-16

> "Thinking re spool sounds - multichannel wave file, for example 9 channels. Each channel is an
> angle on the tilt sensor. Middle channel is horizontal, first and last channels are full tilt left
> and right. Pd detects the number of channels in the sample, starts sample looping. Center channel
> fades out after a short time, parametise that decay, intensity of the crossfade between channels,
> and later an VCA envelope to give each angle an attack. Maybe later a dynamic filter. Then a spool
> preset is simply a wave file with some parameters for shaping it. Different spool sounds can
> accompany different movements. Various spool sounds can be active across the fleet at any one
> time. The cost is streaming those channels off the sd card."

Bob, same session: *"Might be a bopOS loom item more than a KC one."* That's why it lives here.

## Naming

Bob said "spool preset". bopOS **removed presets** on 2026-10-03 (`65-remove-presets`), so this
thread uses **tilt bank** so the old concept doesn't come back by name. Rename it if Bob prefers.

## The design as proposed, with notes

| Piece | Proposal | Note |
|---|---|---|
| Channels | N channels, centre = horizontal, 1 and N = full tilt | Channel count comes from the file, so banks can be 5, 9 or 15 angles |
| Playback | All channels stream together from one interleaved file | Keeps the angles in sync, so a crossfade between them never smears time |
| Crossfade | `width`: how many neighbouring angles sound at once | Small width steps between angles; large width blurs them. Equal-power or equal-gain is a per-bank choice, depending on how correlated the channels are |
| Centre decay | `centre_decay`: the horizontal channel fades out after it is reached | Matches the existing Kite Choir rule that a spool is **silent when horizontal** |
| Later | Per-angle VCA attack; dynamic filter | Not in this thread's first cut |

### Stream with readsf~ and hide the seams with fades (Bob, 2026-10-16)

An early version of this stitch proposed loading banks into RAM for gapless loops. Bob ruled
against that: *"I want to avoid loading in to ram. Would prefer adding subtle fades and using
readsf~. This is the strategy throughout."* That ruling is the Glean finding
`stream-audio-with-readsf`, and it applies to all of bopOS. `bop.stream~` already uses `readsf~`,
so start there.

- **Bandwidth is small.** 9 ch × 48 kHz × 16-bit is about 0.86 MB/s, well inside what an SD card
  reads. Expect two streams at once during a loop crossfade.
- **Looping:** `readsf~` leaves a gap when it reopens the file, so use two players and crossfade at
  the loop point. The same fade covers bank switches.
- **Channel count:** `readsf~` fixes its channel count when it's created. Create it for the largest
  bank allowed (`1` sets the limit) and leave the unused outputs silent.
- **Detecting the count:** `soundfiler` called with no arrays reads only the file header and
  reports the channel count (up to 64), without loading audio. Checked in the Pd 0.57 help file on
  2026-10-16; confirm on the fleet's Pd version.
- Because the whole loop is never in memory, loop length isn't limited by RAM.

### Things the idea doesn't yet say

- **Which axis.** Left/right is one axis of the LIS3DH. Is forward/back ignored, folded into the
  same angle, or kept for the later filter?
- **Calibration.** Where is "horizontal" on each unit, and what angle counts as "full tilt"? The
  sensor's mounting may not be level, so this is probably a per-unit zero offset plus a per-bank
  `max_angle`.
- **Tilt rate.** bopOS polls I/O at **10 Hz** by default. That's coarse for a played instrument.
  Smooth the gains with `line~` either way, and test whether 30–50 Hz feels better and costs little.
- **Jitter at angle boundaries.** Sensor noise near a boundary will keep re-triggering the later
  attack envelope. Add hysteresis before the attack goes in.
- **Decay is only at the centre.** A spool held still at 40° drones forever. That may be fine, but
  the alternative is an envelope driven by *movement* (angular speed), which keeps a still field
  quiet.
- **Fleet variation.** Give each spool a random start offset (`readsf~`'s `open` takes an onset) so
  50 spools on the same bank don't pulse together.

## How it fits the show model

A bank change can be an ordinary cue to the Generative-layer track: `/spoolsynth/play <bank-folder>`.
With no network, the spool boots into a default bank. Kite Choir authors banks against groups, so
different parts of the field can carry different banks at once. That covers "various spool sounds
across the fleet" without any new message.

## Done when

- A spool loads a tilt bank of any channel count and plays it from tilt, looping without a seam.
- The bank's parameters (at least `width`, `centre_decay`, `max_angle`) come from a file next to the
  audio, not from the patch.
- Loops and bank switches are smoothed by fades and don't click or drop out.
- The CPU and SD streaming budget on a Pi 3A+ is measured.
