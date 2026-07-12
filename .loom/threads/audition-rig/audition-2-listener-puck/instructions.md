# audition-2-listener-puck — in-engine spatial preview

Stage A of `../instructions.md`: spatial monitoring from a listener
perspective. Stage 0 and engine-boundary v1.2 are tied.

**Chosen strategy (Bob, 2026-07-12):** every real audition engine keeps its
normal CoreAudio/Linux output path. A private `bopos.mix~` stage passes
audio unchanged in production and applies a listener matrix only in audition
mode. The OS sums the already-spatialized device outputs to stereo. The SC
starter gets an equivalent final-output adapter.

Agents never edit `.pd`; Bob owns `bopos.mix~.pd` and its integration in
`bopos.out~.pd`. Agents implement/test controller, dashboard, simulator, SC,
docs, and exact PD edit recipes.

## Boundary

- The adapter sits upstream of the existing final master stage. Master remains
  the last production gain and is never composed into a patch parameter.
- Listener rendering is audition-tool behavior, not `/pt`, a meter, a report,
  patch semantics, or a production engine capability.
- The local audition matrix uses a private `/audition/*` namespace accepted by
  `tools/audition.py` and audition-mode engine adapters only. Production
  `bopos.py` ignores it; it is not added to the fleet OSC contract.
- Default/bypass operation is bit-for-shape pass-through. Missing or malformed
  preview state must never silence or remap production audio.

## Derived channel model

The `bopos.mix~` creation argument is authoritative for channel count:
`[bopos.mix~ 2]` in Wave 1. Dashboard position count is not: one position may
describe a stereo pair, while two positions describe two mono elements. Do not
add a second hand-maintained `channels` field to installation state or infer
channels from signal energy. The adapter validates every matrix against its
creation argument.

Wave 1 uses the current `bopos.out~` two-channel ABI. Its interpretation is:

- zero positions: unpositioned/bypass; preserve current L→L, R→R output;
- one position: one co-located stereo element; preserve stereo content while
  applying shared distance and directional stereo balance;
- two positions: two mono elements; apply one L/R gain row per input channel
  and sum them to preview stereo.

The matrix update is one atomic indexed frame, not per-element messages. The
controller and adapters must reject a frame whose count/arity disagrees with
the adapter's channel-count argument and retain the last valid frame or bypass safely.
Gains are smoothed in the engine adapter.

For later N-channel support, `[bopos.mix~ N]` should accept a PD multichannel
signal or an indexed wrapper whose width is built from the same `N` argument.
Matrix frames remain indexed/count-prefixed; no wire redesign. Changing `N`
may require rebuilding DSP, which is acceptable; it must not require changing
dashboard storage or the controller grammar. Higher counts are not implemented
in this wave.

## Position and listener convergence

- Dashboard installation state remains the authority for device element
  positions. Today it exposes `pos1`/`pos2`; `/os/assign` already carries the
  complete ordered position list whenever assignment or positions change.
- `tools/audition.py` must handle matching virtual-node assignment updates,
  retain the ordered positions on each `VirtualNode`, update identity if
  assigned, push `/id`, and heartbeat the converged state like a real node.
- Listener position + heading use an audition-local dashboard→relay channel,
  never the fleet contract. A listener or position change recomputes and sends
  a complete matrix to every affected virtual engine immediately.
- Node appearance, engine restart, assignment catch-up, and listener reconnect
  all resend the current matrix. Silence means hold only after one valid frame;
  before that, bypass is mandatory.
- `tools/simfleet.py` gains enough preview-state logging to verify convergence,
  but no fake audio engine.

## Planned sequence

1. **`preview-0-channel-model-spike`** — Bob proves bypass, one-position stereo,
   and two-position mono behavior in a small `[bopos.mix~ 2]` jig; agents ship
   matrix math/fixtures and record the N-channel construction seam.
2. **Relay state and matrix model** — virtual-node ordered positions,
   `/os/assign` convergence, listener state, atomic frame shaping, catch-up,
   and simfleet regression coverage.
3. **PD + SC adapter integration** — Bob integrates PD upstream of master;
   agents build the equivalent SC output adapter and static/behavioral gates.
4. **Dashboard listener puck** — position + heading on the spatial map and a
   local audition channel; position-count edits update relay state immediately.
5. **Mac/Linux audible gate** — three real engines, live element-count/position
   changes, puck sweep, bypass comparison, clean teardown, Bob confirmation.

Create later stitches only after the preceding gate is tied; keep one concrete
loose end at a time. Binaural/HRTF remains deferred.

## Done

The same real patch instances used by Stage 0 produce a stable listener-relative
stereo preview on macOS and Linux without JACK/taps/aggregate devices; normal
output is unchanged; channel count comes from the adapter creation argument;
position/element edits and listener motion converge immediately; and the model
extends to indexed N-channel audio without changing its matrix frame.
