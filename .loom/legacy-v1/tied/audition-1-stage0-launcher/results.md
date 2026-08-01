# Stage 0 launcher results

Stage 0 is complete on the composition Mac. `tools/audition.py` owns LAN 6660,
launches three real PD/CoreAudio engines on distinct local ports, publishes
distinct virtual identities, serves the selected patch manifest to the
dashboard, relays selector-stripped controls, and tears down only its owned
process trees.

The parent instructions predate the ratified patch seam: `/all/aloha`, direct
PD LAN binding, and JACK-specific routing are superseded. Current acceptance
uses the default patch's continuous audio, its `facilitator:true` `gain0` and
`gain1` controls, and the provided master term through the Mac relay topology.

## Software verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/audition-rig/audition-1-stage0-launcher.stitching/verify_stage0.py
```

PASS: three distinct dashboard identities and one selector-specific raw
manifest reply, including both promoted controls.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/audition-1c-engine-boundary-adoption/verify_audition_boundary.py
```

PASS: v1.2 launch context, dynamic PD port override, relay isolation,
exclusive binding, failure cleanup, and owned teardown.

Python compilation also passed for `tools/audition.py` and
`verify_stage0.py`.

## Real dashboard and audible gate

Launched:

```sh
~/.venvs/bopos/bin/python dashboard/server.py \
  --host 127.0.0.1 --osc-target 127.0.0.1

~/.venvs/bopos/bin/python tools/audition.py \
  --devices 3 --bind 127.0.0.1 --target 127.0.0.1 \
  --engine-port-base 17661 --audio-backend coreaudio \
  --hb-interval 1 --catchup-secs 0.5
```

Headless Chromium opened `/facilitator` through the real WebSocket path and
confirmed `audition-0001`, `audition-0002`, and `audition-0003` each exposed
one `gain0` and one `gain1` control. It swept global master 0→1 four times at
1.2-second intervals, ending at 1. Bob confirmed live: **"sweep working"**.

Both launcher and dashboard then stopped cleanly. The expected fixed-6662
warnings remain harmless for Stage 0: Bob ruled audition peripheral IO
unsupported until virtual peripherals are required; production retains its
dedicated 6662/8880 performance boundary.

Not measured: calibrated output level, latency, clipping, or multi-device
quality. Spatial listener mixing belongs to audition Stage A.
