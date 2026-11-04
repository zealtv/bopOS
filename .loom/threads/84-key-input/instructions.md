# 84-key-input

**Goal:** USB keyboard-like devices (a Makey Makey first) reach the engine on a
headless node as `/io/key <key> <1|0>`.

## Bob's rulings, 2026-11-04 (in session, in chat)

- **Always on.** The IO bridge (`python/io/main.py`) reads keys whenever it
  runs; nothing has to create or declare it.
- **Generic, not Makey-specific:** `/io/key` is the standard for any key input.
- **Wire shape:** `/io/key <key> <1|0>`, key name as the first value (the
  bridge README's one-segment-address rule), not `/io/key/<key>`.
- **Out of the manifest:** no `io_modules` declaration, no Device-tab module.

## Why the bridge, not Pd

`start-engine.sh` launches Pd `-nogui`, so `[key]`/`[keyup]` get nothing, and
with no desktop the kernel hands keystrokes to the tty1 login prompt. The
bridge reads `/dev/input` (evdev) directly and grabs the device.

## Ratified, 2026-11-04 (Bob, in session, in chat)

- Contract amendment moving keyboard and mouse into the framework: "sounds
  good" → v1.24 (`1-input-contract`).
- Key names as proposed (`key_1` etc.): "sounds good".
- Mouse motion unthrottled "at this stage".
- Simulator: **option A**, a Patch Edit panel (`2-input-sim-panel`).
- Hardware test: Bob's, "shortly" (`3-input-hardware-check`).

The 2000-count virtual pointer span stays the agent's estimate; Bob didn't
rule on it.

## Stitches

1. `1-input-contract`: §2, §11 and §15 of the contract, version 1.24.
2. `2-input-sim-panel`: the "key · mouse" simulated panel in Patch Edit.
3. `3-input-hardware-check`: a Makey Makey on the rig (Bob).
