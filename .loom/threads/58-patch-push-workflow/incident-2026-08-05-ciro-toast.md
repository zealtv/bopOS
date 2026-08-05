# Incident, 2026-08-05 — Ciro Toast would not restart, and could not be pushed to

Recorded as the evidence base for thread 58. Everything below was observed on
the device over SSH in Bob's tmux pane, not inferred.

## Symptom

Bob brought Ciro Toast up to date after the large sweep of bopOS changes,
pushed the latest `fire-button` patch, and *"the engine doesn't restart"*.

## What was actually happening

`systemctl status bopos` on `ciro-toast`:

```
Active: activating (auto-restart) (Result: exit-code)
Process: ExecStart=/home/pi/bopOS/bash/start.sh (code=exited, status=1/FAILURE)
```

`journalctl -u bopos`, repeating every 5 s, **restart counter at 211**:

```
manifest: param shutdown-button: type was removed (2026-07-28); use kind (float/int/toggle/enum/text)
ERROR: PATCH REQUIRES A VALID bopos.patch.json: /home/pi/bopOS/patches/fire-button
ERROR: bopOS startup failed; stopping the partial stack
Shutting down...
```

The framework repo on the device was fully current — `361452e`, identical to
the host — and `git status` was clean apart from `M patches/active_patch.txt`.
The stale file was the *patch*:

```json
{ "name": "shutdown-button", "type": "i", "min": 0, "max": 1, "default": 0, "dashboard": true }
...
"cues": [],
```

i.e. the pre-`44-event-plane/2-kind-grammar` `type` grammar plus the
`4-cue-retirement` `cues` key. The host's copy has said
`"kind": "toggle"` since 2026-07-28.

`patches/` is gitignored (`patches/.gitignore:2` is `*`, and `git ls-files
patches` lists only `demo-pd`, `demo-sc`, the template and the README), so
`fire-button` reaches a device **only** by dashboard distribution. `git pull`
on the device could never have fixed it, and never touched it.

## The deadlock

`bash/start-engine.sh:42-44` exits 1 on an invalid manifest. `bash/start.sh:18-25`
traps `ERR` and runs `stop.sh`, tearing down the *entire* stack:

```sh
start_failed() {
    status=$?
    trap - ERR
    echo "ERROR: bopOS startup failed; stopping the partial stack" >&2
    "$SCRIPT_DIR/stop.sh"
    exit "$status"
}
```

`bopos.py` — the device's whole OSC surface, heartbeats included — goes down
with the engine. So:

* the device never appears online in the dashboard;
* `deployable` in `fleetPatchPanel` (`dashboard.js:526-527`) filters on
  `device.online`, so it is not in the deploy target dropdown at all;
* `patchDiagnostics`' remediation button (`dashboard.js:1145`) also requires
  `d.online`, so the Device page offers nothing either.

**The only mechanism that can replace a bad patch is disabled by the bad patch.**
Recovery was SSH, by hand.

## Repair performed

Backed up the stale manifest to `/tmp/fire-button.manifest.bak` on the device,
wrote the host's current manifest over it, `sudo systemctl restart bopos`.
Service went `active`; JACK came up on `sndrpihifiberry` at 44100/512/2; PD
launched; `bopos-context` reported `patch fire-button`, `version 361452e`,
`id 11`, `patch-fingerprint c1b2653247dbf7e0d7aee34e81d46543f025760314d7b359aff5abd084b71c10`.

Left deliberately unrepaired: `main.pd` is still the device's older copy
(host `0da2ca94…` vs device `02f947b9…`), so the *normal* push path can be
exercised now that the device is reachable. That divergence is the natural
starting fixture for `1-device-push-action`.

## Second session, same day — the push still did not work

With the device healthy and online, Bob still could not sync it: fleet deploy,
unpin, and `Sync to fleet patch` all left the badge `stale` with no visible
switch. The device's record read `fetch: {"patch:fire-button": "timeout"}` and
its journal showed `IDENTIFY` arriving but no `FETCH` line — so host→device OSC
was working and the fetch command specifically was never sent.

Cause: the expired-fetch **tombstone** in `OSCBridge.fetch_pending`, written
while the device was crash-looping and never consumable because the reply it
waits for can never arrive. It blocks every subsequent fetch for that
device+slot, and `fetch_matches` reports it as in-flight so the convergence loop
waits on it and gives up silently. Full analysis and the intended fix are in
`5-fetch-tombstone-lockout/instructions.md`.

Cleared by restarting `dashboard/server.py` (the structure is in-memory). One
`retry_fleet_patch` then converged the device end to end: fetch ok, `/11/os/patch`,
engine restart, badge `current`, and the device's `main.pd` now hashes
`0da2ca94…`, matching the host.

The restart also refreshed a second stale reading worth noting: the dashboard
had been showing `git_rev 62c2a5a` / `contract_version 1.13` for a device that
had been running `361452e` / `1.16` since before the session started. `/os/report`
is only requested on demand, so a device that updates while the dashboard holds
an old report keeps presenting the old one indefinitely.

## Audio, checked the same session

Bob heard nothing — no identify chirp, no fire-button audio — with no physical
access to the box. Measured on the device, the digital chain is intact:

* `jack_lsp -c` — `pure_data:output_1/2` connected to `system:playback_1/2`.
* `jack_rec` on PD's outputs while firing `green-button` / `red-button` and an
  `identify`: **peak 3267/32767 (~-20 dBFS), 98k non-zero samples of 705k.**
  PD is producing signal.
* `/proc/asound/card1/pcm0p/sub0/status` — `state: RUNNING`, `hw_ptr`
  advancing, owned by jackd. The DAC is being fed.
* `amixer -c sndrpihifiberry scontrols` — **empty**. `snd_rpi_hifiberry_dac` is
  the plain DAC with no hardware mixer, so the startup log's run of
  `amixer: Unable to find simple control 'Digital'/'Master'/'PCM'/…` warnings is
  expected on this board, not a fault. All volume is software.

So everything from the patch to the DAC is working, and silence is downstream of
the DAC — analog out, amp, wiring, power — which needs physical access. The
identify chirp is a separate question: `identify` sends `/notify identify` to
the engine (`python/bopos.py:659-669`), `fire-button/main.pd` carries the
template's `r bopos-notify` at line 66, and whether anything is wired from there
to make a sound is patch-side, i.e. Bob's.

## Two things worth carrying

**A device can be current on the framework and stale on the patch, and the
framework's own version reporting will not show it.** `bopos-context: version
361452e` was correct and reassuring while the patch underneath it was three
contract revisions behind.

**A hard-break grammar change reaches devices at the speed of patch
distribution, not at the speed of `git pull`.** `2-kind-grammar` and
`4-cue-retirement` both swept `python/`, `dashboard/`, `tools/` and the
tracked patch manifests — but any locally-authored, gitignored patch already
sitting on a device keeps the retired grammar until someone re-pushes it, and
the failure mode is a crash-loop, not a warning. Any future manifest hard
break should assume there are stale copies in the field.
