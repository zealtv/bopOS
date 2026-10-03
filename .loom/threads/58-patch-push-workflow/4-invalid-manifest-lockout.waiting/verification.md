# Verification — 4-invalid-manifest-lockout

2026-10-03. Software half verified; hardware half explicitly pending.
Decision and rationale: `decisions.md` (run without an engine at the boot-time
manifest gate). No new badge, operator wording, contract or wire behavior.

## Passed — software shell harness and fetch-worker regression

- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest discover -s tests -p test_manifest_boot.py`: **3 tests, OK** (`shell.log`).
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest discover -s tests -p test_node_fetch_dispatch.py`: **5 tests, OK** (`fetch.log`).
- `./tools/run-tests.sh fast`: **359 tests, OK** (`fast.log`).
- `bash -n bash/start.sh`, `bash -n bash/start-engine.sh`, and
  `git diff --check`: passed.

The shell harness executes the real startup script, engine launcher and manifest
validator in an isolated directory, with retired `type` grammar and with missing
or malformed JSON. Boot exits successfully; both inert service processes remain
alive; no engine/JACK PID is created; full stop does not run; the existing error
and validator reason remain visible. A direct engine-only start still exits 1
for the invalid manifest, preserving fetch/switch callers' failure semantics.

A valid manifest followed by an injected engine-stage failure (exit 65, with a
partial engine process already present) still triggers full-stack cleanup and
preserves the failing status. The hardware stage alone is replaced in this test;
manifest validation and start.sh's existing trap are real.

The strengthened node fetch-worker test starts with an invalid active directory
and an absent engine, fetches a valid source through the real file-URI fetcher,
validates the replaced manifest with the real CLI, and exercises the existing
stop → converge → start sequence. Engine launch/liveness is a stand-in, not
JACK/Pd. It checks replacement bytes and terminal `/os/fetched ... ok` only
after the engine stand-in becomes alive.

This is a shell harness, **not a simfleet model**: the repaired boundary is Bash
startup and no protocol is being added. The shell services are inert live OS
processes; these checks prove process survival, not real heartbeats/admin replies.
No actual node, I2C, audio, Pd or dashboard hardware claim is made. No browser
journey is needed for the unchanged UI.

The macOS sandbox initially denied Bash's `/dev/fd` process-substitution pipes;
the harness and fast suite were rerun outside it and passed. No test was skipped.

## Pending — Bob's Finn Jet / Ciro Toast hardware claim

**NOT RUN.** On the rig, make the active host-mirrored patch manifest invalid
using the retired `type` grammar. Restart the stack and verify:

1. systemd stays active without a restart loop; bopos.py and IO are up.
2. The device continues heartbeating and answering `/admin`; engine_alive is 0.
3. The existing validator diagnostics and demand-refreshed installed-patch
   manifest `invalid`/engine-stopped observations expose the failure.
4. Push a valid patch through the existing dashboard route, without SSH repair.
   Confirm successful fetch/restart, engine_alive = 1 and the patch running.

Record each node's revision, observations, diagnostics and push outcome. This
hardware gate remains open; park the stitch `.waiting`, do not tie it.
