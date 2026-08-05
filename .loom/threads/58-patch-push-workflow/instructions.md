# 58-patch-push-workflow

Make "push this patch to this device" a first-class, always-available operator
action, and make the pin a legible toggle rather than a side effect of the
Patch tab's deploy control.

Raised by Bob on 2026-08-05, from the incident recorded in
`incident-2026-08-05-ciro-toast.md` beside this file: *"there's currently no
'update patch' button on the device page. only 'pin to device' on the patch
page — which won't push if the device is already pinned. i think there are some
ux workflow niggles to smooth out there"*, and *"similarly a simpler
pin/unpin button to get the device to hold onto a patch would be part of that
ux sweep"*.

## What the incident actually exposed

Bob edited `patches/fire-button/main.pd` on the host and tried to push it to
Ciro Toast. He could not, and the device would not come up. Three separate
things were true at once, and they are separate stitches:

1. **The device was offline**, because its *stale* `bopos.patch.json` still used
   the retired `type`/`min`/`max` grammar and the pre-`4-cue-retirement` `cues`
   key. `bash/start-engine.sh:42-44` rejects the manifest, `bash/start.sh:18-25`
   traps the failure and runs `stop.sh` over the *whole* stack — including
   `bopos.py`. So the device vanished from the network, which is the one state
   in which patch distribution cannot repair it. Recovery required SSH. That is
   `4-invalid-manifest-lockout`.
2. **Every push affordance is gated on `online`**, and both of them disappear
   silently rather than saying why. The Patch tab's target `<select>` is built
   from `deployable` = seat-bound ∧ `online` ∧ ¬`virtual`
   (`dashboard/static/js/dashboard.js:526-530`), so an offline device is simply
   not in the list. The Device tab's remediation button additionally requires
   `d.online` (`dashboard.js:1145-1146`). That is `3-push-target-legibility`.
3. **There is no push action on the Device page at rest.** The button that
   would have done it — `Sync to pinned patch`, sending `retry_fleet_patch`,
   which `server.py:2756-2761` correctly routes to the device's *own* pin — only
   renders when `d.patch_badge ∈ {missing, stale, stale_unverified, mismatch,
   failed, timeout}`. That is `1-device-push-action`.

## A finding that narrows the scope, and must not be silently dropped

**"Pin to device won't push if the device is already pinned" is not what the
code does.** `set_device_patch` (`dashboard/server.py:680-697`) re-pins and
calls `converge_device_patch` unconditionally; nothing in
`fleetPatchPanel` (`dashboard.js:532-550`) disables the button for an
already-pinned target, and the option is merely annotated `· pinned`.
`converge_device_patch` (`server.py:2722-2754`) supersedes any in-flight
operation and re-stages regardless of the stored fingerprint.

The reported symptom is fully explained by (2) — Ciro Toast was **absent from
the target list entirely**, not present-and-inert. But this has not been
confirmed with Bob, and an unreproduced report is not a closed one: if the
button is ever pressed against a listed, pinned, online device and nothing
converges, that is a different bug in `converge_fleet_patch`'s generation
tracking and belongs in its own stitch. Whoever claims `1` should ask.

Related and verified working, so nobody re-derives it: the desired fingerprint
is **not** captured at pin time. `device_desired_patch` (`server.py:2263+`)
re-resolves it from the live host catalog on every broadcast, exactly as
`live_fleet_patch` does, so a host-side patch edit *does* move an online
device's badge to `stale`. The drift detection is sound; only the affordance
is missing.

## Shape of the work

Children, in queue order:

0. `5-fetch-tombstone-lockout` — **added later the same day and queued first.**
   A defect, not an affordance gap: an expired fetch leaves a permanent
   tombstone that silently blocks every future push to that device for the
   dashboard process's lifetime. It is why the second half of the 2026-08-05
   session also failed, with the device healthy and online. Ships alone.
1. `1-device-push-action` — an explicit, always-available "push the host's copy
   of this patch to this device" on the Device page.
2. `2-pin-unpin-toggle` — the pin as its own two-state control on the device,
   not an inference from which entry the Patch tab's deploy dropdown had
   selected.
3. `3-push-target-legibility` — when a device cannot be a push target, say so
   where the operator looks, instead of omitting it from a list.
4. `4-invalid-manifest-lockout` — node-side: a bad patch must not cost the
   device its OSC surface. Bash + hardware; independent of the three UI
   stitches and claimable in parallel.

`1`–`3` all touch the same two surfaces (`patchDiagnostics` /
`bindPatchDiagnostics` in `dashboard.js`, and `fleetPatchPanel`), so they are
ordered rather than parallel. None of them changes the wire: the verbs
`set_device_patch`, `clear_device_patch` and `retry_fleet_patch` already exist
and already do the right thing. **This sweep is an affordance and labelling
pass over verbs that ship today** — if a stitch finds itself widening the
server vocabulary, that is a signal to stop and re-read, not to proceed.

## Bob's gate

The Device tab is desktop operator chrome, not the facilitator/Remote view, so
this is not automatically a ratification gate. But `1` and `2` together decide
what the Device page's patch section *says* — button names, what is destructive
enough to confirm, and whether push and pin are one control or two. Put the
concrete proposal (with the shipped panel screenshotted, per `08`'s `shoot.py`
pattern of measuring rather than asserting) in front of Bob inside `1` before
implementing `2`.
