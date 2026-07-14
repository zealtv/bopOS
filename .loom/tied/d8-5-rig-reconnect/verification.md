# Verification

## Software

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/dashboard/d8-5-rig-reconnect.stitching/verify_d8_rig_reconnect.py
```

Result: 4/4 passed.

- Bound seat zero routes lifecycle actions with selector zero.
- Identify remains UID-targeted through the all selector.
- An online appearance replays authoritative seat assignment.
- Appearance replay does not infer or alter mute state.

`git diff --check` also passed.

## Live bop000 evidence

- Captured the dashboard's `/all/os/identify` packet, including bop000's UID,
  at the node; Bob confirmed audible Identify.
- Bob confirmed cue-point audio playback.
- Node processes, UDP listeners, active `default` patch, JACK graph, and output
  routing were inspected and healthy.
- DigiAMP gain read `0.00 dB`; restoring its independent playback switch
  restored output without changing gain.
- Node revision `ec33524` matched `origin/main`; therefore only the published
  `default` patch was present. No push was performed.

## Boundaries

- Shutdown was not invoked as a live destructive test.
- Update/reboot was not repeated after establishing that the published branch
  had no newer revision for the node to receive.
- No production file and no `.pd` file changed in this stitch.
