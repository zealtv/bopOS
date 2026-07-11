# seam-5 results

Shipped `templates/supercollider-bopos/` as the first-class SC starter patch:

- `bopos.patch.json` selects `sclang main.scd`, declares volume and a promoted
  frequency parameter;
- one `sclang` process boots one `scsynth`, creates element Synths lazily by
  0-based element index, and maps them to output channels;
- the `boposOut` Synth is the sole final mix stage and smoothly enacts raw
  master without modifying patch gain;
- `/p/*`, `/os/master`, `/pt`, `/cue`, and `/id` are consumed on the local
  engine surface;
- the README documents obligations, legal degradation, extension points, and
  links to Bob's pending PD twins.

## Evidence-driven delivery correction

The installed SuperCollider 3.13 runtime proved it cannot join helper's
already-bound UDP 6660 socket. With a SO_REUSEPORT helper analogue bound first,
`OSCdef` failed `Could not open UDP port 6660`. The starter therefore exposed a
real incompatibility in the direct-engine-listener assumption.

Helper now selector-matches and relays `/os/master` and `/p/<name>` to active
**non-PD** engines on localhost 6661. Points and cues already use that channel.
PD retains its existing direct 6660 path and receives no duplicate relay.
Helper performs no value interpretation or composition. The contract and SC
README document the selector-stripped local surface.

The related identity catch-up was also healed: `/config` always sends the
already-resolved `NodeState.id` even without `bopos.devices`; the CSV remains a
hostname seed and no longer overwrites a persisted dashboard assignment.

## Verification

- `verify_sc_starter.py` — **13/13 pass**: valid manifest/launcher, required SC
  surfaces, helper identity without CSV, non-PD relay selection/filtering,
  real OSC datagrams, independent 0-based elements, raw
  `gain × proximity × master`, and cue delivery.
- `verify_sc_runtime.py` — **6/6 pass** with SuperCollider 3.13.0: class/source
  compile, JACK + `scsynth` ready, template ready, `/id`, `/cue`, and tolerant
  confirmation of relayed master/gain/frequency inside the live SC process;
  no SC language errors before teardown.
- `.loom/tied/assign-persistence/test_assign_persistence.py` — all checks pass.
- `.loom/tied/seam-3-points-node-side/verify_points_node_side.py` — **18/18
  pass** against the real helper and full dashboard/simfleet stack.
- `python -m py_compile` and `git diff --check` pass.
- Post-runtime process audits found no remaining `sclang`, `scsynth`, or JACK.

The runtime test intentionally terminates the whole SC/JACK process group after
assertions; JACK prints a transient `JackTemporaryException` during that forced
teardown, after the 6/6 result. Realtime-priority warnings are expected on this
development account and do not prevent server readiness.

## Historical test drift

- `hb-identity/test_hb_identity.py` has two exact-config-dictionary assertions
  predating later config keys; its other identity/config checks pass.
- `patch-manifest/test_patch_manifest.py` reaches its simfleet section without
  the later-required `args.manifest` field.
- `node-contract-fixes/test_node_fixes.py` expects a historical instrumented
  `pyOSC3.SENT` shim absent from the current venv.

These tied artifacts were not edited. Current focused integration suites cover
the changed paths.

## Not verified

The server and OSC/audio graph ran against the laptop's real two-channel ALSA
device, but no human audible-quality judgment was claimed. Pi packaging,
multichannel hardware, realtime scheduling, and installation-level audition
remain rig/audition work. No `.pd` file was edited.
