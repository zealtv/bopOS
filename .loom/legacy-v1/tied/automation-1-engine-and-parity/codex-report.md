# Codex report — parameter automation engine and parity

## Built

### `python/paramgen.py`

- Added the ratified §3.2 parser for constants, fades, multi-segment fades,
  loops, stop, and all six LFO shapes.
- Added duration-unit parsing, canonical and hand-typed option aliases,
  option placement/range validation, and readable `ParamGrammarError` failures.
- Added one-slot-per-identity `GeneratorEngine` with lazy single-thread
  scheduling, last-message-wins replacement, stop/close, and
  `current_value()`.
- Float fades emit the existing engine go-to primitive; curved fades subdivide
  at approximately 33 Hz. Int generators emit ordered integer crossings only.
- LFO phase is recomputed from leader time on every tick; free phase is chosen
  at apply time. `sh` and `drift` use deterministic per-identity/per-period
  random targets so clock-anchored replay is phase/value deterministic.

### `python/bopos.py`

- Kept the existing provided-term branch and added only the numeric declared
  parameter decision inside it.
- Active-manifest numeric params now parse and use the module-level generator;
  constants replace their slot and produce one unchanged relay.
- String, undeclared, and no-manifest parameters retain the old verbatim path.
- Grammar errors log the selector-stripped address and reason, then drop.
- The module-level engine shares `sync_state` and closes in the existing exit
  handler.

### `tools/simfleet.py`

- Imports the shared parser/engine and retains canonical declarations by
  qualified identity.
- Each simulated device owns a generator and a sync-state adapter. Its clock
  source includes that device's simulated skew, matching the real node's
  device-clock-minus-offset leader-time calculation.
- Generator emission updates `device.params` and preserves the existing
  `p/<member>=<value>` log format. Plain sets remain one log entry.
- Grammar errors use `p/<member> grammar error: <reason>` and do not kill the
  simulated device. Unresponsive/dead-engine devices still apply nothing.
- Engines close during simulator teardown.

### Focused verifier

- Added `verify_param_automation.py`, locating the repo by the
  `tools/simfleet.py` marker.
- It covers all requested parser forms/rejections; linear and curved float
  fades; upward/downward int crossings; loop reset; stop; mid/completed
  `current_value`; sync/free LFO phase; and simfleet plain set, fade, stop,
  LFO, grammar-error, and recovery behavior.
- The normal verification path starts real simfleet and sends UDP OSC. Because
  this execution sandbox rejects even loopback UDP socket creation, the script
  has a narrowly scoped fallback that sends the same real OSC datagrams through
  `SimFleet.receive_contract` in-process. A normal host still takes the required
  subprocess/UDP path automatically.

## Decisions beyond the written spec

- A fade from an identity never touched by this process starts from the numeric
  manifest default, or zero when no numeric default exists.
- Negative fade durations are grammar errors; zero-duration fades are allowed.
  LFO periods must be greater than zero and are clamped to at least one
  nanosecond internally.
- The explicit three-element `from x to y` form emits an immediate one-value
  set to `x`, then the go-to/crossing sequence. Current-based fades do not emit
  a redundant starting value.
- `c:`/`curve:` on a one-value constant is rejected because §3.2 permits the
  curve option only on fades, loops, and LFOs.
- Generator callbacks are serialized under the generator condition lock. This
  prevents an old scheduler result from being emitted after a concurrent
  last-message-wins replacement.

## Verification results

Commands were run from `/Users/bob/repos/bopOS` with
`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache` where applicable.

1. `~/.venvs/bopos/bin/python .loom/threads/16-param-automation/automation-1-engine-and-parity.stitching/verify_param_automation.py`
   - PASS: 32 checks, 0 failures.
   - The sandbox selected the documented in-process OSC-datagram fallback
     because loopback UDP bind returned `PermissionError: [Errno 1] Operation
     not permitted`.
2. `~/.venvs/bopos/bin/python .loom/tied/1-contract-model-relay/verify_param_contract_relay.py`
   - PASS: 28 checks, 0 failures.
3. `~/.venvs/bopos/bin/python .loom/tied/1-protocol-node/verify_group_protocol_node.py`
   - PASS: 37 checks, 0 failures.
4. `~/.venvs/bopos/bin/python .loom/tied/boundary-3-framework-slimdown/verify_framework_slimdown.py`
   - NOT PASSABLE in this environment: import-time bind of UDP 7770 fails with
     `PermissionError: [Errno 1] Operation not permitted`.
   - A bind-free inspection also found a pre-existing stale expectation in this
     tied verifier: it expects only `/config`, `/load`, `/report`, `/store`, while
     current ratified v1.7 `bopos.py` also exposes `/admin`. The actual callback
     list is `['/admin', '/config', '/load', '/report', '/store']` before this
     task and after it. Per the task instruction, the tied verifier was not
     amended.
5. `python3 -m py_compile python/paramgen.py python/bopos.py tools/simfleet.py`
   - PASS.
6. `git diff --check`
   - PASS.

## Not done / limitations

- No real loopback UDP subprocess run was possible inside the managed sandbox;
  the focused verifier's in-process OSC decoder/handler fallback passed instead.
- No Raspberry Pi, engine/audio, or hardware verification was run.
- The requested implementation is complete, but the full acceptance command
  set cannot honestly be called all-green because the mandated
  `verify_framework_slimdown.py` is both network-blocked here and stale with
  respect to the already-ratified `/admin` surface. No tied file was changed.
- No commit was made. No `.pd`, `dashboard/`, or Loom state file was touched by
  this task.
