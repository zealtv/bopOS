# Results

Implemented and live-verified the JACK/engine lifecycle fix prompted by the
silent `bonks-pd` switch on bop000.

## Root cause

At 14:15:53 AEST on 2026-07-14, the outgoing JACK server received SIGTERM but
did not finish releasing its PD client/audio card until 14:16:17. The launcher
started a replacement immediately; it logged `Failed to open server`, waited a
fixed five seconds, and launched PD anyway. The helper considered the surviving
PD process healthy even though neither patch audio nor Identify could play.

## Changes

- `stop-engine.sh` waits up to 15 seconds for each tracked engine/JACK process,
  escalates to SIGKILL with a bounded follow-up, and fails if shutdown cannot
  be confirmed.
- `start-engine.sh` waits up to 15 seconds for the tracked JACK process and a
  successful no-autostart `jack_lsp` probe. It never launches the selected
  engine after JACK exits or fails readiness, and cleans up failed JACK starts.
- `bopos.py` reports engine health only when both the tracked JACK server and
  selected engine process are alive. This makes heartbeat and patch-switch
  convergence fail closed.

## Verification

Local:

- `verify_jack_readiness.py`: 7/7 passed.
- Existing `verify_patch_switch_lifecycle.py`: 10/10 passed.
- Python compilation, Bash syntax checks, and `git diff --check`: passed.
- Existing `verify_dist2_node_side.py`: every real-node distribution check
  passed; its one pre-existing simulator assertion still requests active patch
  `default` while the current simulated fleet starts on `demo-pd`.

Hardware, bop000:

- Pulled revision `a62ced4`.
- Recovered the initially silent `bonks-pd` state with the new stop/start
  scripts. JACK PID 2033 became ready before PD PID 2044 launched; both PD
  outputs connected to the DigiAMP playback ports. Bob confirmed Identify.
- Dashboard switch to `demo-pd`: JACK PID 2238 ready in about one second, PD
  PID 2264 launched, no lifecycle errors.
- Dashboard switch back to `bonks-pd`: JACK PID 2427 ready in about one second,
  PD PID 2446 launched, both outputs connected to hardware playback. Bob
  confirmed bonks audio and Identify after the final switch.
- The device did not reboot and the bopOS helper PID remained 1078 throughout.

The long-running helper predates `a62ced4`; the next normal device reboot will
load the new Python heartbeat health predicate. The fixed Bash lifecycle is
already active and passed the live switching gate.
