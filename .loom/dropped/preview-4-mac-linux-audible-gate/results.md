# Preview 4 audible gate results

## Disposition

- macOS/CoreAudio: audible sequence passed on 2026-07-13.
- Linux/JACK: not run; no Linux audio host was available in this session.
- The stitch therefore does not claim the cross-platform done condition and
  remains open for the Linux gate.

The harness deliberately leaves `audible_result` neutral in `run.json`; Bob's
human listening observations are recorded here.

## macOS run

Host: macOS 14.6.1 (23G93), arm64. Engine: Pd 0.55.2. Audio backend:
CoreAudio, heard through the MacBook Air speakers.

The passing run is retained as `macos-pass-*`. It launched the dashboard on
HTTP 18118, report UDP 15578, command UDP 16688, and three real PD engines on
17691--17693. Initial owned PD PIDs were 14359, 14360, and 14361. The owned
relay restart replaced them with PIDs 15380, 15381, and 15382.

Bob's observations, in sequence:

- Listener-puck spatialisation: "spatialisation is working well."
- The initial UI was illegible in light mode. Literal locale-warning text was
  found at the top of `dashboard/static/css/style.css`, invalidating the base
  theme. After removing it and explicitly locking both views to dark mode, Bob
  confirmed the UI was legible.
- Zero-position identity worked on the unpositioned devices. The first harness
  bypass attempt left device 3 positioned because its short-lived WebSocket
  closed before the last update was acknowledged. After all three clears were
  acknowledged, Bob confirmed identity bypass was "all good." The harness now
  waits for each `device_update` acknowledgement.
- Restoring all three seeded positions restored the spatial image immediately,
  without another listener gesture: "yes."
- Master `1 -> 0.5 -> 0 -> 1`, independent `gain0`/`gain1`, and per-device
  identify targeting: "all good."
- One-to-two positions, independent element movement, return to one position,
  unplace/re-place identity convergence, and browser reload convergence:
  "all good."
- Restarting the owned relay and all three PD engines while retaining the
  dashboard recovered audio, assignments, listener state, and the spatial
  image without another edit: "all good."

No clicks, dropouts, stuck values, unexpected silence, targeting errors, or
UI/audio mismatches were reported in the requested checks. This was a listening
gate, not a clipping, latency, or calibration measurement.

Every three-instance launch reported four
`netreceive: listen failed: Address already in use (48)` warnings from the
patch's known fixed auxiliary receivers. The three required private engine
ports were distinct and bound, all three engines produced audio, and the
warnings did not affect the accepted gate. They remain recorded verbatim in
the launch records rather than being hidden.

On final `q`, the dashboard, relay, and replacement engines exited. The run
record reports `processes_released`, `ports_released`, and
`owned_pd_pids_released` all true; independent `lsof`/`pgrep` checks found no
owner remaining on 18118, 15578, 16688, or 17691--17693.

The `macos-preflight-*` files retain the earlier pre-ready attempt. It treated the known fixed
auxiliary-receiver warnings as fatal and safely released every process and
port. The harness was then narrowed to retain those warnings while still
requiring three live owned PIDs and three distinct bound engine ports.

## Automated verification

Passed:

- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python .../run_audible_gate.py
  --no-engine --http-port 18218 --report-port 15678 --cmd-port 16788
  --engine-port-base 17791 --results-dir /tmp/bopos-audible-gate-postfix`:
  three heartbeats, no engine ports bound, clean process/port/PID release.
- `~/.venvs/bopos/bin/python .../verify_dark_theme.py`: 6 checks passed for
  technical and facilitator views under an emulated light OS theme.
- `~/.venvs/bopos/bin/python
  .loom/tied/preview-1-relay-matrix-model/verify_relay_matrix.py`: 96 checks
  passed.
- `python -m py_compile` for `run_audible_gate.py` and
  `verify_dark_theme.py`.
- `git diff --check`.

The tied preview-3 browser regression ran 13 checks before its historical
exact-coordinate assertion failed: a pixel-derived puck drag produced x=2.99,
then room resize correctly retained x=2.99 and clamped y=5.00, while the test
requires x exactly 3.00. Its preceding drag assertion already accepts +/-0.08
m, and the expected resized matrix arrived. This appeared only once the broken
base stylesheet was restored. The production coordinate was not distorted to
satisfy an over-exact browser assertion; Bob manually passed the affected
drag, resize-adjacent positioning, element-count, reload, and audio behavior.

## Remaining gate

Repeat the same owned harness and audible sequence on a Linux host with a real
JACK output. Record the JACK device/server details, Bob's observations, exact
commands and PIDs, restart convergence, warnings, and clean teardown before
tying this stitch or claiming Linux support.
