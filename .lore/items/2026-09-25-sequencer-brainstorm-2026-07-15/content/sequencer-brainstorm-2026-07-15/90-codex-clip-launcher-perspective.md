# bopOS clip launcher: behaviours, not packets

> Brainstorm material for the Bob-gated `scene-sequencing` co-design. Nothing here ratifies scripting syntax or a new OSC term.

The useful Ableton metaphor is the performance model, not the implementation model: tracks organise behaviours, clips describe bounded or looping behaviour, scenes launch combinations, and follow actions create long-form structure. The bopOS-native version should compile those behaviours into compact, scheduled terms that the fleet expands locally.

The dashboard should therefore act less like a timeline continuously playing OSC and more like a conductor issuing timestamped instructions:

1. Compile text into an immutable behaviour plan.
2. Stage that plan before it is needed.
3. Activate it at an exact shared-clock instant.
4. Let nodes generate ramps, fields and deterministic variation locally.
5. Retain enough generation and ownership state to cancel or replace it safely.

## Data model

Tracks should remain organisational lanes rather than audio mixer channels. A track might mean “percussive cues,” “westward point motion,” “density drift,” or “scatter this sound family.” Normally one clip is active per track, while clips on different tracks compose concurrently.

| Object | Persistent definition | Important runtime state |
|---|---|---|
| Session | Tempo/meter map, global launch quantum, tracks, scenes, deterministic session seed | Transport state, beat-to-monotonic mapping, session epoch |
| Track | Stable ID, label, default selector, behaviour category, conflict policy | Active and queued clip instances, generation number, owned targets |
| Clip | Source text, compiled-plan hash, duration/timebase, loop mode, launch quantum, follow actions, seed policy, declared reads/writes | Start time, playhead, loop count, random stream, scheduled horizon |
| Scene | Sparse track-to-action map, scene quantum, transition duration/curve, optional follow action | Queued/running/complete state, transition generation |
| Playback instance | Derived from a clip rather than saved as authoring data | Unique instance ID, clip revision, start beat/time, cancellation token, target snapshot |

A scene cell needs three explicit states:

- **Launch** this clip.
- **Stop** the current clip on this track.
- **Hold** the track exactly as it is.

An empty cell cannot safely stand for all three. Ableton’s removable stop buttons solve this visually; bopOS should make the distinction part of the saved model. This matters especially when a scene is intended to change spatial motion while leaving an unrelated ambient behaviour running.

Every compiled clip should advertise its **resource claims**: cue IDs fired, parameters written, points or fields controlled, and selector used. This makes several errors detectable before launch:

- references to undeclared patch parameters or cues;
- two tracks attempting to own the same continuous target;
- a crossfade whose incoming behaviour has no initial state;
- use of a fleet-only term from a group-bound track.

