# audition-2-listener-puck

Stage A of `../instructions.md`: spatial monitoring from a listener
perspective. Stage 0 and engine-boundary v1.2 are tied.

## Ratified constraints

- The audition relay represents N virtual **devices**, each running the real
  patch behind its own `BOPOS_ENGINE_PORT`. Do not replace these with one
  synthetic engine implementation.
- Listener monitoring is composition-tool output processing. It stays outside
  patch parameters and the engine surface; it must not compose master, `/pt`,
  or any listener factor into patch-owned values.
- One patch instance may clone N positioned **elements** internally. The
  monitor therefore consumes a distinct stem per virtual device and preserves
  that instance's element channels before producing the listener stereo mix.
- Device/element positions come from dashboard installation state. Reuse
  `python/pointfield.py` falloff curves where the listener model uses the same
  radius semantics; do not revive the superseded dashboard `/p/gain` model.
- Meters and framework streaming remain deleted. Audio capture is the monitor's
  local concern, not a report/meter protocol feature.

## Transport decision gate

**Bob's direction (2026-07-12):** pursue the parent-PD `[pd~]` design in the
`pd-audition-host` loom thread. It keeps capture and listener math in one PD
graph, enables manual rerouting, and is consistent across macOS and Linux.
This listener-puck stitch remains waiting on that thread's three-child spike
and host/matrix implementation rather than on JACK or Core Audio tap selection.

The verified macOS/CoreAudio Stage 0 path lets several PD processes share the
hardware stereo output, but the OS mixes them before an external monitor can
recover per-device stems. The old "small Python JACK client" instruction is
therefore not an accepted cross-platform implementation.

Rejected as default paths (retain only as future specialist fallbacks):

1. JACK per-instance ports (strong isolation, proven Linux shape; adds a Mac
   runtime dependency and replaces the verified CoreAudio path while active).
2. A macOS virtual/aggregate device with deterministic channel allocation
   (native CoreAudio operation; setup and per-process routing need proof).
3. Engine-native audition buses where an engine supports them (clean for SC,
   but cannot become the only path because Stage 0 runs the actual declared
   engine, including PD).

The parent-PD direction is now the accepted default. Revisit these fallbacks
only if the `[pd~]` spike produces concrete contrary evidence.

## Implementation after the gate

- [ ] Capture one isolated, element-preserving stem per virtual device.
- [ ] Implement the listener position + heading gain matrix and stereo output.
- [ ] Add a listener puck to the dashboard spatial map; use an explicit local
      monitor channel (WebSocket or localhost OSC), not the fleet wire.
- [ ] Verify three real audible instances at distinct positions: automated
      stem/matrix capture plus Bob's drag-and-listen confirmation.

Binaural/HRTF remains deferred; do not start it here.
