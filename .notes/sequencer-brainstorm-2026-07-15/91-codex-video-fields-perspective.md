# Spatial modulation authoring

Spatial modulation should feel like painting motion across the room, while compiling to the smallest representation the fleet can safely expand. The author works with gradients, lines, rings, noise and textures on the Seat map; bopOS chooses whether that source becomes a compact field programme, predictive ramps, or pre-baked automation.

The preferred hierarchy is:

1. Use an analytic field when the pattern can be described mathematically.
2. Use predictive texture sampling when the source is genuinely live or visually irreducible.
3. Bake repeatable texture work into breakpoint automation for production playback.

This keeps the visual authoring intuition without importing the lighting world’s assumption that every output channel can be streamed continuously.

## Shared model

Every spatial source should produce one or more normalized channels, usually `0..1`, evaluated at each Seat position. A binding then describes:

- source channel: luminance, red, field value, edge distance, and so on;
- destination: a manifest-declared modulation input or parameter;
- target scope: all Seats or a lowercase Seat group;
- input range, output range, polarity and curve;
- outside-room behavior: hold edge, zero, repeat or mirror;
- ownership when another clip also targets the destination.

Coordinates should be expressed in room metres internally, with an explicit room-to-UV transform for textures. The default sample point is the Seat anchor; per-element sampling can remain an advanced option for Seats with multiple positioned outputs.

There is an important seam decision here. The safest match for the ratified point design is a new normalized provided term:

```text
/field <fieldId> <element> <value>
```

The patch decides how that term affects gain, cutoff or another internal quantity. Having `bopos.py` multiply a field into `/p/cutoff` would recreate the composition mistake that the `/pt` design removed. The UI may still present a friendly “luminance → cutoff modulation” binding, but its destination should be a patch-declared modulation input unless a future contract explicitly ratifies distributed parameter evaluation.

All three architectures need the same lifecycle:

- definitions and frames are full-state, revisioned and idempotent;
- launch uses a future shared time;
- replacement and removal are explicit states, not toggles;
- a reconnecting node receives the current definition and derives the correct phase;
- silence means finish any already-scheduled ramp, then hold the endpoint.

## A. Analytic fields evaluated on each node

A field definition contains a primitive, coordinate transform, shaping parameters, initial phase, time evolution, seed where applicable, and a future shared start time. It is broadcast once conceptually; each node evaluates the function at its own stored position and updates its engine over localhost.

Examples:

```text
linear gradient + phase velocity       sweeping wash
angular gradient + angular velocity    rotating pinwheel
line distance + moving origin          animated boundary
radial distance + repeating waveform   expanding rings
seeded noise(x, y, time)                drifting noise field
```

A spinning field therefore consumes one control command, while local evaluation can run at 30–60 Hz without using WiFi.

### Bandwidth

Assume a generously sized OSC field definition of about 160 bytes, including address, type tags, primitive parameters, revision and shared start time.

| Delivery | 30 Seats | 100 Seats |
|---|---:|---:|
| One definition | 160 B | 160 B |
| Three identical launch repeats | 480 B | 480 B |
| Optional 1 Hz state refresh | 1.28 kbit/s | 1.28 kbit/s |
| Node-local evaluation at 30 Hz | no LAN traffic | no LAN traffic |

The Seat count changes aggregate node CPU work, but not WiFi airtime: the same broadcast datagram is transmitted once. Even several simultaneous fields remain tiny compared with per-Seat updates.

“Broadcast once” should mean one semantic command, not necessarily one physical UDP attempt. WiFi broadcast has no MAC acknowledgement, so bopOS should send the same idempotent definition perhaps three times before its scheduled start and retain it for catch-up.

### Latency and coherence

This is the strongest architecture for coherent motion:

- All nodes derive phase from the same shared start time and their synchronized local clocks.
- Packet arrival time does not become animation phase.
- Dashboard frame rate, browser throttling and video decoding do not affect playback.
- A field can start sample-tight-ish using the same timing approach as `/cue`.
- Slowly accumulating phase should be calculated from elapsed monotonic time, not by incrementing a float each frame.

Timing remains in `bopos.py`; the engine receives only relative scalar values, never absolute timestamps.

### Loss and failure behavior

The dangerous case is a lost one-shot replacement: one node continues the previous field while the rest adopt the new one. Mitigations are:

