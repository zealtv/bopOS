# 5-device-input-forwarding

**Asked:** Bob, 2026-11-04, in chat, after Theo River's Makey Makey reached
its own engine but not Patch Edit: "Since the option is in the dropdown
already, we probably want to implement it."

## Rulings (Bob, 2026-11-04, in chat)

- Contract change: "the contract change is okay in this specific instance"
  → v1.25. Keys and pointers may ride the leased development stream.
- "throttle the mouse movement for only when it's forwarding": `xy`/`move`
  are held to one report per poll tick on the forwarded copy. The engine's
  own copy stays unthrottled.

## Built

- `python/io/main.py`: while the stream lease is active, `forward_input()`
  copies each key and button into the stream (via bopos.py on 7771) as a
  one-message bundle. Pointer motion waits for `flush_motion()`, which runs
  once per poll loop: `move` is summed and `xy` keeps the latest. Motion
  queued before a click is sent ahead of it.
- `python/io_stream.py` `decode_bundle()` accepts `/io/key` and `/io/mouse`
  rows, so the node's stream check lets them through.
- `dashboard/io_streams.py` keeps input rows out of module values, so the
  Monitor's module panels never see them.
- `dashboard/editor_input.py` `forward()` still passes bundles unchanged. It
  now notes held keys and buttons from the device; `clear()` (source change,
  leaving Patch Edit, the selecting connection going) and the dashboard's
  offline sweep release them.
- Contract v1.25 (§11 and §15), `osc_contract.VERSION`, `python/io/README.md`,
  and glean `osc-contract`.

Hardware: step 8 in `3-input-hardware-check`.
