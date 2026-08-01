# Preview engine adapter results

The tied private matrix frame now reaches both engine families at their final
fixed-stereo output boundary. Bob integrated and audibly verified PD; the SC
starter implements the equivalent matrix and validation in its existing
`boposOut` SynthDef.

## SuperCollider adapter

- Identity `[1,0,0,1]` is installed before any preview state.
- `boposOut` reads two ordered inputs and renders
  `L=x0*l0+x1*l1`, `R=x0*r0+x1*r1`.
- Matrix controls use independent 20 ms `Lag.kr` smoothing before the separate
  30 ms production master multiplier.
- `/audition/matrix` accepts exactly four numeric, non-NaN gains in `[0,1]`.
  Retained state and Synth controls change together only after complete-frame
  validation; malformed state holds the last valid matrix.
- PD resets all four typed-unpack validation values to an out-of-range sentinel
  before every candidate, preventing a symbol in a cold inlet from reusing a
  stale coefficient. Bob audibly verified symbol rejection in all four slots.
- The template README records the private frame, equations, identity behavior,
  fixed Wave 1 ABI, and master/parameter separation.

## Verification

Focused PD/SC static and shared-model gate:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/audition-rig/audition-2-listener-puck/\
preview-2-engine-adapters.stitching/verify_engine_adapters.py
engine adapter verify: 73 checks passed
```

Compilation, tied matrix regression, and whitespace:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/audition-rig/audition-2-listener-puck/\
preview-2-engine-adapters.stitching/verify_engine_adapters.py \
  python/audition_matrix.py python/audition_geometry.py tools/audition.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/preview-0-channel-model-spike/verify_audition_matrix.py
audition matrix verify: 81 checks passed
git diff --check
```

Socket-bearing relay and Stage 0 regressions:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/preview-1-relay-matrix-model/verify_relay_matrix.py
preview relay matrix verify: 96 checks passed
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/audition-1c-engine-boundary-adoption/verify_audition_boundary.py
PASS: v1.2 context, PD port override, relay isolation, and owned teardown
```

## Runtime boundaries

- PD was audibly exercised through the real selector-stripped UDP engine port;
  exact observations and messages are retained in `pd-session-results.md`.
- `/Applications/SuperCollider.app/Contents/MacOS/sclang` exists, but the local
  native launch exits before class-library parsing with:
  `Incompatible processor. This Qt build requires ... neon`. An attempted
  x86_64/Rosetta launch did not reach class-library output. SC source spellings
  and shared matrix fixtures pass, but SC syntax/runtime/audio are not claimed.
- No three-engine Mac/Linux audible sweep was run here. That remains the final
  installation gate after the dashboard listener puck exists.
