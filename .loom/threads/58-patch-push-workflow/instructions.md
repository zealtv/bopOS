# 58-patch-push-workflow

**Goal:** pushing a patch to a device is obvious and honest, and a bad patch
can never knock a device off the network.

**Status:** `5`, `6` tied; `2` dropped (pinning is being retired, `66`).
`4` is ready and independent. `1` and `3` wait on `66-projects/0-project-design`
— with one patch per fleet, their shape will change.

## Origin (Bob, 2026-08-05)

Pushing an edited `fire-button` patch to Ciro Toast failed
(`incident-2026-08-05-ciro-toast.md`):

> "there's currently no 'update patch' button on the device page. only 'pin to
> device' on the patch page …"

What was actually wrong:

1. **The device was offline.** Its old on-device manifest used retired grammar;
   `start-engine.sh` rejected it and `start.sh`'s error trap stopped the whole
   stack, including `bopos.py`. Off the network, a push can't fix it. → `4`
2. **Offline devices silently vanish from push targets.** → `3`
3. **No push button at rest** — the Device page's sync button only appears when
   the patch badge shows a fault. → `1`

## Stitches

- ~~`5-fetch-tombstone-lockout`~~ — tied 2026-08-13.
- ~~`6-dashboard-url-advertisement`~~ — tied 2026-08-17.
- ~~`2-pin-unpin-toggle`~~ — dropped 2026-10-03; pinning is being retired.
- `1-device-push-action` — always-available push on the Device page. Waits on
  `66/0`.
- `3-push-target-legibility` — say *why* a device can't be pushed to. Waits on
  `66/0`.
- `4-invalid-manifest-lockout` — node-side: a bad patch must not take
  `bopos.py` down. **Ready.**
