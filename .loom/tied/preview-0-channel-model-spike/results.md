# Preview channel-model spike results

The fixed-stereo audition model is accepted and independently reproducible.
Bob built and tested the PD implementation; agents did not edit `.pd` files.
`python/audition_matrix.py` is the pure controller-side authority for shaping
the four coefficients until the next relay-state stitch integrates it.

## Frozen model

- Coefficient order is `(l0, l1, r0, r1)`.
- Rendering is `L=x0*l0+x1*l1`, `R=x0*r0+x1*r1`.
- Zero positions return exact identity `(1, 0, 0, 1)`.
- One position treats the inputs as one stereo or duplicated-mono element:
  `M=(x0+x1)/sqrt(2)`, `S=(x0-x1)/sqrt(2)`, constant-power pan for `M`, and
  bounded side gain `min(pL,pR)`. Centre is identity and hard extremes collapse
  both channels equally into the selected output.
- Two positions treat `x0` and `x1` as independently panned mono elements.
- Balance is `[-1,1]`, gain is `[0,1]`, and invalid/non-finite/bool inputs fail
  before frame construction.
- PD coefficients are finite `[0,1]` floats rounded to at most six significant
  figures, with negative zero normalized.
- The private engine frame is exactly
  `/audition/matrix <l0> <l1> <r0> <r1>`. It has no selector, node index,
  position count, or geometry: relay targeting selects the engine, while the
  ordered coefficient slots carry the fixed channel indices.
- Listener geometry, position retention, catch-up/resend, and OSC delivery are
  deliberately deferred to the next stitch.

## Verification

Focused pure-model verification:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/audition-rig/audition-2-listener-puck/\
preview-0-channel-model-spike.stitching/verify_audition_matrix.py
audition matrix verify: 81 checks passed
```

Compilation and whitespace checks passed:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/audition_matrix.py \
  .loom/threads/audition-rig/audition-2-listener-puck/\
preview-0-channel-model-spike.stitching/verify_audition_matrix.py
git diff --check
```

The nearby v1.2 Stage 0 regression needs localhost UDP sockets. Its first
sandboxed run failed at `bind()` with `PermissionError: Operation not
permitted`; the permitted rerun passed:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/audition-1c-engine-boundary-adoption/verify_audition_boundary.py
PASS: v1.2 context, PD port override, relay isolation, and owned teardown
```

## Boundaries and limitations

- The audible and steady-signal PD results, exact matrices, master checks, and
  cold-start malformed-state gate are retained in `pd-session-results.md`.
- Rapid PD frames at 40 ms and 10 ms were click-free with 20 ms `line~` ramps.
- The current Bob-owned helper is intentionally only claimed for the one
  `bopos.audition~` instance inside the one public `bopos.out~`; this spike does
  not claim multiple helper instances in one canvas are isolated.
- No listener geometry, dashboard, SC adapter, hardware, or multi-engine
  matrix delivery was implemented or claimed here.