- repeat identical definitions before the future start;
- include a field slot and monotonically changing revision;
- periodically advertise a compact current-state digest or snapshot;
- push retained definitions to reconnecting nodes;
- make `stop`, `clear` and replacement full-state operations.

If communication disappears after a field has started, every node continues locally. That is usually preferable to freezing, but it slightly stretches “silence = hold.” The precise rule should be: silence holds the field programme, including its declared time evolution. An explicit stop freezes or removes it. If the evaluator itself fails, the engine holds its last delivered scalar.

Deterministic noise needs a named, versioned algorithm. “Noise seed 42” is not enough if Python/library upgrades can change the result.

### Authoring experience

This should be the everyday mode:

- Add a field directly on the Seat map.
- Drag its centre, direction, width or handles.
- Press play and adjust speed, phase and softness.
- See the normalized result as a heatmap behind the Seats.
- Audition the corresponding patch input.
- Save the compact definition in the clip’s plain-text source.

Fields should expose artistic controls—centre, angle, width, repeat, softness and speed—not shader terminology unless an advanced inspector is opened.

## B. Live texture sampling with predictive ramps

Some sources cannot be compactly described: live camera images, hand-drawn animation, feedback textures or arbitrary video. Here the dashboard samples the source at the Seat coordinates, predicts a short interval, and sends a piecewise-linear segment at only 2–5 Hz. Each node plays the segment smoothly over localhost.

A literal per-device packet stream is still unacceptable. The workable form is an atomic broadcast ramp frame containing every Seat’s segment; each node extracts its own entry.

A full-state entry should contain at least:

```text
seatId, valueAtStart, valueAtEnd
```

The frame also needs a revision, shared start time and common duration. Sending only an endpoint is smaller, but makes the result depend on what each node happened to receive previously and is therefore not fully idempotent.

### Bandwidth

For OSC, three 32-bit arguments plus type-tag overhead cost approximately 15 bytes per Seat. With roughly 48 bytes of fixed frame metadata:

```text
frame bytes ≈ 48 + 15 × Seat count
```

| One parameter channel | 30 Seats | 100 Seats |
|---|---:|---:|
| Approximate frame | 498 B | 1,548 B |
| At 2 Hz | 8.0 kbit/s | 24.8 kbit/s |
| At 5 Hz | 19.9 kbit/s | 61.9 kbit/s |
| Raw equivalent at 30 Hz | 119.5 kbit/s | 371.5 kbit/s |

These are UDP payload estimates, not WiFi airtime. Broadcast’s low basic rate, framing overhead and contention make the real cost worse. Four independent RGBA mappings multiply the payload approximately fourfold.

The 100-Seat frame is also above a conservative single-datagram budget. It should be split into revisioned chunks below roughly 1,200 bytes and applied only after all chunks for the frame arrive. That creates about 100–250 frame datagrams per minute at 2–5 Hz, rather than 3,000 per-Seat packets per minute.

For comparison, addressing every Seat separately at 5 Hz would create 150 packets/s for 30 Seats and 500 packets/s for 100 Seats. The packet storm is more damaging than its nominal data rate and violates bopOS’s transport law.

### Latency and coherence

Predictive ramps exchange responsiveness for resilience:

- At 5 Hz, the natural planning interval is 200 ms.
- At 2 Hz, it is 500 ms.
- Scheduling one interval ahead gives coherent starts but adds roughly that much control latency.
- Nodes interpolate locally, so visible or audible stepping is avoided.
- Shared frame start times prevent packet-arrival jitter from becoming spatial skew.

A live camera gesture will therefore feel delayed but smooth. Five hertz is plausible for slow washes and organic video; it will not preserve sharp 30 Hz cuts. A discontinuity detector could send an immediate replacement frame for cuts, accepting that this is an exceptional burst.

Texture decoding and sampling should not depend on a foreground browser tab. A backend worker, dedicated renderer, or explicit browser-to-backend sampling process is safer than the dashboard’s main UI loop.

### Loss and failure behavior

If one ramp frame is lost, a node finishes its previous segment and holds its endpoint. It must not extrapolate the previous slope indefinitely. The next complete full-state frame catches it up smoothly.

Chunking adds a new failure mode: receiving half a fleet frame. Frames therefore need:

- frame revision and chunk count;
- atomic application only when complete;
- expiry before their scheduled start;
- repeated transmission where bandwidth permits;
- retention of the last complete frame for reconnect diagnostics.

