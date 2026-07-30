# Decision

The persistent Device-enabled replay is real production behavior, not a missing
output-safety feature. `OSCBridge.handle()` has replayed
`state.device_enabled_for(uid)` whenever a physical device first appears or
returns from offline since `5eda7b4`.

The red was an environment-dependent test fake introduced by promotion:
`tests/test_device_control_routing.py` replaced only `bridge.sender`. The later
macOS routing change `54ff063` discovers the source route from a physical
heartbeat and may create `bridge.lan_sender`; on a host where the documentation
address is routable, that bypassed the recorder and left its frame list empty.
On a host where source discovery fails, the same test passed.

The fake now forces successful LAN-source discovery and routes every sender
created by the bridge back through the recorder. This exercises the dedicated
LAN-sender selection deterministically while retaining the original exact
`enabled 0` safety assertion.

## UI accordion check

The living accordion coverage is already appropriately placed in
`tests/verify_control_surface_component.py`. Its focused browser journey covers:

- open-by-default `<details>` / `<summary>` structure;
- 12 px child indentation and `▾` / `▸` disclosure glyphs;
- collapse by click;
- persistence across a heartbeat re-render and page reload;
- the exact scope + branch-path storage key;
- reopening and clearing the stored collapse.

No duplicate test was added.

---

## Note for anyone who comes across this again (2026-07-30)

**This is resolved. If you see it red, you are on a host where the fix is not
in your tree — not looking at a live bug.** Confirmed green on 2026-07-30:
green standalone, green in `tools/run-tests.sh fast` (250 tests), fix landed
in `e9e25cc` "Make device replay test route-independent" (2026-07-27).

The reason it deserves a note rather than silence: **this failure is
host-dependent, so "I reproduced it" and "I couldn't reproduce it" are both
expectable and neither settles anything.** Before the fix, the test passed or
failed according to whether the *machine* could route to the documentation
address `192.0.2.1`. `54ff063` made the bridge discover its source route from a
physical heartbeat and, when discovery succeeds, create a separate
`bridge.lan_sender`. The promoted fake replaced only `bridge.sender`, so on a
routable host the replay went out through a sender the recorder never saw and
the frame list came back empty. On a host where discovery failed, the original
`sender` was used and the same test passed.

Two things follow, both worth carrying beyond this stitch:

1. **A fake that stubs one sender is not a fake of a bridge that may create
   more.** The repair forces successful LAN-source discovery and routes every
   sender the bridge creates back through the recorder, so the dedicated
   LAN-sender path is exercised deterministically rather than incidentally.
2. **The exact `enabled 0` assertion was never weakened.** A disabled device
   that drops off and returns must not come back with output live; that
   behaviour is real and has been in `OSCBridge.handle()` since `5eda7b4`. If
   this test ever goes red again, suspect the harness first — but verify the
   production path before touching the assertion.

**CLAUDE.md was stale until 2026-07-30**, still listing this as "the one red
test in `tools/run-tests.sh fast`" three days after it was fixed. That stale
line is what sent a later session looking for a bug that no longer existed.
Corrected there now. `47-live-param-kinds-flake` is the genuinely open one —
intermittent, under full-suite load only, and it happened to pass in the
2026-07-30 run, which proves nothing either way.
