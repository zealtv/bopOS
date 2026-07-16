# Core proposal — the bopOS clip launcher

*Fable brainstorm, 2026-07-15. Illustrative syntax throughout — the real
language is a co-design session with Bob. Semantics and architecture are the
substance here.*

## The frame: a compiler, not a streamer

The Belief System rig failed where it *streamed* (automation curves → network
flood) and succeeded where it *organised* (track = behaviour, follow actions →
generative flow). bopOS has spent two months building the opposite of MIDI: a
wire where the fleet already knows how to expand compact intent — cues on a
shared clock, `/pt` node-side decomposition, manifest-declared params, ramp
pairs, groups.

So the sequencer's identity: **the clip launcher is a behaviour compiler.**
A clip is a small script; the interpreter runs in the dashboard backend; its
output is not a firehose of values but the *cheapest possible wire form* of
each gesture:

| gesture in the clip | wire form | cost |
|---|---|---|
| "fire cue `snap` on group 1 at bar 3" | one `/cue` broadcast, pre-scheduled on the shared clock | 1 msg |
| "sweep gain 0→1 over 8s on all" | one param-ramp message, node/patch decomposes | 1 msg |
| "orbit a point around the room" | `/pt` frames at 20–30 Hz (existing budget) or a parametric orbit primitive | low, bounded |
| "gradient sweeps east→west over 20s" | one field primitive broadcast, evaluated node-side at each seat (§04) | 1 msg |
| "scatter plinks across random seats" | seeded probability on a broadcast cue — nodes coin-flip deterministically | 1 msg per event burst |

The grid, tracks, and follow actions are the *composition* layer on top; the
compiler is what makes it feasible on WiFi broadcast.

## The grid model (steal Ableton's, then simplify honestly)

- **Tracks are vertical lanes = named behaviours.** Exactly the organisational
  affordance that worked in Belief System. A track carries defaults its clips
  inherit: a **target selector** (`all`, `g2`, `007`), optionally an **address
  prefix** (`/p/fx/`), optionally a **clip type** (below). Scripts stay
  compact because the track answers "who and where"; the clip answers "what
  and when".