If the dashboard texture process stalls, the room settles onto the last predicted endpoint rather than producing noise or silence. This is musically sane, but the UI should show a conspicuous “texture source stalled; fleet holding” state.

### Authoring experience

This is the most immediate visual workflow:

- Drop video, a camera, canvas or generated texture onto the room.
- Position it using fit, fill, stretch, rotate, mirror and crop controls.
- Choose luminance, RGB, alpha, hue, saturation or a derived channel.
- Preview sampled dots on every Seat.
- Choose 2, 3 or 5 Hz quality and see the estimated bandwidth.
- Record or bake the result when it becomes repeatable.

The hard UX problem is calibration, not modulation. bopOS should never require manual UV coordinates for each Seat. The room transform owns that mapping, and a checkerboard/test-pattern view should make orientation errors obvious.

## C. Offline video baking into breakpoint automation

Offline baking samples the texture at every Seat, simplifies each resulting curve within a chosen error tolerance, and stores ordinary breakpoint automation. The data is distributed before the show. Playback requires only a timed clip launch.

This is the best production form for fixed video, especially when the visual is merely an authoring instrument and does not need to be rendered during performance.

### Bandwidth and storage

Using a compact binary breakpoint of one 32-bit time delta plus one 32-bit value gives eight bytes per point. Before adaptive simplification, a 60-second, single-channel bake costs:

| Sampling density | 30 Seats | 100 Seats |
|---|---:|---:|
| 2 Hz: 121 points per Seat | 29.0 kB | 96.8 kB |
| 5 Hz: 301 points per Seat | 72.2 kB | 240.8 kB |

Text or JSON may be two to four times larger. Error-bounded simplification can make slow gradients dramatically smaller, while noisy material may remain near the unsimplified size.

The important distinction is when those bytes travel:

- Before the show: approximately 29–241 kB per minute per channel, transferred through reliable content distribution.
- At launch: one small scheduled cue, perhaps 40–100 bytes, independent of Seat count.
- During playback: no WiFi modulation traffic.

Each node should receive only its own automation lane plus shared metadata. Sending a complete 100-Seat bake to every node would turn a linear asset into needless quadratic distribution.

### Latency and coherence

Baked automation has excellent deterministic playback:

- Breakpoints use the shared clip timeline.
- Nodes start from a future scheduled cue.
- Video decode, GPU load and dashboard frame rate are absent during the show.
- Scrubbing and rehearsal can be exact.
- Adaptive breakpoint density can preserve sharp transitions while simplifying smooth regions.

It cannot react to live video or last-second source edits without rebaking. That limitation is often desirable: the authored result becomes inspectable, diffable and reproducible.

### Loss and failure behavior

Asset distribution should be acknowledged and hash-verified. A launch preflight must know which nodes hold the required bake revision; silently launching mixed revisions would be worse than refusing.

The timed launch can be repeated idempotently before its future start. A node rebooting mid-clip should derive the current clip offset from the shared timeline, seek to the surrounding breakpoint pair and resume. If that is not implemented, the honest fallback is to hold until the next clip launch.

### Authoring experience

“Bake” should be one button, followed by useful evidence:

- original texture and sampled Seat preview;
- simplified curve preview for selected Seats;
- maximum and RMS approximation error;
- resulting file size and breakpoint count;
- warnings for hard cuts or very noisy channels;
- stale badge when the video, room geometry, Seat positions or mapping changes.

The generated automation should remain plain-text or have a deterministic text representation so agent-coded composition and git review remain first-class.

## Minimal analytic field vocabulary

A small orthogonal vocabulary will cover more work than a large effects catalogue.

### Coordinate transforms

Every primitive gets the same transform controls:

- origin/translation;
- rotation;
- independent X/Y scale;
- room normalization;
- repeat, mirror or clamp;
- phase and phase velocity.

This is what makes one primitive reusable. A linear gradient plus repeat becomes stripes; radial distance plus repeat becomes rings; a line plus rotation becomes a sweep.

### Scalar primitives

1. **Plane / linear coordinate**  
   Projection of position onto a direction. Covers gradients, wipes, bands and travelling waves.

2. **Radial distance**  
   Distance from a centre. Covers blobs, halos, expanding rings and distance waves. This generalizes much of `/pt`, though `/pt` should remain intact.

3. **Angular / conic coordinate**  
   Angle around a centre. Covers rotating gradients, pinwheels and angular sectors.

4. **Line or segment distance**  
   Distance from an infinite line or bounded segment, with width and softness. Covers moving boundaries, scanning bars and drawn spatial paths.

