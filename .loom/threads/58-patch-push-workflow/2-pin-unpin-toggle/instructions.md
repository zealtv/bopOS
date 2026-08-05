# 2-pin-unpin-toggle

Make the pin a two-state control the operator can see and flip on the device —
*"a simpler pin/unpin button to get the device to hold onto a patch"* (Bob,
2026-08-05).

Depends on `1-device-push-action`'s ratified answer to "is pin the same control
as push, or a second one?". Do not start the implementation before that.

## Measured starting state

The pin is already a clean axis in the model. `server.py:2309-2313` publishes
`patch_pinned` and `pinned_patch` separately from `patch_badge`, with the
comment saying exactly why:

```python
# A device may be pinned to a patch other than the fleet default. The
# convergence badge (current/stale/…) measures against the *effective*
# desired target; the pin itself is a separate axis surfaced as
# patch_pinned so the roster can mark it without overloading the badge.
```

Both verbs exist and are symmetric: `set_device_patch` pins and converges
(`server.py:680-697`), `clear_device_patch` clears and actuates the return to
the fleet default on the device's own generation track (`server.py:698-706`).

The **UI** is where the symmetry is lost:

* **Pinning** happens on the *Patches* tab, as a side effect of the deploy
  control. `fleetPatchPanel` (`dashboard.js:532-550`) reuses one button whose
  label flips between `Deploy as fleet patch` and `Pin to device` depending on
  a target `<select>`, and whose confirm text is the only place the word "pin"
  is explained. Nothing on that tab tells you what is *currently* pinned beyond
  a `· pinned` suffix on the option and a count in `#fleet-patch-summary`.
* **Unpinning** happens on the *Device* tab, and is called something else:
  `Follow fleet patch` (`dashboard.js:1147`), rendering only when
  `d.patch_pinned && d.online`.
* The device's own state is a 📌 emoji marker with the explanation in a
  `title` attribute (`pinnedMarker`, `dashboard.js:489-493`) — *"Pinned to
  <name> — follow fleet to clear"*, which is documentation standing in for an
  affordance.

So the two halves of one toggle live on two tabs under two names, one of them
phrased as its consequence rather than its action.

## The change

One pin control on the Device page's patch section, showing the current state
and flipping it: pinned to `<patch>` ⇄ following the fleet patch. Pin sends
`set_device_patch` with the effective desired patch name (which is what the
panel already displays as `Desired patch`); unpin sends `clear_device_patch`.

Two things to settle in the doing, both of which the model already supports so
neither is a wire question:

* **What does "pin" pin to, when the device is currently following the fleet?**
  The honest answer is "the patch it is running now", which makes the toggle
  mean *hold this*. That is Bob's phrasing — "get the device to hold onto a
  patch" — and it wants no patch picker.
* **Does pinning re-converge?** `set_device_patch` always calls
  `converge_device_patch`, so pinning the patch a device is already running
  restarts its engine for no content change. If the toggle is to be a cheap,
  safe click, that is the wrong behaviour for the *hold this* case, and the fix
  belongs on the server: skip convergence when the stored override resolves to
  the same name and fingerprint the device already reports. Guard it — a
  "no-op" that silently skips a genuinely needed push is the worse failure, so
  the condition must be fingerprint equality, never name equality alone.

The Patches tab keeps `Pin to device`; it is the right place to pin a
*different* patch than the one running, which is a deploy, not a hold. This
stitch adds the device-local hold/release and makes the two consistent in
wording. Leaving both is deliberate — say so in `decisions.md` rather than
letting a later reader think it was missed.

## Verification

Extend `tests/verify_device_patch_targeting.py`:

* an unpinned online device shows the control in its "following fleet" state;
  clicking it sends `set_device_patch` and the state inverts on the next
  broadcast;
* clicking again sends `clear_device_patch`;
* the pin state survives a reload (it is durable server state, so this is a
  cheap assertion and it pins the axis separation from `patch_badge`);
* if the no-op-convergence guard lands: pinning a device already running that
  exact fingerprint does **not** produce an engine restart, and pinning one
  running a different fingerprint does.

Playwright gotcha 12 applies — a `data-uid` is not unique across the Devices
and Seats rosters; scope roster clicks to `#device-roster`.
