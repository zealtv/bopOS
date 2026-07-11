# audition-1b PD Mac gate results

The Bob-owned PD rewrite now exposes an audition-only selector-free local
engine surface through `BOPOS_ENGINE_PORT`. The real Mac test launched three
default-patch PD 0.55.2 processes through `tools/audition.py` on distinct ports
17661–17663.

## Verification

Command, run from the repository root on macOS 14.6.1 arm64:

```text
~/.venvs/bopos/bin/python .loom/threads/audition-rig/audition-1-stage0-launcher/audition-1b-pd-mac-gate.stitching/verify_pd_mac.py
```

Result:

```text
PASS: 3 PD engines, bound local ports, distinct heartbeats, clean launcher stop
```

The verifier proved:

- three owned PD/CoreAudio engines launched with IDs 1, 2, and 3;
- local UDP ports 17661, 17662, and 17663 were all bound;
- the dashboard-facing relay emitted three distinct heartbeat uid/id pairs;
- selector-stripped patch/master/mute/identify traffic was sent through the
  relay, and direct `/cue snap` plus `/pt 0 0 0.5` frames were sent to every
  local engine port;
- no OSC parse or missing `BOPOS_ENGINE_PORT` errors occurred; and
- launcher shutdown released all command/engine ports and left no `pd` or
  `pd-watchdog` process.

Bob's audible observation during the real run: point-controlled noise came
from the left channel (element 0), and the identify notification chirped
through both channels.

Also run:

```text
python3 -m py_compile tools/audition.py \
  .loom/threads/audition-rig/audition-1-stage0-launcher/audition-1b-pd-mac-gate.stitching/verify_pd_mac.py
git diff --check
```

Both passed with no output.

## Honest limitations

- Each audition PD still attempts the production fixed 6660/6661/6662 binds,
  so macOS logs expected `Address already in use (48)` warnings. The distinct
  local engine ports nevertheless bind and operate. Consolidating production
  and audition ingress is deferred to the engine-boundary design session.
- PD's existing report `netsend` to `255.255.255.255:5550` returned macOS
  `Can't assign requested address (49)`, so this run did not verify level-meter
  arrival at a dashboard. The meter correctly produces `level <value>` on the
  patch-side `osc-out`; macOS report transport and meter lifecycle/semantics are
  recorded design follow-ups, not claimed verified here.
- Audio was audibly present and routed as expected, but no calibrated level,
  latency, clipping, or multi-device quality measurement was performed.
