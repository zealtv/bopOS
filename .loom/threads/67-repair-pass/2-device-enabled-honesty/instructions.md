# 2-device-enabled-honesty

**Status:** ready · software fix plus a rig check
**Goal:** Device enabled never reports "disabled" while the device is still
making sound.

## The bug (likely)

`set_device_enabled` (`python/bopos.py`) persists the new state before
`enforce_mute`. When no mixer control works it sends no receipt (deliberate,
tested), but the state stays changed, so the next `/os/report` says
`output_enabled: false` and the dashboard shows "current". HiFiBerry boards have
no hardware mixer (`glean:test-rig`) — Ciro Toast may be a real case.

## Do

- First confirm on Ciro Toast: disable it from the Device page; is it silent?
  Record which half ran (`glean:hardware-claims`).
- Report what the mixer actually did, not the intent. Decide what a failed
  disable should leave persisted.
- If HiFiBerry can't be muted by mixer, say what the honest UI is (e.g. "can't
  disable on this card"). Bob decides anything operator-visible; a new fallback
  like stopping the engine needs his ruling (he ruled against it 2026-07-23 —
  see the `enforce_mute` docstring).

## Done when

- Test: mute fails → report doesn't claim output disabled.
- Rig result recorded, or explicitly not claimed.