- **One playing clip per track** (Ableton's rule). This is not a limitation,
  it is the *conflict-resolution semantics*: launching a clip supersedes its
  track-mates. Because fleet commands are full-state and idempotent, takeover
  is trivially safe — the new clip simply starts asserting values.
- **Scene column on the right**: launches a row. A scene is just "launch these
  clips together", nothing more, v1.
- **Follow actions per clip**: `after n plays → next | previous | random |
  other | stop`, plus launch quantization (`immediate | beat | bar | phrase`).
  This is the whole generative-autonomy story and it is cheap to implement —
  it is a state machine in the backend, zero wire cost.
- **Clip inspector = codebox** (Bob's sketch): click a clip, see its script,
  its oneshot/loop toggle, its follow action, its target override.

### Tempo, or the absence of one

The launcher needs a transport: a tempo, a bar/beat grid for quantization, and
a phase everyone agrees on. But bopOS shows are often *textural* — so make
musical time optional per clip: a clip declares whether it thinks in
`bars.beats` or in seconds. The transport maps both onto the shared leader
clock. (An installation that never sets a tempo just gets clips in seconds
with `immediate` launches — still a fully working show.)

## Clip types: polymorphic clips, one chrome

Rather than one language straining to express rhythm, ramps, geometry, *and*
video, let clips come in **types** that share the same grid/launch/loop/follow
chrome but open different inspectors. This is the single strongest synthesis
of Bob's two intuitions — the video idea stops being a separate system and
becomes *a clip type in the same launcher*:

1. **Cue clip** — a timed list of cue firings + waits. Renders as a picker
   over the *manifest-declared cues* of the loaded patch (no guessing).
   The v0 show-driver: Bob already believes cues alone can drive a show.
2. **Pattern clip** — rhythmic step/notation sequencing of cues or param hits
   (where intermals-style rhythm notation would eventually live).
3. **Ramp clip** — breakpoint automation per parameter, *compiled to
   node-decomposed ramp segments*, not streamed. Drawn or typed
   (`.bopseq`-style `param v1 t1 v2 t2 …` pairs are exactly this).
4. **Point clip** — animates `/pt` points: authored paths, orbits, particles
   (the Belief System particle system reborn as a clip you can launch).
5. **Field clip** — a spatial primitive (linear/radial/spinning gradient,
   noise) with animation parameters, delivered per §04.
6. **Video clip** — a video/canvas texture sampled at seat positions,
   delivered per §04 (baked or live-linearised).
7. **Script clip** — the escape hatch: the full scene language, which can do
   everything the sugared types do. **Design rule: every sugared clip type
   must round-trip to script** — "open as script" on any clip. The sugared
   inspectors are then just *views over the language*, which keeps the system
   honest, keeps everything diffable text, and keeps agent-writability
   first-class.

v1 does not need all seven. It needs the chrome + two types (cue, ramp) to be
a real instrument. The type system is the extensibility story.

## Scheduling architecture (backend)

- **Interpreter with lookahead.** The transport ticks in the dashboard
  backend (asyncio). Each playing clip is evaluated **ahead of real time**
  (~0.5–2 s horizon), emitting timestamped intents. Time-critical intents
  (cue firings) go out early as scheduled `/cue <id> <sharedTimeNs>` — WiFi
  jitter becomes irrelevant because the *node* holds the deadline. Continuous
  intents compile to ramps/fields whose node-side evolution covers the
  horizon.
- **Lookahead needs a cancel.** Pre-scheduled cues that a stop/retrigger
  should revoke imply either (a) keep the horizon short for cancellable
  things, or (b) an additive `/cue/cancel <id>` term someday. v1: short
  horizon (≤ launch quantum), problem mostly dissolves.
- **Last-writer-wins per address.** Two clips touching the same param on the
  same selector: the later write wins, no mixing, v1. Parameter-level
  crossfade/mixing is a known hard problem (Ableton doesn't solve it either —
  it has one clip per track for this reason). Defer scene crossfading;
  takeover-on-launch is the honest v1 semantics.
- **Determinism and the seed.** Clips take the run seed (run context already
  exists) so `random` in a script is reproducible per run. Scatter uses
  seeded node-side coin-flips (§04) so even fleet-random behaviour replays.
- **State on stop:** a clip stopping leaves values where they are (full-state
  world — nothing "returns to default" unless a clip says so). A scene's
  first clip can open with explicit resets; consider a per-track "release
  ramp" later.

## Where it lives

**A dashboard tab backed by a separable engine module.** Arguments:

- The IA already reserves the Sequencer tab (ratified 2026-07-15).
- The backend already owns the leader clock, positions, groups, params — a
  standalone app would have to re-speak all of that over yet another link.
- Separability discipline: the interpreter/transport lives in its own module
  (`sequencer/`), talks to the relay through the same internal API the tabs
  use, is testable headless against simfleet, and could be lifted into a
  standalone process later if the dashboard becomes a liability (the thread's
  named fallback, kept genuinely open).
- **Shows are files.** A show is a directory: `show.json` (grid layout,
  tracks, follow actions) + one text file per clip. Git-friendly,
  agent-writable, diffable — an LLM can compose a show by writing files, and
  the launcher is also a *file browser* over that directory. (Same philosophy
  that made the patch manifest work.)

## What stays out (explicitly)

- **No syntax ratification here** — examples are illustrative.
- **No parameter mixing/crossfading v1** — takeover semantics.
- **No MIDI/DAW bridge v1** — but note the door: a tiny OSC/MIDI input shim
  could launch clips from a Launchpad later; the grid model maps 1:1.
- **The auxiliary multichannel system** (Belief System's second sound system)
  is out of scope, but nothing prevents a track whose selector is an external
  OSC destination — tracks-as-destinations generalises cleanly. Worth one
  line in the design session.