5. **Deterministic noise**  
   Seeded 2D noise with scale, contrast and time/advection. One fixed algorithm initially; optional octaves later.

Lighting consoles validate this compact set. ETC’s virtual effect layers centre on gradients and Perlin noise, while its pixel maps apply images, movies and procedural effects to positioned fixtures ([ETC effect layers](https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/21_Virtual_Media_Server/Effect_Layers.htm?TocPath=Virtual+Media+Server%7C_____6), [pixel-map model](https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/21_Virtual_Media_Server/Pixel_Map_%5BTab_9%5D.htm)). Notch similarly builds field systems from points, images, primitives, turbulence and vortex-like motion, suggesting that primitive type and motion behavior should remain separate concepts ([Notch Fields](https://manual.notch.one/2026.1/en/docs/reference/nodes/fields/)).

### Shaping and combination

A short modifier chain is more valuable than more primitives:

- invert;
- clamp and remap;
- smoothstep/softness;
- gain, bias or gamma;
- sine, triangle, saw and pulse wrapping;
- quantize into bands;
- combine two fields with add, multiply, minimum, maximum or subtract.

Combination depth should be deliberately bounded in the first version—perhaps two sources and four modifiers. If the editor becomes a general node-based shader tool, the plain-text clip representation and predictable node cost will both suffer.

## Lessons from lighting and pixel mapping

Lighting tools treat a physical layout as durable infrastructure. ETC’s pixel-map editor assigns fixtures to an X–Y map, provides rotate/flip/order operations, colour-codes patch state and includes a Flash check ([ETC pixel-map setup](https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/21_Virtual_Media_Server/Setting_Up_Pixel_Map_Features.htm)). TouchDesigner can sample an image at an arbitrary list of UV coordinates and produce RGBA channels for those positions ([TouchDesigner TOP to CHOP](https://derivative.ca/UserGuide/TOP_to_CHOP)). MadMapper separates fixtures and surfaces from media, provides generative materials, fixture grouping, parameter snapshots and offline DMX export ([MadMapper features](https://madmapper.com/madmapper/features), [Scenes and Cues](https://madmapper.com/files/06-Scenes%20and%20Cues.pdf)).

The useful lessons for bopOS are:

- **Patch positions once.** Seat geometry is authoritative; modulation clips reference it rather than storing another channel layout.
- **Keep spatial mapping and value mapping distinct.** “Where is the texture?” and “What does luminance control?” belong in adjacent but separate controls.
- **Use semantic destinations.** Show manifest names, ranges, units and groups—not raw OSC addresses or device IDs.
- **Preview at the fixtures.** Each Seat dot should display its sampled value, with a solo/identify gesture comparable to a lighting console’s Flash.
- **Provide transform presets.** Fit, fill, stretch, rotate 90°, flip and mirror remove most UV fiddling.
- **Offer sensible channel adapters.** Luminance is the default; RGB, alpha, hue and saturation are named alternatives. Parameter ranges supply the default output scaling.
- **Make collisions visible.** If two clips target the same input, show the ownership rule. Do not hide generic HTP/LTP-like priority behind automatic behavior; require replace, crossfade or an explicit combiner.
- **Use groups as masks.** Apply the same field to `all` or a Seat group without cloning the mapping.
- **Separate edit and live state.** Editing a source should preview locally until committed or launched, so a stray drag cannot rewrite a running installation.
- **Expose cost before launch.** Analytic fields show negligible network cost; texture sampling shows rate, channels, datagrams and MTU warnings; baked clips show asset size and readiness.
- **Make baking reversible.** Preserve the source texture, transform and simplification settings alongside the generated curves.

## Recommended first version

The strongest first version is analytic fields plus offline baking:

- Add a small, contract-ratified normalized field term patterned after `/pt`.
- Implement plane, radial, angular, line and deterministic noise sources.
- Give every field shared transforms, shaping and node-side time evolution.
- Build the Seat-map editor and mapping cards around normalized channels.
- Let the same editor bake any texture or field preview into per-Seat breakpoint lanes.
- Launch both field programmes and baked clips with future shared times.
- Treat 2–5 Hz live predictive textures as an experimental bridge, limited to a small number of channels and guarded by explicit bandwidth/fragmentation warnings.

That combination captures most of the immediacy of pixel mapping while preserving bopOS’s defining advantage: the network carries compact intentions, and the fleet expands them locally.