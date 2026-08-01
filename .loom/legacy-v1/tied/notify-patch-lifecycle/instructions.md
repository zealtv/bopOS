# notify-patch-lifecycle

**Goal:** close the `/notify` gap so a running patch can give audible feedback
when its own patch is about to be swapped out — the same way it already can for
shutdown / reboot / update-bopos / restart-engine / identify.

## Why

`/notify` exists so a patch can react to framework lifecycle actions (Bob's
use: a helpful audible blip when an action is undertaken). Today
`bopos.py` emits `/notify` for six actions but **not** for the patch-lifecycle
ones. Confirmed 2026-07-17 (surfaced while scanning `patches/.templates/
bopos-template.pd`, built on the merged `pd/bopos~.pd`):

| action | callback | emits `/notify`? |
|---|---|---|
| identify | `identify` | ✅ `identify` |
| update-bopos | `update_bopos_callback` | ✅ `updatebopos` |
| checkout | `checkout_callback` | ✅ `checkout` |
| restart-engine | `restart_engine_callback` | ✅ `restart-engine` |
| shutdown | `shutdown_callback` | ✅ `shutdown` |
| reboot | `reboot_callback` | ✅ `reboot` |
| **update-patch** (`/os/pullpatch`, engine `/admin update-patch`) | `pull_active_patch_callback` | ❌ none |
| **patch switch** (`/os/patch`) | `switch_patch_callback` | ❌ none |

Both patch-lifecycle callbacks end by running `bash/stop-engine.sh` →
`start-engine.sh`, which tears the engine down — so, exactly like the working
cases, the notify must be sent **before** the stop so the patch gets its
window to blip. The six working callbacks are the pattern to copy
(`msg = OSCMessage("/notify"); msg.append(<event>, 's'); send_to_engine(msg)`
at the top of the callback, before any teardown).

## Event symbol — `updatepatch` (ratified Bob, 2026-07-17)

Both patch-lifecycle callbacks emit the **same** symbol `updatepatch` — a patch
switch and a patch update are indistinguishable to the patch (both mean "you
are about to be replaced"). `updatepatch` matches the existing `updatebopos`
style (no hyphen) for wire consistency. This is the stable symbol patch authors
`route` on.

## Do

1. In `python/bopos.py`, emit `/notify updatepatch` at the top of
   `pull_active_patch_callback` and `switch_patch_callback`, before the
   stop/swap, mirroring `shutdown_callback`/`reboot_callback`
   (`msg = OSCMessage("/notify"); msg.append("updatepatch", 's');
   send_to_engine(msg)`).
2. This is a `bopos.py` change only — **do not edit `.pd` files** (house rule).
   Note in the tie that the reference template's `bopos-notify` route should
   key on `updatepatch`; the actual `.pd` edit is Bob's.

## Verify

- No hardware needed. Drive `pull_active_patch_callback` /
  `switch_patch_callback` and assert a `/notify updatepatch` reaches the engine
  port **before** stop-engine runs (a browser-free engine-surface check; see
  `docs/VERIFICATION.md`). Confirm the six existing notify events are
  unchanged.

## Done when

update-patch and patch-switch each send `/notify updatepatch` before teardown,
and a verify artifact in this stitch shows the ordering (notify precedes stop).
