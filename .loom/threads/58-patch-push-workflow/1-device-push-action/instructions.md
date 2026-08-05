# 1-device-push-action

Give the Device page an explicit "push this patch to this device" action that
is available whenever the device can receive one — not only when the dashboard
has already decided something is wrong.

Read the goal instructions first, particularly the finding about
`set_device_patch` already re-converging. **No new wire verb is needed.**

## Measured starting state

`dashboard/static/js/dashboard.js:1145-1146`:

```js
const remediation=allowRemediation&&d.online&&["missing","stale","stale_unverified","mismatch","failed","timeout"].includes(d.patch_badge)
  ? `<button id="fleet-patch-retry">Sync to ${d.patch_pinned?'pinned':'fleet'} patch</button>`:"";
```

Bound at `dashboard.js:1158-1159` to `ws.send("retry_fleet_patch",{uid})`.
Server side (`dashboard/server.py:2756-2761`) that verb already does exactly
what this stitch wants:

```python
async def retry_fleet_patch(self, uid, ws):
    # A pinned device (thread 37) retries its own pin, not the fleet patch.
    override = self.state.device_patch_for(uid)
    if override:
        await self.converge_device_patch(uid, override["name"], ws)
        return
```

So the capability ships. Three things keep it from being usable:

1. **It is conditional on a fault badge.** A device whose badge reads `current`
   has no button, and `current` is what you get when the fingerprints agree —
   which is most of the time, including immediately after a push attempt that
   never left the host.
2. **It is named after the mechanism, not the intent** — "Sync to fleet patch"
   is the dashboard's word for convergence. Bob's word is *update patch*.
3. **It reads as remediation.** It sits in `.actions.patch-remediation` beside
   `Pull latest` and `Follow fleet patch`, so it presents as something you do
   when the panel is complaining.

`allowRemediation` is the seat-bound test; keep it. OSC v1.5 cannot uniquely
target unbound content operations and `converge_device_patch` refuses
(`server.py:2730-2735`) — the unbound case is `3-push-target-legibility`'s
to explain, not this stitch's to bypass.

## The change

An always-rendered push action in the Patch diagnostics section, enabled when
the device is seat-bound, online and non-virtual, disabled with a stated reason
otherwise (the reason text is `3`'s; a `title`/`disabled` pair is enough here).

The action sends `retry_fleet_patch` — it pushes the **effective desired**
patch, which is the pin if there is one and the fleet patch otherwise, matching
what the panel's `Desired patch` row already displays. It must not make the
operator re-choose a patch: choosing is the Patch tab's job, and the Device
page's job is "make this device match what it is already supposed to be
running".

Keep the existing badge-conditional button or fold it into the new one — one
control that always renders and changes emphasis is preferable to two controls
that differ only in when they appear, but that is a judgment for the proposal
below, not a ruling here.

**A push restarts the audio engine.** Confirm accordingly, in the same voice as
the neighbouring confirms (`dashboard.js:1161-1163`).

## Verification

`tests/verify_device_patch_targeting.py` is the living journey for this surface
(it already guards `09-patches-deploy-row`'s row geometry). Extend it:

* a seat-bound online device with badge `current` offers an enabled push
  action — this fails on today's tree, which is the point;
* pressing it sends `retry_fleet_patch` with that device's uid;
* an offline device offers the action disabled, not absent.

The natural fixture is real: Ciro Toast's `main.pd` is currently one edit
behind the host (see the incident note beside the goal), so a push from the
device page can be verified end to end against hardware once the software gate
passes. Say in `verification.md` which half you actually ran.

## Bob's gate

Before `2-pin-unpin-toggle` starts, put the shipped panel in front of Bob:
screenshot the Device page's patch section as it stands and as proposed, name
the buttons, and ask the two questions this stitch cannot settle alone —
whether push and pin are one control or two, and whether "update patch" or
"push patch" is the word. `08/1-columns-design`'s `mockup.py` (generate from
the real running app, do not draw) is the pattern.

Also ask Bob to confirm the goal-level finding: did he ever see `Pin to device`
present, pressed, and inert — or was Ciro Toast simply missing from the
dropdown? If the former, that is a separate defect and needs its own stitch.
