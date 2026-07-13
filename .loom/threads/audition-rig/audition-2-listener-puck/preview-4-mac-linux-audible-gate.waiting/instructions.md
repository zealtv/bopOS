# preview-4-mac-linux-audible-gate

(Coordination, 2026-07-13: if the deferred seats model (`d8-1..3`) lands
before this gate runs, "seed three named audition devices at positions"
becomes "author three seats and let sim-mode bind them" — same audible
sequence, updated harness vocabulary.)

Run the final real-engine listening gate for the tied listener-puck preview.
This stitch may commit Bob's current `patches/default/main.pd` edit, which
provides two distinguishable element voices; agents must not edit that file.

## Owned interactive harness

- Launch a real dashboard and three real `tools/audition.py` virtual nodes on
  isolated localhost ports with a temporary installation state. Seed three
  named audition devices at clearly separated room positions.
- Launch the current default patch in three real PD processes. Use CoreAudio on
  macOS and JACK on Linux. Confirm three distinct uids/ids, three bound local
  engine ports, and no PD/OSC startup errors before asking Bob to listen.
- Print the dashboard URL and keep the harness alive until an explicit Enter,
  Ctrl-C, or termination signal. Own process groups and clean up only processes
  started by the harness; never blanket-kill another PD/dashboard session.
- On exit, verify dashboard, relay, engines, and all reserved ports are gone.
  Retain exact platform, commands, logs, and cleanup evidence.

## Bob audible sequence

1. Establish zero-position identity/bypass and confirm the patch sounds like
   its normal direct fixed-stereo output, with no silence or remap.
2. Restore the three separated one-position assignments. Sweep the listener
   puck across the room and rotate heading through 0/90/180/270 degrees. Each
   source should move continuously in the expected direction with no clicks,
   dropouts, sudden remaps, runaway gain, or master/parameter changes.
3. Add a second position to one device and confirm its two mono element voices
   separate according to their ordered dots. Remove it and confirm immediate
   return to one-position stereo semantics; unplace/re-place a device and
   confirm identity/spatial convergence without another puck gesture.
4. Exercise `/os/master`, both `gain0`/`gain1` patch params, and
   `/notify identify`. They must remain separate from preview movement and all
   three virtual nodes must stay distinguishable despite one host IP.
5. Restart the owned audition relay while the dashboard remains up. Current
   assignments and listener state must catch up without another edit and audio
   must return to the same image.
6. Compare preview bypass again, then stop the harness and confirm clean silence
   plus owned-process/port release.

Record Bob's observations literally. Do not substitute UDP/model checks for an
audible claim, and do not call clipping/latency/calibration verified without a
measurement.

## Platform boundary

Run the same sequence on macOS and Linux before claiming both platforms. If
only one is available, retain its passing evidence and leave this stitch
claimed or waiting with the other platform named explicitly; do not turn a Mac
pass into a Linux claim or vice versa.

## Automated regression

- Run the harness preflight/teardown check plus the tied preview-3 21-check
  browser/UDP gate and preview-1 96-check relay regression.
- Compile the harness and touched Python, check JS syntax if changed, and run
  `git diff --check`.

## Done

Three real engines produce stable listener-relative stereo preview under live
puck, heading, element-count, position, master, parameter, identify, and relay
restart changes on both macOS and Linux; identity bypass remains normal output;
and teardown leaves no owned process or port behind.
