# Making it perform flexibly — the OSC surface and what the node's "patch" is

Bob: *"would be good to think about how to make something like this that could
be small, cheap, and flexible (ie define the right osc address and behaviour so
it can perform flexibly. the trigger layer is pretty close to that)."*

He is right that it is close, and the reason is worth naming precisely, because
it also tells you what **not** to design.

## 1. The reframe: restrict the patch, not the framework

"Restricted feature set" is the natural way to say it, but taken literally it is
the expensive version and it needs a contract revision.

The cheap version falls straight out of the §1 seam law:

> bopOS **provides** named, full-state terms the patch subscribes to and enacts
> … A patch that doesn't consume a term simply isn't controllable by it —
> **unconsumed is a legal no-op, never an error.**

So: **the firmware implements the whole framework surface; the node's *patch* is
what is small.** A manifest that declares four params and six events is already
a completely legal bopOS patch. Nothing in the dashboard branches, nothing in
the contract moves, and §14's *"no per-host branching in message semantics"* is
honoured rather than argued with.

That is the design. The restriction lives in the manifest, which is the one
place the system already expects instruments to differ from each other.

Two things genuinely cannot be dodged this way, because they are framework
rather than patch: the **fetch tier** (a node that will not pull 300MB of
samples is making a framework-level statement) and **`shutdown`** (there is no
patch-level answer to "halt the machine"). Those, and only those, need declared
facts in `/os/report`. See `open-questions.md`.

## 2. Why the trigger layer is already the right shape

Contract §3.2 does the hard part by **declining to fix meaning**:

> The element list has arity 0–3. Elements are free-form 32-bit OSC floats,
> identified by 0-based position; **meanings such as note/velocity/duration are
> patch convention, not framework semantics.**

and

> Nodes schedule **every well-formed fire without consulting the manifest**.
> Dashboard surfaces badge undeclared identities … declaration is documentation
> and authoring metadata, **not a delivery gate**.

Three consequences that are all flexibility for free:

1. **Three floats per fire, meaning whatever the instrument says they mean.**
   The framework owns scheduling and target matching; it never owns the
   semantics. A sampler can read them as `(variant, gain, rate)` and a solenoid
   node can read them as `(which, force, dwell)` and neither needs permission.
2. **Identities are hierarchical** — 1–8 segments of `[A-Za-z0-9_-]+`. So
   `/e/perc/hat`, `/e/perc/rim`, `/e/voice/breath` organise a bank without a
   flat namespace, and the path is the natural key into a sample map.
3. **Undeclared identities still fire.** A node can be *played* with addresses
   its manifest never mentioned. Live improvisation against a node needs no
   manifest edit and no redistribution — which, given that patch distribution is
   the slow, crash-loop-prone path (`feasibility.md` §2), is a much bigger
   practical gift than it first looks.

## 3. What one fire should be able to say

The expressive knobs that cost nearly nothing in a fixed-function mixer, and so
should all exist:

- **variant / sample select** — `e0` as an index into the bank named by the
  identity. One identity is a whole bank, which keeps the manifest from
  exploding into one entry per sample.
- **gain** — `e1`.
- **playback rate / pitch** — `e2`. Linear-interpolated resampling is cheap and
  turns a bank of 8 samples into a usable instrument.
- **choke groups** — a manifest property of the identity, not a fire argument.
  A hat that cuts the open hat is the difference between a sampler and a
  soundboard.
- **one-shot vs sustain** — with a release on a matching stop, if a `stop`
  spelling is wanted. Default one-shot.
- **short attack/release** — declared per identity, not per fire. Prevents
  clicks, costs nothing.

Note what is deliberately absent: no envelope graphs, no routing matrix, no
per-fire filter settings, no modulation sources. Those are where a sampler turns
into a synthesis language, and a synthesis language is what Pd and
SuperCollider are already for. The line to hold is that **a fire selects and
shapes a sound; it does not describe one.**

## 4. The seed is the compositional gift, and it is already in the contract

§4.2 delivers run context at launch: `seed <int ≤6 digits>`, `run-id`, `patch`,
`assets`, `version`, `patch-fingerprint`, `groups`.

A node with a seed can do **reproducible per-node variation**: round-robin
ordering, random-from-bank selection, small pitch and timing humanisation — all
deterministic within a run, all different between nodes, all recoverable by
re-running the same seed.

At 12 nodes that is a nicety. At 60 cheap nodes it is arguably the whole point:
a fleet that is *the same instrument, differently*, without authoring 60
variations by hand. And it needs no new wire form at all — the term is already
provided and already launch-delivered.

Worth pairing with the §3.3 note that sync LFO phase is **clock-anchored by
default**, with `f` (free) opting into per-device random phase *for deliberate
decorrelation*. The contract has already thought about when a fleet should move
together and when it should not. A trigger node should inherit that thinking
rather than reinvent it.

## 5. What the `/p/*` surface should expose

Few params, but the right ones — because porting `paramgen.py` (see
`feasibility.md` §2) means **every numeric param gets fades, segment lists,
loops and six LFO shapes for free**, from the existing dashboard, with no node
work. That is the flexibility multiplier and it is the strongest single argument
for porting the whole grammar rather than a subset.

A reasonable starting declaration:

- `gain` — the instrument's own level, distinct from the framework `master`
- per-bank gain, if banks exist
- `rate` — global playback-rate offset; an LFO on this is a tape-wobble for free
- one cheap global filter cutoff (one-pole or SVF), if the CPU is there
- `density` or similar, only if the node ever generates its own fires

An LFO on `gain` and a slow fade on `rate`, authored from the existing Control
panel, is a surprising amount of performance from a $20 box — and none of it is
new protocol.

## 6. The manifest is the instrument definition

On a Pi the patch is a directory of `.pd` files plus `bopos.patch.json`. On an
S3 the firmware is fixed, so **the manifest *is* the instrument** — it declares
the events, the params, and (in extra keys) the sample bindings.

Measured: `manifest.validate()` passes unknown top-level keys through untouched,
so those bindings can live in the same `bopos.patch.json` that the Pi-side
validator reads, without touching it.

The consequence worth appreciating: **an S3 node is configured by the same
artefact, distributed by the same mechanism, and rendered on the same dashboard
control panel as a Pi node.** Bob's manifest editor already builds its events
and params. That is the whole bopOS value proposition — one contract across
heterogeneous nodes — actually collected rather than promised.

## 7. The thing to resist

The temptation, once a fixed-function node exists, is to keep adding to the
firmware until it is a bad synthesiser. Two guards:

- **Every addition must be expressible in the existing planes.** If it needs a
  new plane or a new verb, it is probably a different instrument.
- **If the answer is "we'd need an envelope editor", it belongs in Pd or SC.**
  The horizon note's Force 2 exists to make SuperCollider a real peer; a
  capable engine is the answer to "this needs to be more capable", not a
  firmware feature branch.
