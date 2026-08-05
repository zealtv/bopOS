# Terminal session, 2026-08-05 — bringing up an ADS1115 on Ciro Toast

Bob was trying to confirm button presses from an ADS1115 breakout on Ciro
Toast and did it in a terminal, deliberately, to see what the Device tab
should offer. This is the record of what the terminal workflow actually was.
It is the design input for this thread.

## What was wrong

`patches/fire-button/main.pd` carries, as a click-me message box:

```
io create adc ads1015 0x48
```

Both arguments are wrong for the hardware attached:

- **Address.** `i2cdetect -y 1` reports `0x1a` and `0x4b`. Nothing answers at
  `0x48`. `0x4b` is an ADS1x15 with ADDR strapped to SCL; confirmed by
  `i2cget -y 1 0x4b 0x01 w` → `0x8385`, which byte-swapped is `0x8583`, the
  chip's power-on config default.
- **Type.** The board is an ADS1115; `ads1015` selects a different module
  (`python/io/io_ads1015.py`).

Neither error was visible anywhere. `io/main.py` replies `/io/error adc
create-failed` — to `127.0.0.1:6662`, the engine, where nothing in the patch
routes it. **The operator's only symptom is silence**, which is
indistinguishable from a wiring fault, a dead chip, or a patch that never sent
the create at all.

## The four moves the terminal workflow needed

1. **Scan the bus** — `i2cdetect -y 1`. Answers "is anything there, and at
   what address". This is what `1-scan-transport` already covers.
2. **Confirm the address is the chip you think it is** — a register read.
   Discovery gives an address, not an identity; `0x4b` vs `0x1a` was only
   resolvable by knowing what an ADS1x15's config register reads at reset.
3. **Instantiate the peripheral** — `/io/create <name> <type> <addr>`, and
   **see whether it worked**. Today this is authored into the patch as a
   hardcoded message box and its failure is invisible.
4. **Watch the inputs while pressing the button.** This is the step that
   actually answered Bob's question, and its shape matters (below).

## The finding that shapes the design: step 4 must not stream

The script that worked sampled all four channels at 50 Hz **on the device**
for a fixed 90 s window and returned one summary:

```
--- 90s window, 21 edge(s)
A0  rest 3.245  min -0.001  max 3.253  swing 3.254  <== MOVED
A1  rest 0.001  min  0.000  max 3.289  swing 3.288  <== MOVED
A2  rest 3.248  min -0.001  max 3.256  swing 3.257  <== MOVED
A3  rest 3.282  min  3.281  max 3.289  swing 0.008
```

plus a timestamped line per edge. That is the right shape for three reasons:

- **It answers the question asked.** "Am I getting button presses" is a
  question about a 90-second window, not about this instant. A live needle
  requires the operator to watch and press simultaneously and proves nothing
  about the press they missed.
- **It survives the contract.** §6 says in as many words that there is **no
  streamed telemetry and no framework meter plane** — `meter_loop`, the `/rpt`
  echo chain and `role: "meter"` were deleted, not renamed, and the *leased*
  probe (`… <hz> <ttl>`) was proposed at the v1.2 ratification and
  deliberately declined. A bounded capture returning one summary needs none of
  that reopened.
- **It caught something a needle would not have.** A1 rests at 0 V and rises;
  A0/A2 rest at rail and fall. The rest-value column made the inversion
  obvious. A live readout would have shown three numbers changing and left the
  operator to notice.

An extra-credit live readout is not forbidden, but it is a separate,
Bob-gated argument. **The bounded window is the feature.**

## Transport, re-decided in light of this

`1-scan-transport` was written weighing "`bopos.py` scans directly" against
"relay to the io bridge". The scan alone could go either way — the bus was
free here. But moves 3 and 4 **must** go through `io/main.py`: it owns the
peripheral registry, it is the process holding the chip open, and two
processes driving one ADS1115 is a bus-contention problem nobody should
invent. So the relay is needed regardless, and building it once in `1` is
cheaper than building it in `1`'s style and then again in `3`'s.

The concrete obstacle, measured: `io/main.py:40-41` creates **one** OSC client,
hardcoded to `127.0.0.1:6662`, at construction. Every reply it has —
`/io/scan`, `/io/error`, peripheral bundles — goes there and nowhere else. A
relay therefore needs a reply route back to `bopos.py`, not just a request
route in.

## Second half of the session: the patch, and where the chain really broke

Bob then built the patch and reported no audio from button presses, with no
visibility into which hop was failing. Bisected on the device:

