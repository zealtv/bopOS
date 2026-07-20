# Scalar engine-frame correction — results

Bob's 2026-07-20 real CoreAudio gate established that the originally
implemented two-atom float ramp frames corrupt scalar Pd consumers. Bob
clarified the intended seam: bopOS evaluates automation; Pd receives ordinary
scalar parameter values.

## Implementation

- `python/paramgen.py` now samples float fades, loops, and LFOs at the existing
  30 ms control tick and emits only one-element numeric argument lists.
- Integer crossing semantics, sync/free phase, last-message-wins, stop,
  current-value catch-up, and plain scalar behavior are unchanged.
- Production `python/bopos.py`, `tools/simfleet.py`, and `tools/audition.py`
  share this implementation; there is no audition-only compatibility branch.
- Contract §3.2 and its v1.8 history row now state the scalar-only engine
  boundary. No `.pd` file changed.

## Verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/paramgen.py tools/audition.py tools/simfleet.py python/bopos.py \
  .loom/tied/automation-1-engine-and-parity/verify_param_automation.py \
  .loom/tied/aa-1-audition-generator-parity/verify_audition_automation.py
```

Passed with no output.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/automation-1-engine-and-parity/verify_param_automation.py
```

Passed with zero failures. Float linear and curved fades produced progressive
scalar frames and reached their destinations; parser, int crossings, loop,
stop/current value, phase, and simfleet checks remained green.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/aa-1-audition-generator-parity/verify_audition_automation.py
```

Passed 12/12 over real loopback OSC and three fake engine receivers. Every
fade/LFO engine datagram had exactly one numeric argument; selector isolation,
node-local slots, aligned phase, replacement, malformed recovery, nested
identities, passthrough, and worker cleanup remained green.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/pe-3b-simulator-param-catchup/verify_sim_param_catchup.py
```

Passed 6/6.

## Remaining boundary

Software proves scalar engine datagrams. The parent still owns the real
CoreAudio/Pd rerun and Bob's audible/visual acceptance.
