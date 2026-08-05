# 4-invalid-manifest-lockout

A bad patch must not cost the device its OSC surface. Today an invalid
`bopos.patch.json` takes down `bopos.py` along with the engine, so the device
disappears from the network — and the only mechanism that could replace the bad
patch is patch distribution, which needs the device on the network. The loop
closes and recovery is SSH by hand.

Node-side bash. Independent of the three UI stitches; claimable in parallel.
Read `incident-2026-08-05-ciro-toast.md` beside the goal instructions — that is
this stitch's whole evidence base, observed on Ciro Toast, restart counter 211.

## Measured starting state

`bash/start-engine.sh:41-45`:

```sh
if ! MANIFEST_OUTPUT=$(python3 "$BOPOS_DIR/python/manifest.py" "$PATCH_PATH"); then
    echo "ERROR: PATCH REQUIRES A VALID bopos.patch.json: $PATCH_PATH" >&2
    exit 1
fi
```

`bash/start.sh:18-25`:

```sh
start_failed() {
    status=$?
    trap - ERR
    echo "ERROR: bopOS startup failed; stopping the partial stack" >&2
    "$SCRIPT_DIR/stop.sh"
    exit "$status"
}
trap start_failed ERR
```

`start.sh` starts `bopos.py` and `io/main.py` *before* reaching
`start-engine.sh` (`start.sh:72`), so at the moment of failure the OSC surface
is already up and healthy — and then gets torn down by a fault that has nothing
to do with it. systemd restarts, and the whole cycle repeats every 5 s
indefinitely.

The teardown is correct as a default: a half-started stack is worse than none.
What is wrong is that it treats *"this patch is unusable"* — an ordinary,
recoverable, operator-caused condition — the same as *"the audio subsystem is
broken"*.

## The change

Keep `bopos.py` alive when the failure is patch-scoped, so the device stays
reachable, reports honestly, and can be repaired by pushing a good patch.

The shape is a ruling this stitch must make and record, not one to be assumed.
Options, cheapest first:

* **Fall back to a known-good patch.** `patches/demo-pd` is tracked in git and
  always present. Simple, keeps audio alive, but it lies about what is running
  unless the report says so loudly.
* **Start the stack without an engine** and report the patch as failed —
  closest to the truth, and the device's `patches` listing already carries a
  per-patch `manifest: valid|invalid` column that the dashboard renders
  (`dashboard.js:1144`), so the reporting vocabulary exists.
* **Narrow the `ERR` trap** so a patch-scoped failure does not stop the
  services that were already up. Smallest diff; needs care that a genuinely
  half-started *engine* still tears down.

Whichever lands, two properties are non-negotiable and should be asserted:

1. after a manifest failure the device still heartbeats and still answers
   `/admin` requests, i.e. it is a valid distribution target;
2. pushing a valid patch to it recovers it **without SSH**.

Property 2 is the whole point of the stitch. A fix that keeps the device online
but still cannot accept a patch has not fixed anything.

## Also in scope: the dashboard should be able to say this

`patch_badge` has no vocabulary for "online but its patch will not load" — an
engineless device reports its listing with `manifest: invalid`, and the badge
derives from names and fingerprints (`state.py:60-95`), not from validity. If
the chosen approach makes this state reachable and normal, check whether the
badge or the panel needs a word for it. Do not add one speculatively.

## Verification

Software gate: `tools/simfleet.py` does not model manifest validation, so this
needs either a simfleet addition (in the same stitch, per the house rule that
new protocol behaviour lands in the simulator alongside it) or a local shell
harness driving `start.sh` against a deliberately invalid patch directory.

Hardware gate: reproduce on a real Pi by writing a manifest with the retired
`type` grammar — which is exactly the state Ciro Toast was found in — then
confirm the device stays visible in the dashboard and recovers via a push.
The Finn Jet / Ciro Toast rig is the place. **Do not claim the hardware half if
it did not run**; record the split in `verification.md` the way
`44-event-plane/5-pd-adoption` did.

## Carry this finding forward

A hard-break grammar change reaches devices at the speed of patch distribution,
not `git pull` — `patches/` is gitignored and locally-authored patches only
arrive by push. `2-kind-grammar` and `4-cue-retirement` swept the repo
thoroughly and still left a field device crash-looping three contract revisions
later. Any future manifest hard break should assume stale copies exist on
devices and should fail soft on the node, which is what this stitch is for.
