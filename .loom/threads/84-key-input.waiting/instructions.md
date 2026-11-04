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

## Open for Bob

- Contract text: §11 currently says the engine owns HID. The amendment
  (draft in `proposal.md`) moves key input to the framework. Wire and
  contract wording are Bob's to ratify (glean `decision-gates`).
- Key naming (`proposal.md` §2).
- Hardware check: a real Makey Makey on a rig device, keys arriving in Pd.
