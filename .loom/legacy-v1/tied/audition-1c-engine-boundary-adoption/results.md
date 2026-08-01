# Engine-boundary adoption results

Stage 0 now follows the ratified v1.2 boundary: `tools/audition.py` owns LAN
6660, launches each engine with a distinct `BOPOS_ENGINE_PORT`, delivers run
context atomically, and uses the shared selector-stripping relay logic.
Pure Data's `[bopos]` accepts the launch port and rebinds its engine ingress.

Bob ruled on 2026-07-12 that peripheral IO remains unsupported in audition:
the nodes are virtual/simulated, and virtual peripheral routing stays out of
scope until required. Production retains the dedicated 6662/8880 performance
boundary. Multiple audition PDs may therefore log fixed-6662 bind warnings;
these do not affect Stage 0 audio/control acceptance. A future
`BOPOS_IO_PORT`-style launch context could enable virtual peripherals without
folding IO into the engine-control port.

## Verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/audition-rig/audition-1-stage0-launcher/\
audition-1c-engine-boundary-adoption.stitching/verify_audition_boundary.py
```

PASS: v1.2 context, PD port override, relay isolation, exclusive LAN bind,
partial-start cleanup, and owned process-tree teardown.

```sh
PD='/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd' \
  ~/.venvs/bopos/bin/python \
  .loom/tied/audition-1b-pd-mac-gate/verify_pd_mac.py
```

PASS: three real PD engines bound distinct ports 17661-17663, emitted distinct
heartbeats, accepted relayed control, and stopped cleanly. With an unrelated PD
closed, four expected fixed-port warnings remained: two audition instances
could not share the production-only 6662 peripheral receiver, plus transient
6661 contention before the engine-port override. All assigned engine ports
were bound, so the latter did not affect control delivery.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  tools/audition.py \
  .loom/threads/audition-rig/audition-1-stage0-launcher/\
audition-1c-engine-boundary-adoption.stitching/verify_audition_boundary.py
```

PASS.

Not verified: audible summing by a listener or an N-instance SuperCollider
launch (`sclang` was not exercised). The preserved three-PD Mac topology and
control-plane gate passed; peripheral IO is explicitly outside Stage 0.
