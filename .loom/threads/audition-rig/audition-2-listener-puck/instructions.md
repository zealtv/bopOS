# audition-2-listener-puck — in-engine spatial preview

Stage A of `../instructions.md`: spatial monitoring from a listener
perspective. Stage 0 and engine-boundary v1.2 are tied.

**Chosen strategy (Bob, 2026-07-13):** every real audition engine keeps its
normal CoreAudio/Linux output path. The existing `bopos.out~` passes audio
unchanged in production and applies a listener matrix internally only in
audition mode. The OS sums the already-spatialized device outputs to stereo.
The SC starter gets equivalent behavior in its existing final-output adapter.

Agents never edit `.pd`; Bob owns the `bopos.out~.pd` audition branch and may
factor its private DSP into `bopos.audition~.pd`. Agents implement/test
controller, dashboard, simulator, SC, docs, and exact PD edit recipes.
`bopos.out~` remains the only public patch abstraction; do not rename it.

## Boundary

- The internal helper sits after the existing production master/notification
  mix and immediately before `dac~`. It is conceptually an external audition
  monitor embedded at the output boundary: bypass is identical, and it never
  changes, stores, or composes the master term or a patch parameter.
- Listener rendering is audition-tool behavior, not `/pt`, a meter, a report,
  patch semantics, or a production engine capability.
- The local audition matrix uses a private `/audition/*` namespace accepted by
  `tools/audition.py` and audition-mode engine adapters only. Production
  `bopos.py` ignores it; it is not added to the fleet OSC contract.
- Default/bypass operation is bit-for-shape pass-through. Missing or malformed
  preview state must never silence or remap production audio.

## Fixed stereo model

Wave 1 keeps the current `bopos.out~` two-input/two-output ABI with no channel
argument or discovery. Those channels are interpreted from dashboard positions:

- zero positions: unpositioned/bypass; preserve current L→L, R→R output;
- one position: one co-located stereo or dual-mono element; preserve stereo
  content while applying shared distance and directional stereo balance;
- two positions: two mono elements; apply one L/R gain row per input channel
  and sum them to preview stereo.

The matrix update is one atomic fixed-stereo frame, not per-element messages.
Adapters reject bad arity/values and retain the last valid frame or bypass
safely. Gains are smoothed in the engine adapter.

A mono patch using this ABI duplicates mono to both inputs. A signal present
only on the left is intentionally treated as hard-left stereo, never inferred
as mono from energy or correlation. Higher channel counts are fully deferred:
do not design an N-channel argument or grammar until a real patch requires it.

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

1. **`preview-0-channel-model-spike`** — Bob proves bypass, one-position
   stereo/dual-mono, and two-position mono behavior inside `bopos.out~`; agents
   ship fixed-stereo matrix math/fixtures.
2. **Relay state and matrix model** — virtual-node ordered positions,
   `/os/assign` convergence, listener state, atomic frame shaping, catch-up,
   and simfleet regression coverage.
3. **PD + SC adapter integration** — Bob integrates the private helper at the
   final output boundary; agents build the equivalent SC output adapter and
   static/behavioral gates.
4. **Dashboard listener puck** — position + heading on the spatial map and a
   local audition channel; position-count edits update relay state immediately.
5. **Mac/Linux audible gate** — three real engines, live element-count/position
   changes, puck sweep, bypass comparison, clean teardown, Bob confirmation.

Create later stitches only after the preceding gate is tied; keep one concrete
loose end at a time. Binaural/HRTF remains deferred.

## Done

The same real patch instances used by Stage 0 produce a stable listener-relative
stereo preview on macOS and Linux without JACK/taps/aggregate devices; normal
output is unchanged; position/element edits and listener motion converge
immediately; and no new abstraction or channel-count configuration is required.
