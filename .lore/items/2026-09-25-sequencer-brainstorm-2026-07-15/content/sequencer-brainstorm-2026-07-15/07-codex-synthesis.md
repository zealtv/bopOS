# Codex synthesis — what the independent perspectives add or challenge

*Fable, 2026-07-15. Two GPT-5.5 reports were commissioned mid-session
(`90-…` clip launcher, `91-…` spatial fields/video). This note extracts what
they genuinely add beyond §02–§05, and where they push back.*

## From `91` (spatial fields & video) — strong report, adopt most of it

**Confirms the core bets** independently: analytic fields + offline baking as
the recommended v1, live sampling as a gated experimental bridge, `/field
<id> <element> <v>` shaped-scalar delivery as the seam-pure choice (it
explicitly warns that framework-side param composition would "recreate the
composition mistake that the `/pt` design removed").

**Genuine additions worth folding into the design session agenda:**

- **Transforms as the multiplier:** give every primitive one shared transform
  set (origin, rotation, X/Y scale, repeat/mirror/clamp, phase + velocity)
  instead of growing the primitive list — linear+repeat = stripes,
  radial+repeat = rings. Add **line/segment distance** as a fifth primitive
  (scanning bars, drawn boundaries). Bounded modifier chain (invert, remap,
  smoothstep, wrap-shapes, quantize; ≤2 sources, ≤4 modifiers) rather than a
  node-graph editor — protects the plain-text clip form.
- **Lossy-launch discipline:** repeat identical full-state definitions ~3×
  before a scheduled start; give fields a slot + monotonically increasing
  revision; periodic current-state digest. Sharpens my "slow re-assert".
- **"Silence = hold" needs a field-specific reading:** silence holds the
  *programme* (field keeps evolving node-side); explicit stop freezes or
  clears. Worth ratifying as exact words.
- **Deterministic noise must name a versioned algorithm** — "seed 42" is not
  reproducible across library upgrades. Applies equally to the scatter hash
  and seat-personality hash (§06).
- **Live-sampling form, if ever built:** not per-seat unicasts but an
  *atomic broadcast ramp frame* (all seats' start/end values, revisioned,
  chunked under ~1200 B, applied only when complete). Its bandwidth tables
  (100 seats @5 Hz ≈ 62 kbit/s payload before airtime penalties) are the
  numbers to quote when someone asks why streaming is banned.
- **Bake UX:** report approximation error + size after baking; **stale
  badges** when the video, room geometry, or seat positions change under a
  bake; keep source + transform + tolerance alongside generated curves so
  bakes are reversible/regenerable. Per-seat lane distribution only (never
  ship the whole fleet bake to every node).
- **Calibration over mapping:** the finicky part of video UX is the
  room↔texture transform, not channel mapping — solve with fit/fill/rotate
  presets and a checkerboard test pattern rendered across the fleet map.
  Lighting-console lessons (ETC pixel maps, MadMapper fixtures): patch
  positions once, preview at the fixtures, per-seat "flash/identify".
- **Cost surfacing in the inspector:** every clip type shows its network
  cost class before launch (fields ≈ nothing; live sampling shows rate ×
  channels with MTU warnings; bakes show asset size + distribution
  readiness). Cheap to build, prevents the Belief System failure mode
  culturally as well as technically.

**Pushback to weigh:** it suggests a node rebooting mid-clip should *seek*
into running baked automation from the shared timeline — that implies nodes
know clip-transport position, which enlarges the contract. Fine to note as a
later option; the honest v1 fallback it names (hold until next launch)
matches the catch-up philosophy.

## From `90` (clip launcher) — strong on execution discipline; one big divergence

**Confirms:** tracks as organisational lanes, one clip per track as the
conflict rule, compile-into-compact-terms as the identity, single-writer
ownership of continuous targets, deterministic seeded randomness in two modes
(leader-chosen for structure, node-derived for scatter — a distinction §04
should adopt as vocabulary), and "the LAN carries descriptions of change, not
samples of change."

**Genuine additions worth adopting:**

- **Scene cells need three states — launch / stop / hold.** An empty cell
  can't mean all three; Ableton's removable stop buttons solve it visually.
  Directly relevant to "change the motion, leave the ambience running."
  Cheap to include from Rung 1. Adopt.
- **Source text vs compiled plan as separate artifacts** (SC's
  pattern-vs-stream distinction): editing creates a new immutable revision
  and never mutates a running clip. Also gives clips **resource claims**
  (cues fired, params written, selectors used) — validated against manifests
  before launch, so conflicts and undeclared names surface as pre-launch
  badges. Adopt as backend architecture from Rung 1.
- **One authoritative reducer + priority-queue scheduler**, not a sleeping
  asyncio task per clip — and a fixed arbitration order when several actions
  hit the same quantum boundary (emergency stop > user scene launch > scene
  follow > user clip launch > clip follow). Adopt.
- **Queued / committed / playing / stopping as visible UI states**, QLab-style
  arm/audition/GO discipline, a global "disable follows" control, and
  *weighted* random follow actions. All cheap, all good.
- **Ghost events from the future** (failure mode 1): pre-scheduled actions
  need a session epoch + track generation fence so a node that missed a
  cancellation can't fire a stale cue after a partition or dashboard restart.
  This is the strongest single catch in either report — it belongs in the
  contract discussion next to lookahead/cancel (decision list #11).
- **MTU discipline** (failure mode 2): even compact plans can exceed one
  datagram; fragmentation on lossy broadcast is fatal. Launch packets must
  stay single-datagram and reference pre-staged, hash-verified content.
- **Node CPU as a budget** (failure mode 3): synchronized field evaluation
  can spike every Pi at the same instant — phase-stagger non-critical
  evaluation, estimate node cost per plan, and gate "production-ready" on
  audible-rig CPU/underrun measurement, not simfleet alone.
- **`/cue` is fleet-wide, full stop:** a track selector doesn't make cues
  group-addressable; pretending otherwise fakes a capability. Group-targeted
  scheduled triggers need their own ratified term. Correct and worth stating
  in the decision list (#7/#8 gain a sibling).

**The big divergence to weigh at the design session:** report 90 proposes a
full **stage-then-activate** model — content-addressed behaviour plans cached
on nodes, activations by hash at a shared time, readiness reports, generation
fences. That is a *substantially* smarter node than today's bopos.py and a
much bigger contract ask than my §02 sketch (short-horizon lookahead from the
dashboard, nodes stay dumb-ish). My read: the staging model is where a mature
system ends up (it is QLab's arm/GO and it solves ghost events at the root),
but it is *not* the first slice — Rungs 0–3 work with today's contract plus
short horizons, and staging can arrive later as the delivery mechanism for
ramp/field plans without changing the grid model or clip semantics. Frame it
to Bob as "v2 delivery architecture, designed-for but not built first."

## Net effect on the decision list (§08)

Additions: scene-cell three-state semantics (#12 gains a sub-question);
session epoch / generation fencing joins #11; "silence holds the programme"
wording joins #4; named+versioned noise/hash algorithms join #4 and #6;
stage-then-activate vs short-horizon becomes its own headline question; node
CPU budgeting joins the `/field` term discussion; group-addressable scheduled
triggers join #7/#8.
