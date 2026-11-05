# 4-pd-reference-patches

**Status:** Bob's. Agents never edit `.pd` files. Bob asked for this stitch on
2026-11-04, in chat.
**Goal:** the Pd reference patches show how to capture keys and the mouse,
so a composer can copy a working example.

## Where it goes

**The template is the must** (Bob, 2026-11-05): *"i want to make sure io keys
is referenced in the pd template that feeds a new patch"*. The Patches tab's
New patch copies `patches/.templates/bopos-template.pd` verbatim
(`dashboard/server.py` `PATCH_TEMPLATE`), so every new patch starts with the
example. The demo patch is a nice-to-have.

- `patches/.templates/bopos-template.pd`: a **keys and mouse** section next
  to the existing `i2c io` section (canvas header at about y 779,
  `[r bopos-io]` at about 41 886).
- `patches/demo-pd/main.pd`: the same idea, or something that plays.
  Bob's working copy of this file had uncommitted edits when this stitch was
  written (`git status`, 2026-11-04).

## What reaches the patch

The bridge sends `/io/key` and `/io/mouse` to port 6662. `pd/bopos~.pd` runs
it through `[oscparse] → [list trim] → [s bopos-io]` without stripping
anything, so the `io` stays at the front. That differs from I2C peripherals,
which arrive under their own name (`adc …`). Checked in Pd 0.55 `-nogui` on
2026-11-04 with a scratch patch.

```
[r bopos-io]
|
[route io]
|
[route key mouse]
|                 \
[route up down left right space w a s d f g]   [route left right xy move wheel]
```

- Keys: `key <name> <1|0>`, with autorepeat already removed. Number-row keys
  arrive as `key_1` … `key_0`, so use `[route key_1]`, not `[route 1]`.
- Mouse buttons: `mouse left|right|middle <1|0>`.
- Pointer: `mouse xy <x> <y>`, each value 0 to 1 from the top-left. Also
  `mouse move <dx> <dy>` (raw counts) and `mouse wheel <steps>`.
- The Makey Makey defaults to: front, `up down left right space` and the
  left click; back header, `w a s d f g`; back header mouse pins, `move` and
  `xy`.

## Verify (no hardware needed)

1. Use Patch Edit with input set to *simulated*. In the Modules tab's
   **key · mouse** panel, click the `space` and `w` pads, type `1` in "Type
   keys", click "left click", and drag the XY pad. The patch's prints or
   number boxes should follow.
2. Alternatively, on a node or with a local engine, run
   `python3 tools/iosim.py --key space`, `--click left` and
   `--xy 0.25,0.75`.
3. Make a new patch from the template (the Patches tab's **New patch**).
   Check that the section comes through and that the existing `i2c io`
   example still works.

## Afterwards (agent)

`docs/COMPOSING.md` line 116 describes `bopos-io` as "sensor data, if you use
I2C peripherals". Once the patches show keys and the mouse, widen that line
to cover them too. That is a doc change, so an agent can make it.
