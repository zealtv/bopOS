# Decision — run without an engine for an invalid patch at boot

Choose the stitch's **run without an engine** option. Implement it only at the
manifest gate, before any JACK, engine or patch startup work, with the internal
launcher flag `--skip-invalid-manifest` passed by start.sh. The existing manifest
error still prints; full-stack startup finishes successfully so systemd's
oneshot service remains active instead of restarting and tearing down the node.

This is the smallest change: no fallback patch or audio, no duplicate validation,
no broad ERR-trap exemption, no Python service changes. start.sh's full cleanup
trap remains unchanged. Any later launcher failure still fails boot and cleans
up the partial stack. Engine-only starts, including fetch/switch recovery, do
not pass the flag and still report an invalid manifest as failure.

## Visibility and recovery

Use existing observations: heartbeat engine_alive = 0, Device health/Engine
"engine stopped"/"stopped", installed patch manifest "invalid", and the
existing validator + `PATCH REQUIRES A VALID bopos.patch.json` diagnostics.
No new operator-visible wording or wire field is needed. patch_badge describes
content convergence, not engine health; a "current" content badge is not a
claim that the engine is running. Keep those existing meanings separate.

An ordinary push to the active host-mirrored patch already runs the node fetch
worker's stop → fetch → start sequence. Keeping bopos.py alive restores access
to that route. A valid pushed manifest passes the strict engine launcher; the
existing worker reports terminal success only after engine_alive = 1.

## Software verification choice

Use a **shell harness**, rather than adding manifest modeling to simfleet,
because the defect is the real Bash launcher/ERR trap and no protocol changes
are being made. tests/test_manifest_boot.py runs copies of the real start.sh,
start-engine.sh and validator against retired-type, missing and malformed
manifests. Network/IO slots are inert live OS processes; the fixture stop
script only kills its own PIDs. No real I2C, audio, networking or Pd is used.
A separate post-validation failure seam proves cleanup is still triggered even
when a partially-started engine exits with an arbitrary status.

Strengthen the existing node fetch-worker test with an invalid destination,
a valid file-URI source and the **real fetcher and manifest validator**. Engine
launch/liveness is a stand-in: this pins software convergence and restart order,
not actual JACK/Pd startup. No new simfleet protocol behavior is warranted.

Actual heartbeat/admin reachability, dashboard observations and corrective push
on Finn Jet/Ciro Toast remain Bob's pending hardware claim.
