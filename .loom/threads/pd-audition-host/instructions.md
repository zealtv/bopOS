# pd-audition-host — Audition Host

**Goal:** run N real Pure Data patch instances inside one parent PD audio graph,
so a composer can monitor a virtual installation spatially, inspect or reroute
raw stems manually, and optionally expose channels to a DAW without JACK,
Core Audio process taps, or production-patch audition code.

The user-facing component is **Audition Host**. The proposed Bob-owned parent
patch is `pd/audition-host.pd`; agents never edit `.pd` files.

## Architecture

- The parent hosts one `[pd~]` subprocess per virtual device. Each subprocess
  opens the actual manifest-declared patch entrypoint, receives its own device
  id, run context, and `BOPOS_ENGINE_PORT`, and does not open a hardware audio
  device. Its `[dac~]` channels become signal outlets in the parent.
- The parent alone owns the hardware/DAW audio device. Raw child outputs stay
  accessible in the patch before any listener rendering, allowing manual PD
  routing, recording, inspection, or alternate monitors.
- `tools/audition.py` remains the LAN/control-plane owner and source of virtual
  identities. A host mode launches one parent instead of N hardware-output
  engine processes; production and Stage 0 relay grammar do not change.
- The listener matrix belongs entirely to the parent audition graph. It never
  changes patch params, `/pt`, master, `bopos.out~`, or the v1.2 engine surface.
- Peripheral IO is unsupported for virtual children until a concrete need;
  production keeps its dedicated 6662/8880 performance boundary.

## Stereo-first output model

Wave 1 captures exactly two output channels per child (`[pd~ -noutsig 2]`).
This matches almost all current work:

- two coincident assignment positions: preserve the pair as one stereo element;
- two distinct positions: treat the channels as two independently positioned
  mono elements.

The raw pair is never collapsed before the parent monitor. The listener matrix
therefore has enough information for both interpretations. Higher element
counts are deliberately deferred, but the child wrapper and matrix state must
use indexed/channel-counted structures rather than hard-coded `leftPatch` /
`rightPatch` names. Extending `-noutsig`, the position list, and the matrix must
not require a new control protocol.

## Simplicity rules

- No Core Audio tap, aggregate-device, JACK, virtual-driver, or DAW dependency
  in the default path.
- No special structure required inside an authored patch beyond the existing
  bopOS obligations and its two `[dac~]` outputs.
- One parent graph owns capture, spatial preview, final stereo, and teardown.
- Prefer visible PD signal wiring and small abstractions over a Python audio
  engine. Python coordinates processes/state; PD renders audio.
- Keep current N-process CoreAudio Stage 0 as the compatibility fallback and
  comparison baseline.

## Planned sequence

1. **`host-0-three-child-spike`** — prove three unchanged default patches under
   `[pd~]`, two isolated channels each, unique control identity/context, clean
   teardown, and acceptable CPU/latency on the Mac.
2. **Host launcher/control integration** — add an explicit audition host mode
   to `tools/audition.py`; dashboard discovery and facilitator controls must
   remain identical to Stage 0.
3. **Listener matrix** — parent-side position + heading renderer, smoothed
   gains, identity/bypass mode, and raw-stem access. Reuse `pointfield` curve
   semantics only where the listener model genuinely shares them.
4. **Dashboard puck** — a local monitor channel from the existing spatial map;
   never place listener state on the fleet wire.
5. **Composition/DAW gate** — Bob drag-and-listen run, manual PD rerouting, and
   optional multichannel device output from the parent. Document a recipe, not
   a mandatory DAW.
6. **Higher-channel extension** — only when a real patch needs more than the
   stereo-first model; preserve arbitrary indexed element positions.

Create later stitches only after the preceding gate is tied; keep one concrete
loose end at a time.

## Done

Three or more real declared PD patches run as independently controlled virtual
devices inside one parent graph; their isolated stereo outputs can be manually
routed or spatially rendered to a listener-controlled stereo mix; the dashboard
composition loop works; shutdown leaves no child process; and the current
Stage 0 remains available unchanged.
