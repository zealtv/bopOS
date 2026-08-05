# 3-push-target-legibility

When a device cannot receive a patch, say so where the operator is looking.
Today it is silently omitted from a dropdown, which is indistinguishable from
the dashboard having forgotten it exists.

## Measured starting state

`dashboard/static/js/dashboard.js:526-530`:

```js
const deployable=Object.values(installation.seats||{}).map(occupant)
  .filter(device=>device&&device.online&&!device.virtual);
if (fleetPatchTarget!=="all" && !deployable.some(device=>device.uid===fleetPatchTarget)) fleetPatchTarget="all";
target.innerHTML=[`<option value="all" …>Whole fleet</option>`]
  .concat(deployable.map(device=>`<option …>${…}${device.patch_pinned?" · pinned":""}</option>`)).join("");
```

Three exclusions, none of them stated: not seat-bound (it is never an
`occupant`), offline, or virtual. And the second line **silently resets a
chosen target back to `all`** when the device drops out of the list — so a
device that goes offline mid-selection takes the operator's aim with it, and
the next press deploys to the whole fleet.

This is what Bob hit on 2026-08-05: Ciro Toast was crash-looping, so it was
absent, and "pin to device won't push" was the reasonable conclusion to draw
from a dropdown that simply did not contain it (see the incident note beside
the goal instructions).

The Device tab has the same gap in the other direction. `patchDiagnostics`
does explain the *unbound* case well — `unboundNote` at `dashboard.js:1151-1152`
is a good model for the voice to use:

> Assign this device to a Seat before syncing content. OSC v1.5 does not
> UID-target patch distribution or switching.

— but the *offline* case is unexplained: `d.online` just removes the buttons
(`dashboard.js:1145-1153`). The panel keeps rendering the fingerprint table and
badge, so the operator sees plenty of information and no way to act on it.

## The change

* **The deploy target list names its exclusions.** Ineligible devices appear
  as disabled options carrying the reason (`offline`, `unassigned`,
  `simulated`), rather than vanishing. This is the shape the Assets tab's
  device picker already uses — showing ineligible devices with reasons is the
  exact quality `09-patches-deploy-row` cited when it decided the Assets
  `TargetPicker` earned its size. Do **not** mount `TargetPicker` here: `09`
  measured it at 51px closed against the row's 37px and ruled it out on
  geometry, and that ruling stands.
* **A selected target that becomes ineligible is not silently re-aimed.** Keep
  the selection and disable the button with the reason, or state the reset
  where the operator can see it. Silently switching the target of a fleet-wide
  destructive action is the sharp edge here, not the missing entry.
* **The Device page states why it cannot push**, in `unboundNote`'s voice,
  covering offline and virtual as well as unbound. `1-device-push-action`
  renders the disabled control; this stitch owns the sentence beside it.

## Verification

Extend `tests/verify_device_patch_targeting.py`. The suite can produce a real
offline device: the offline sweep marks a device down 30 s after its last
heartbeat, so gotcha 14 applies — a test that kills simfleet and waits for
`online === false` needs a timeout longer than 30 s. Prefer driving the state
directly if a fixture allows it, and only fall back to the wait if not.

Assert on the *reason text*, not just on the option count — the failure this
stitch exists to prevent is an operator reading absence as absence of the
device, so a test that only counts entries would pass on a list of unlabelled
disabled options.