The source text and compiled plan should be separate artifacts. Editing produces a new immutable revision; it must not mutate the plan of a clip already running. This follows SuperCollider’s valuable distinction that patterns define behaviour while streams hold execution state. Its event model also demonstrates the usefulness of separating event generation from the action performed by an event. [SuperCollider Pattern Guide](https://doc.sccode.org/Tutorials/A-Practical-Guide/PG_01_Introduction.html), [Pbind and Events](https://doc.sccode.org/Tutorials/A-Practical-Guide/PG_03_What_Is_Pbind.html)

## Compiler and scheduler architecture

The compiler should lower clip semantics into a small intermediate representation, not directly into OSC packets. The useful semantic operations are approximately:

- discrete fire;
- full-state parameter assignment;
- breakpoint ramp;
- analytic spatial field or point trajectory;
- deterministic scatter selection;
- clip/loop boundary;
- follow-action decision;
- release or takeover of a controlled resource.

This leaves syntax open for the human co-design session while giving the backend a stable execution model.

Compilation should happen when a clip is saved or armed, not for the first time on launch. It should validate against the fleet patch manifest and produce:

- a content hash and source revision;
- finite event blocks plus loop/follow metadata;
- initial and terminal state for each continuous target;
- resource claims;
- required bopOS capabilities or contract extensions;
- an estimate of LAN traffic and node evaluation cost.

The asyncio backend should have one authoritative scheduler rather than a sleeping task per clip:

```text
WebSocket/UI intents
        ↓
serialized state reducer
        ↓
quantized launch/follow decisions
        ↓
immutable playback instances
        ↓
look-ahead compiler → priority queue ordered by shared monotonic time
        ↓
wire adapter → staged plans / timestamped activations / cancellations
```

A single reducer prevents simultaneous UI launches, scene follows and clip follows from racing. A heap-based scheduler can wake for the next preparation deadline while maintaining a rolling look-ahead horizon. Thousands of `asyncio.sleep()` tasks would be harder to cancel coherently and would distribute transport logic across mutable coroutines.

The transport should own a piecewise mapping between musical beat and leader `monotonic_ns()`. Each tempo change creates a new mapping segment. Clock-time clips remain in real duration; musical clips follow beat time. Already committed events inside a short safety horizon should retain their scheduled instant, while events beyond it can be regenerated from the new tempo segment. Otherwise a tempo edit can reorder packets already staged on nodes.

Launch handling should be transactional:

1. Receive an intent and calculate the next legal quantum boundary.
2. Snapshot selector membership, clip revision and deterministic seed.
3. Check plan readiness and conflicts.
4. Create a new track generation.
5. Stage anything nodes do not already have.
6. Send an idempotent activation naming the plan, generation and shared start time.
7. Publish the queued state and exact launch boundary to every dashboard client.

The existing `/cue <id> <sharedTimeNs>` proves the timing mechanism, but it only schedules fleet-wide cues. Ordinary `/p/*` values and spatial terms do not presently carry scheduled start times. A real sequencer therefore needs a ratified extension with the semantics of:

- stage a content-addressed behaviour plan;
- activate a plan instance at a shared time;
- replace or cancel a track generation at a shared time;
- report which plan revision is ready or running.

The exact OSC grammar belongs in a later contract decision. Each operation must remain full-state and idempotent. Repeating an activation must not create a second playback instance.

A track selector also does not make an existing `/cue` selective: ratified cues are broadcast-only and fleet-wide. Initially, cue clips should either be explicitly fleet-wide or require a new selector-bearing scheduled-trigger term. Quietly treating `/cue` as group-addressable would create a false capability.

## Compile behaviours into smart node-side terms

The LAN should carry descriptions of change, not samples of change.

### Parameter ramps

A clip containing a long filter sweep should compile to its destination and breakpoint durations, delivered once shortly before its shared start. The node waits against its local converted deadline and hands the engine relative breakpoint automation. The engine never receives an absolute timestamp, preserving the 32-bit PD boundary.

Curves should be approximated to a bounded error using as few breakpoints as necessary. The compiler can warn when a curve requires an implausibly dense approximation. Vezér’s clear timelines, interpolated keyframes and mixed control tracks are worth borrowing for the inspector; its frame-oriented OSC output is not the transport model to copy. [Vezér](https://imimot.com/vezer/)

### Spatial movement and fields

Moving a point by transmitting `/pt` frames at 20–30 Hz is acceptable for direct manipulation, but wasteful for a known ten-minute trajectory. A scheduled point trajectory should instead contain compact path segments and relative durations. Each node evaluates the point position from its local clock, then performs the existing proximity decomposition at its element positions.

Scatter, gradients and noise should become declared provided terms rather than secretly modifying patch parameters. A field plan could carry a field identity, geometry, duration, seed and evolution parameters. Nodes evaluate the same analytic function at their own positions and provide the resulting scalar to the patch. The patch remains responsible for mapping that scalar to gain, filter, playback or another meaning.

A video texture could eventually compile into these same fields or into simplified automation. Streaming per-seat pixels would recreate the reverted O(N) gain problem.

### Randomness

Randomness needs two distinct modes:

- **Leader-chosen randomness** for structural decisions such as follow actions, where the whole installation must agree on one result.
- **Node-derived randomness** for scatter, where each node deliberately receives a different but reproducible result.

Node variation should be derived from stable inputs such as session seed, clip instance, loop index, Seat identity and element index. It must not depend on packet arrival order or an unseeded local generator. TidalCycles gets the central idea right: cyclical patterns can be queried in time, transformed compositionally, and varied with deterministic randomness rather than stored as enormous event lists. [Tidal patterns](https://tidalcycles.org/docs/reference/patterns/), [Tidal randomness](https://tidalcycles.org/docs/reference/randomness/)

### Stage once, launch cheaply

Compiled plans should be content-addressed and cached on nodes. Editing or arming stages a missing plan; repeated launches send only a small activation containing the plan hash, generation, seed and shared start time.

Readiness should be observable. A scene launch can then distinguish:

- all intended nodes ready;
- some nodes missing the plan;
- selector membership changed since staging;
- launch lead time no longer sufficient.

For installation reliability, “launch anyway,” “move to next quantum,” and “abort” should be explicit policies rather than timing accidents.

## Quantization, follow actions and transitions

Ableton Link’s most reusable abstraction is not distributed transport control but a consistent mapping among beat, time, tempo and quantum. Its captured session-state model also avoids obtaining internally inconsistent timing values during one scheduling calculation. bopOS can use the same ideas while keeping the dashboard as its fleet clock leader. Link participation could later allow Ableton or norns to supply musical tempo and phase without giving them ownership of device scheduling. [Ableton Link concepts](https://ableton.github.io/link/)

A launch quantum belongs to the launch request, resolved in this order:

1. explicit clip quantum;
2. scene quantum;
3. session global quantum.

The UI should show **queued**, **committed**, **playing** and **stopping** as distinct states. If the required staging lead time is missed, move the entire launch to the next boundary. Sending “as soon as possible” to each node would destroy fleet coherence.

Follow actions should be based on logical clip time, not a callback saying that some Python task happened to finish. At the decision boundary, the reducer chooses once and records the result. Useful actions include stop, repeat, next, previous, named target and weighted random target. The action can occur after a duration or loop count, but these are different semantics and should not be conflated.

Ableton demonstrates both the generative value and the traps: follow actions can be quantized, scene follows can take precedence over clip follows, and random/next behaviour occurs within defined clip groups. bopOS should borrow the visible queued state, weighted choices and global “disable follows” control. [Ableton clip launching and follow actions](https://www.ableton.com/en/live-manual/12/launching-clips/)

There must be deterministic arbitration when several actions target the same boundary:

1. emergency stop or global follow-disable;
2. explicit user scene launch;
3. scene follow action;
4. explicit clip launch;
5. clip follow action.

Lower-priority decisions should be cancelled before they create playback instances.

### What a scene crossfade can mean

A generic “crossfade scenes” control sounds simple but behaviours are not all blendable. The safest semantics are a coordinated takeover:

- **Continuous parameters:** capture the sequencer’s current commanded value and ramp to the incoming clip’s declared initial value.
- **Compatible fields or trajectories:** morph between descriptors node-side when both use the same provided-term type.
- **Discrete cues:** use a declared cutover boundary; cues cannot be faded.
- **Scatter processes:** reduce outgoing event probability and increase incoming probability only if that behaviour explicitly supports density morphing.
- **Hold cells:** remain untouched.
- **Stop cells:** execute the outgoing clip’s declared release policy.

At the transition start, affected tracks receive new generations atomically. Outgoing future events become invalid even if their packets arrived earlier.

Cross-track collisions need a hard rule. A reasonable default is single-writer ownership for every continuous target, with launch blocked on conflict. Explicitly configured priority or blend modes could come later. Silently summing two behaviour tracks would turn an organisational lane into an accidental mixer and would risk violating the framework/patch seam.

## Prior art worth stealing

- **Ableton Session View:** the clip/track/scene performance surface, exclusive playback within a track, obvious queued states, follow actions and the distinction between scene stop buttons and unaffected tracks. Do not inherit its assumption that every transition is fundamentally an audio-clip transition. [Session View](https://www.ableton.com/en/manual/session-view/)
- **Ableton Link:** beat/time/tempo mapping, quantum-aligned starts and consistent captured clock state. Use it as an optional musical peer, not as a replacement for bopOS’s measured per-node offsets.
- **TidalCycles:** cyclic time, behaviour as a queryable pattern, deterministic randomness, and transformations that produce compact intent. Keep that semantic power without choosing syntax yet.
- **Vezér:** a legible value-timeline inspector, interpolation choices, loop ranges and cues across heterogeneous control types. Bake those curves into ramps instead of emitting every frame across Wi-Fi.
- **QLab:** explicit targets, visible broken/disarmed cues, preview versus full sequence execution, and the distinction between auto-continue after a delay and auto-follow after completion. bopOS should similarly provide audition, arm/disarm, GO and an unmistakable global stop. [QLab cue sequences](https://qlab.app/docs/v5/fundamentals/cue-sequences/), [QLab fades](https://qlab.app/docs/v5/audio/fading-audio/)
- **monome norns/grid:** a small, immediate performance surface whose meaning is defined by the running instrument, plus a clock API that clearly separates beat-synchronized waits from real-time sleeps. The grid’s restrained queued/active visual vocabulary is a better model than a dense DAW clone. [norns clocks](https://monome.org/docs/norns/clocks/), [monome grid](https://monome.org/docs/grid/)
- **SuperCollider patterns:** stateless pattern definitions, stateful streams, arbitrary key/value events and replaceable event prototypes. These map cleanly to `ClipPlan`, `PlaybackInstance` and transport adapters.

## Three non-obvious failure modes

### 1. Ghost events from the future

Pre-scheduling improves timing but makes stop and edit operations non-local. A node that missed a cancellation can fire an old cue or ramp seconds after the dashboard says the clip stopped—particularly after a network partition or dashboard restart.

Every staged action therefore needs a session epoch, track generation and bounded validity. Replacement should install a generation fence at a shared time; nodes discard older future actions. On restart, the dashboard must create a new epoch and explicitly invalidate the old one rather than attempting to resume from UI state alone.

### 2. Compact plans becoming unreliable giant UDP packets

A field or breakpoint program may be tiny compared with a stream yet still exceed the network MTU. IP fragmentation is especially dangerous on lossy Wi-Fi broadcast: losing one fragment loses the entire message, and a hundred nodes can disagree about whether they received it.

Plan staging needs bounded chunks, hashes, reassembly limits and readiness receipts. Launch packets should remain comfortably within one datagram and should only reference already verified content. Clock sync and emergency control must never queue behind plan transfer.

### 3. Smart-node work destabilising the audio it was meant to protect

Moving field evaluation, scatter and path interpolation onto Pi Zero 2 W nodes saves LAN capacity but consumes CPU beside the sound engine. If all nodes evaluate a complex field at the same synchronized instant, the design can create fleet-wide CPU spikes and audio dropouts.

Each compiled plan should include a node-cost estimate and fixed evaluation-rate budget. Expensive analytic work should be simplified or pre-baked; noncritical field updates can be phase-staggered without changing their shared mathematical time. The simulator can validate protocol behaviour, but the feature should not be considered production-ready until the audible rig measures worst-case node CPU, scheduler jitter and audio underruns.