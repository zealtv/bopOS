# Hardware sketch — small, cheap, flexible

Bob's second half of the question: *"we'd still need an audio amp and power. but
would be good to think about how to make something like this that could be
small, cheap, and flexible."*

**Everything in this file is asserted from general knowledge. Nothing was
measured, no part was in the room, and prices move.** It is a starting point for
a bench build, not evidence.

## The core

**ESP32-S3-WROOM-1-N16R8** — 16MB flash, 8MB octal PSRAM, dual Xtensa LX7 at
240MHz, 512KB internal SRAM, 2.4GHz WiFi b/g/n only.

The PSRAM variant is not optional for this application, and the reason is
architectural rather than a matter of headroom — see "storage" below.

Two things the S3 specifically does **not** have, both of which the original
ESP32 did, and both of which catch people out:

- **No built-in DAC.** The classic ESP32's two 8-bit DACs are gone. Audio out
  is I2S to an external part, which is better anyway.
- **No Ethernet MAC.** Wired networking needs an SPI MAC+PHY (W5500, DM9051).
  This matters more than it sounds — see "network" below.

## Output stage — the flexibility hinge

The right move is to make the output stage **a swappable board against a fixed
core**, because the three deployment shapes want genuinely different things and
the core is identical for all of them.

| shape | part | notes |
|---|---|---|
| **self-contained speaker node** | MAX98357A | I2S in, class-D out, ~3.2W into 4Ω at 5V. One chip, no separate DAC. Mono — use two for stereo (the channel is pin/resistor-selected). Cheapest and smallest possible node |
| **line out to existing amps** | PCM5102A | I2S → line level, no MCLK needed. Feeds whatever Bob already owns. Two chips, more flexible |
| **loud** | PCM5102A → TPA3116D2 | class-D in the tens of watts; now you are designing a power supply, not a node |

**The amp's shutdown pin is the output gate.** MAX98357A has `SD`; most class-D
parts have an equivalent. Wire it to a GPIO and contract §6's *"transport-level
kill enforced below patch logic"* becomes literally true in hardware. This is
better than the Pi's story: the 2026-08-05 investigation found
`amixer -c sndrpihifiberry scontrols` is **empty** on HiFiBerry DAC boards, so
that fleet's gate is entirely software.

**Multi-channel, and its link to `62-split-elements`.** I2S is natively stereo,
but the S3's I2S peripheral supports **TDM** with many slots. A multichannel
codec on TDM would give one box 4–8 positioned outputs. That is exactly the
shape `62-split-elements` is about — *"a device runs one engine instance per
element, each taking its own Seat"* — and it is worth knowing the cheap node can
pose that question too, rather than only the expensive one. Contract §5 already
allows it: *"a many-output computer IDs as many elements as it drives."*

## Storage

**SD via SDMMC 4-bit, not USB.** The S3's USB-OTG is **Full Speed only**
(12 Mbit ≈ 1.5 MB/s ceiling), it consumes the USB peripheral you may want for
flashing and serial, and MSC hot-plug robustness is worse. SDMMC 4-bit is
several times faster, cheaper, and its failure mode (card falls out) is the same
one.

But for a **trigger layer specifically, the right architecture takes the card
out of the realtime path entirely**: preload one-shots into PSRAM at boot. 8MB
of PSRAM is roughly 90 seconds of 16-bit 44.1k mono, or ~45s stereo — a lot of
one-shots. Mixing 16 voices of 16-bit is nothing on a 240MHz dual-core with one
core free. The card then matters only at boot and at fetch time.

This is why the PSRAM part number is load-bearing, and it is also what makes the
restricted feature set honest rather than merely reduced: a node that only fires
short samples never needs to stream, and never needs to stream is a very
different engineering problem from needs-to-stream-reliably.

USB only earns its place if hot-swap-by-a-non-technician is a real venue
requirement. Worth asking, not assuming.

## Power, and the PoE thought

A single 5V rail runs everything: the S3 (~100–150mA average with WiFi up,
bursting toward 350mA on transmit, at 3.3V behind a regulator) plus the amp
(a MAX98357A at full 3.2W output peaks around 1A at 5V). Call it 5V/2A per node,
~10W worst case, far less idle.

**802.3af PoE is worth serious thought for an installation**, and not mainly for
the power:

- One cable per node for power *and* network. In a venue, cable count is the
  install-day cost.
- ~13W at the powered device — comfortably enough.
- **It sidesteps the broadcast problem completely.** `feasibility.md` §5 flags
  WiFi power-save dropping the broadcast frames that `/e/*`, `/pt`, `/os/mute`
  and `/sync/ping` all ride on. Wired multicast has none of that, and sync over
  wire is better than sync over 2.4GHz by a margin that matters for a trigger
  node.

The cost is the missing EMAC: wired means an SPI W5500 or DM9051, practically
~8–10 Mbit, which is plenty for OSC but is another chip, another driver, and a
second network path for `bopos.py`'s Pi-side equivalent logic to not know about.

**This is a genuine fork, not a detail.** A PoE trigger node and a WiFi trigger
node are different products with different failure modes. Worth deciding early
rather than discovering.

## Cost and size, very roughly

Order-of-magnitude only, module quantities, no enclosure or speaker:

- S3 module: a few dollars bare, ~$6–10 as a dev board
- MAX98357A: ~$1–2
- SD socket, passives, PCB: a few dollars
- PSU or PoE splitter: the swing factor

So something like **$15–25 a node** against a Pi node's $40–70 once you count
card, PSU and DAC hat. Physically it is a matchbox rather than a paperback, and
it boots in under a second instead of ~25.

At that price the interesting consequence is not saving money on a 12-node
piece. It is that **a 60-node piece becomes affordable**, which is a different
compositional proposition — and it is the argument that would actually justify
building this.

## What to do first, if it is ever picked up

A bench test answering three questions, before any bopOS code is written:

1. Does `esp_wifi_set_ps(WIFI_PS_NONE)` give reliable broadcast reception with
   a `/pt`-rate stream running? (This is the risk that kills the idea.)
2. What is the real jitter, box-to-box, on a scheduled fire against a shared
   clock? Measure it against **two Pis doing the same thing**, which has itself
   never been measured (see `feasibility.md` §2).
3. How many voices from PSRAM before the mixer or the I2S underruns?

None of those needs the contract implemented. All three are cheap. If any of
them fails, nothing else matters.