**The I2C half works, end to end.** With the bridge relaunched as
`python -u main.py > /tmp/io.log` and sent `/io/create adc ads1115 0x4b`:

```
  adc: 4-channel ADC ready
✓ Created adc (ads1115 @ 0x4B)
```

It then polls at 10 Hz and sends `/adc <4 floats>` to `127.0.0.1:6662`, where
`pd/bopos~.pd:28` (`netreceive -u -b 6662` → `oscparse` → `s bopos-io`)
delivers it to the patch's `[r bopos-io]` → `[route adc]`. Nothing in that
path was broken.

**The MIDI half does not exist.** Three stacked reasons, any one sufficient:

1. `patches/fire-button/main.pd` has **no `noteout`**. The chain ends
   `[makenote 127 500]` → `[pack]` and stops. `grep -n
   "noteout\|midiout\|ctlout"` on the patch returns nothing.
2. **PD has no ALSA MIDI client.** `aconnect -l` on the node lists only
   `System` and `Midi Through` — no `Pure Data`. `start-engine.sh:143` launches
   `pd -nogui -jack …` with no MIDI flags.
3. **No MIDI hardware is attached.** `lsusb` shows two root hubs and a VIA
   Labs hub; `amidi -l` finds no device. The Casio is not on this Pi.

So the audible test Bob chose to prove the I2C chain was itself the broken
part, and it was failing for reasons entirely unrelated to I2C. **That is the
generalisable lesson for this thread**: he had no way to observe any
intermediate hop, so the one signal available — silence at the far end — was
attributed to the hop he was actually working on. Every stitch here is
ultimately about making the hops individually observable.

## `tools/iosim.py`

Written in this session and used to prove the split. The bridge's output is
just OSC on a known localhost port, so nothing privileged is required to
reproduce it: `iosim.py` sends the same `/adc` bundles at the same rate,
which means a patch can be developed against simulated button presses on a
laptop with no bus, no chip and no bridge — and on a real node it can inject a
press alongside the running bridge, separating "is the patch wrong" from "is
the sensor wrong" in one move.

It is a developer tool, not a dashboard feature, but its existence changes
`4-sensor-test-window`'s job: the device-side capture answers *"is the sensor
producing values"*, and `iosim` answers *"does the patch respond to values"*.
Those are the two halves, and neither substitutes for the other.

## Operational finding: an I2C wedge needs a COLD power cycle

Late in the session the bus died on Ciro Toast: `i2cdetect` crawled and
reported nothing, and both the Argon fan hat at `0x1a` and the ADS at `0x4b`
vanished together. `pinctrl get 2,3` showed **SCL held low, then both lines
low**, with pull-ups enabled and no process holding `/dev/i2c-1`.

**Two warm `reboot`s did not clear it. A full power-down did, immediately.**

The mechanism is the stack: Pi → Qwiic shim → Argon fan hat → Pimoroni Audio
DAC SHIM. The fan hat has its own MCU on the bus at `0x1a`, and a `reboot`
never drops the 3V3 rail, so a latched peripheral stays latched across it.
Only removing power resets it.

Worth knowing for any node with this stack: **if the I2C bus wedges, `reboot`
is not a remedy and its failure tells you nothing.** Pull the power for ~30 s.
`rmmod i2c_bcm2835` is also not available as a fallback — the adapter is held
(refcount 1 with no dependent modules) and unloading it would not release an
externally-held line anyway.

Two methodology notes, both mistakes made here:

- **Measure a healthy baseline before reading meaning into pin states.**
  GPIO4 reads `ip pu | lo` on this stack *normally* — it still does with the
  bus fully working — but with no baseline it looked like a third anomalous
  pin, and together with GPIO2/3 it suggested a mechanical short across three
  adjacent header pins. That story was wrong, and it was wrong in the
  direction of sending someone to disassemble hardware.
- **"It broke across a reboot" is not evidence that the reboot is innocent.**
  The first reading of the timeline here was that a reboot had failed to fix a
  pre-existing fault; in fact the wedge arrived with that boot and the previous
  boot had been healthy. Those two readings recommend opposite actions.

## Evidence

- `ads.py` / `watch.py` beside this file are the scripts that ran.
- Bus: `0x1a`, `0x4b` on `/dev/i2c-1`. `/dev/i2c-20` and `/dev/i2c-21` also
  exist (HDMI DDC), which is why the scan must stay pinned to bus 1 or take
  the bus as an argument.
- `/home/pi/venv` has `adafruit_ads1x15`; the io modules' imports are
  satisfied on a real node.
