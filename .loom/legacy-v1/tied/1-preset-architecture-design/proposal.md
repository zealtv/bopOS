# Proposal — the preset primitive

**Status: RATIFIED by Bob, 2026-07-28 (live session) — all four forks ruled in
§10; see `decisions.md`. Nothing here is implemented yet, and a review stitch
(`41-preset-primitive/2-proposal-review`) runs before anything is built.**
Date: 2026-07-28. Stitch: `41-preset-primitive/1-preset-architecture-design`.

Sources already ruled and *not* re-litigated here: presets live in the patch
folder; shows stay in `dashboard/shows/`; individual params stay targetable
with hard takeover; presets do not capture events; venue presets retire;
collections start as show steps; group targets resolve by name; content is
referenced by `{name, fingerprint}` with derived non-blocking drift.

---

## 0. The headline

**A preset is not a wire concept.** It is a stored argument list per parameter
identity, belonging to a patch, replayed through the `/p/*` messages that
already exist. The framework gains no preset plane, no preset state on the
node, and no new ownership model.

The whole design is three claims:

1. **A preset entry *is* the wire argument list** for `/p/<identity>`. A value
   preset stores `[0.75]`; a generator preset stores `["lfo","sine",0,1,"10s"]`.
   Applying a preset is a fan-out of exactly those messages. `OSCBridge.set_param`
   already takes a full argument list (`osc_bridge.py:426`), so the application
   path exists today.
2. **Morphing into a preset is one additive `/p/*` grammar form**, `morph`,
   which interpolates the *generator argument vector* rather than crossfading
   two generator outputs. One slot, one owner, last-writer-wins — §3.3's model
   is preserved rather than extended.
3. **Everything else is dashboard-side**: storage, drift, targeting, show
   references, capture-as-step.

Wire delta: **one grammar form and one distribution exclusion.** That is the
entire contract amendment.

---

## 1. Identity and storage (Q1)

### Layout

```
patches/<patch>/
  bopos.patch.json
  main.pd
  presets/
    dawn.json
    full-tilt.json
```

One file per preset. Rationale: git-diffable per preset, rename is a file
rename, two people (or two agents) editing different presets never conflict,
and deleting a preset is deleting a file. A single `presets.json` would make
every save a whole-file rewrite.

### File shape

```json
{
  "bopos_preset": 1,
  "name": "Dawn",
  "saved": "2026-07-28T11:04:00Z",
  "schema": "sha256:1f0c…",
  "params": {
    "gain": [0.75],
    "instrument/marimba/gain": ["lfo", "sine", 0, 1, "10s", "p:0.25"],
    "echo": [1],
    "voice": ["aah"]
  }
}
```

- `name` is the display name; the filename is its slug (the existing 48-char
  `[^\w-]` slug rule from `save_preset` carries over).
- `params` is a **sparse** map from qualified identity to the argument list.
- `schema` is a **parameter-schema fingerprint**, not the patch fingerprint —
  see drift below.
- No `master`, no mute, no positions, no assignments. Those are site-layer
  (R4: sound identity in the patch, mix state in the site). Today's venue
  preset captured `master`; that capture retires with it.

### Sparse by design

A preset stores only the params it captures; omitted params are **untouched**
on apply. This is not layering or ownership — it is simply sending fewer
messages. It buys three things for free:

- A "reverb preset" and a "melody preset" compose by applying in sequence.
- Saving from an All/Group card, where the panel shows aggregates, has an
  obvious rule: **params whose value is mixed across the target are omitted.**
- Manifest drift degrades to the same mechanism: a param that has gone away
  is just another param the preset does not carry.

The save UI defaults to capture-everything, with per-row include/exclude on
the panel (the row already has the affordance space from the control-panel
design language).

### What a capture reads, per param

| Live state on the target | Captured |
|---|---|
| plain value | the durable value, `[v]` |
| periodic generator running (`lfo`, `loop`) | its argument list verbatim — full-state and idempotent by §3.3 |
| fade in flight | the fade **destination** (already the durable value) — a fade is a transition, not a state |
| morph in flight | the current interpolated generator spec (same source as morph catch-up, §4) |
| mixed across an aggregate target | omitted |
| `kind: "text"` | the string, `["aah"]` — set-only, no generator forms |
| event | never (ruled) |

`text` params are **in scope**, contrary to the stitch's original framing:
`kind: "text"` became a ratified manifest kind on 2026-07-28 (§8). What stays
deferred is the *automation grammar* for strings, which a preset does not need
— it stores a set-only full-state value. Excluding text would make a preset an
incomplete snapshot of a patch that legitimately declares text params.

### Distribution: `presets/` is host-only

The patch fingerprint is a hash over every file in the patch directory
(`identity.directory_manifest`). If presets counted, **saving a preset would
restage the fleet patch, refetch it on every node, and restart every engine
mid-sculpt.** That is unacceptable for the core workflow (save presets while
patching).

Proposal: `presets/` becomes a named **host-only patch subdirectory** —
excluded from `identity._walk_files`, and therefore from the distribution
manifest, the fingerprint, and prune-to-manifest convergence. Because the rule
lives in `python/identity.py`, host and node compute the identical identity, so
nothing drifts. Nodes never receive presets, which is correct: apply is
dashboard-driven fan-out (Q7 below).

Presets still *travel with the patch* through git and through host-to-host
copies, which is what the ruling asked for. They just do not travel over the
fetch path.

Alternative rejected: a dot-directory `.presets/` gets the exclusion free
(dotfiles are already skipped) but reads as machine state rather than authored
content, and hides it from casual `ls`. Presets are authored material. Prefer
the explicit named exclusion.

### Drift policy (the live part of Q1)

Presets fingerprint the **control schema**, not the patch directory: the
canonical JSON of the sorted list of `{identity, kind, min, max, options
count}` from `bopos.patch.json`. Editing `main.pd`, adding a sample, or
rewording a description therefore does **not** invalidate a preset — only
changing what is controllable does.

On apply, the preset is resolved against the current manifest, per entry:

| Condition | Behaviour |
|---|---|
| identity present, kind unchanged, value in range | apply |
| identity present, numeric range narrowed | **clamp** and apply, count as adjusted |
| identity present, kind changed | skip, count as dropped |
| identity absent | skip, count as dropped |
| identity in manifest, absent from preset | untouched (sparse) |

Consistent with R2, the verdict is **derived, never stored, and never
blocking**: a preset always applies as much as it can and reports what it
could not. The `schema` field is a fast path for "is there drift at all"; the
per-entry resolution is the authority. Warnings surface in the same two places
the ratified drift check does (Show tab, show load) plus inline on the control
panel's preset row.

---

## 2. Shape and the kind grammar (Q2)

A preset entry is the argument list of the message that reproduces the state.
That is the whole shape. Consequences:

- No preset-specific value schema to keep in sync with the manifest kinds.
  `toggle` is `[0|1]`, `enum` is `[index]`, `int` is `[n]`, `float` is `[x]`,
  `text` is `["…"]` — because that is already what the wire carries.
- Generators are stored in the same slot without a discriminator, because
  `ParamSpec.parse` (browser) and `parse_message` (python) already tell a
  value from a generator by inspecting the argument list. The control panel's
  generator drawer stores drafts as `entry.args` today
  (`control-surface.js:197`); a preset is the same bytes, at rest.
- A preset round-trips through the existing Monitor/console rendering and the
  ratified pill taxonomy with no new encoder.

---

## 3. Application path (Q3) — confirmed, reuse

Apply is a dashboard-side fan-out over the existing selector machinery:

```
apply_preset {patch, name, scope, id, duration_ms?, curve?}
  → resolve target seats via the existing scope resolution
  → resolve entries against the staged schema (active_param_identities)
  → for each identity: osc.set_param(selector, identity, args)
  → update seat/device durable params, broadcast, persist
```

This is today's `load_preset` with the payload coming from the patch folder
instead of installation state, and the values allowed to be argument lists
instead of scalars. No new selector concept, no new plane, no new
acknowledgement. Group targets resolve by name at the dashboard boundary per
F1; the wire still sees `g<id>`.

**Hard takeover is automatic and needs no code**: each fan-out message is an
ordinary write to a single-owner slot, so afterwards every param is exactly as
grabbable as it was before, including mid-morph.

**Applied-preset tracking.** State gains a per-target `applied_preset`
`{patch, name}` marker, set on apply. It records **provenance** — "this target
was last recalled from Dawn" — and is cleared only by recalling another preset
or choosing none. Whether the target still *equals* that preset is a separate
axis, and it is **derived** at render time by comparing the preset's captured
entries against current durable values and automation entries, never stored as
a flag. The panel shows `Dawn` or `Dawn *`. See §10 F4 for why.

---

## 4. Interpolation (Q4) — recommend generator-argument interpolation

### The three candidates

**A. Output crossfade (the mix function).** Two live sources per param plus a
ramped mix coefficient. It handles any pair of sources including shape→shape.
Costs: it breaks §3.3's "one generator slot, last message wins" — the model
that hard takeover is built on; it doubles per-param generator evaluation at
the 30–50 Hz control tick on Pi Zero-class hardware; it needs a second slot's
worth of state, a mid-fade takeover state machine (a direct write must kill
*both* sources), and a genuinely new DSP primitive on the node. It is the
largest contract change of the three and it is the one that "flirts with
layered ownership" that the 2026-07-24 ruling weighs against.

**B. Generator-argument interpolation (recommended).** A generator is
`(kind, args)`. A morph interpolates the **argument vector** over duration and
curve, then settles exactly on the destination spec. One slot, one owner. The
fade concept is reused recursively rather than a new mixing primitive being
invented. Non-interpolable arguments (LFO shape, the `f` free flag) are
discrete: they take the **destination** value at morph start, and the audible
morph is carried by the numeric args.

**C. Compile it dashboard-side into existing messages.** Attractive — zero
contract change — but it dies immediately: a dashboard-side argument ramp is a
stream of generator messages at control rate, which floods the LAN and breaks
the full-state/idempotent law that makes late joiners land in phase. §3.3 is
explicit that decomposition lives in `bopos.py`, never above it. Rejected.

### Recommended wire form

```
/<sel>/p/<identity> morph <dur> <destination-spec…> [c:<n>]
```

where `<destination-spec…>` is any existing full-state form — a constant, or
`lfo …`, or a segment list. Semantics:

- The node interpolates from its **current generator's argument vector** to
  the destination's over `<dur>`, applying `c:<n>` to the interpolation, then
  holds the destination spec exactly.
- **Kind coercion** makes cross-kind morphs continuous without a new
  primitive. A constant `v` is coerced into the destination kind's argument
  space as its degenerate member: against an LFO destination it becomes
  `lfo <destShape> v v <destPeriod>` (zero depth at the current value), so the
  morph opens the depth out from silence-of-modulation. The reverse collapses
  depth onto the destination value. This is Bob's "ramp depth to 0, swap,
  ramp up" — but derived from one rule instead of authored as a special case,
  and with no dip in the same-kind case.
- **Same-kind, different shape** (sine→saw): the shape switches at morph
  start while `min`/`max`/`period` interpolate. Both are clock-anchored, so
  there is no phase clash — the switch is a timbral change inside a stable
  range, not a level jump. If a true shape crossfade is ever wanted, it is
  authorable today as two steps (collapse depth, then expand into the new
  shape) without any of A's machinery.
- **Degenerate case**: `morph <dur> <value>` from a constant is exactly
  today's `x <dur>` fade. `morph` is a strict superset; static→static may
  keep emitting the legacy fade form.
- **Take-over**: any later message on the address replaces the morph, as it
  replaces any generator. No new rule.
- **Catch-up** (§3.3's full-state law): a morph in flight is not replay-safe,
  so — exactly as a fade catches up with its computed current value — a morph
  catches up with the **current interpolated generator spec**, sent as a plain
  full-state generator message. The argument vector is small, so this is
  strictly better behaved than the fade case: the late joiner lands on a real,
  idempotent generator rather than a frozen scalar.
- **Int/enum/toggle** params quantize through the existing §3.3 int path
  (truncate, emit once per crossing). `text` params cannot morph; a morph
  containing text entries sets them at *t=0*, and the UI says so.

### Cost

One argument-vector lerp per morphing param per control tick, in `bopos.py`,
beside the existing generator evaluation. Compared with A, no second
evaluation, no second slot, no new take-over state machine, and no §3.3 model
change.

### Preset-level morph

An apply with a duration compiles per captured param into one `morph` message.
Params whose captured entry equals the current state may be skipped. That is
the entire interpolation feature at the preset layer.

---

## 5. Collections (Q5) — ruled: show steps

No new store, no new wire form, no new disk artifact. A "meta preset" is a
show step whose messages apply different presets to different targets. Step
templates, if wanted later, are a Show-tab concern.

---

## 6. Show integration (Q6)

### The message

A new message family in the Show document model, by **reference**:

```
address: /preset/<patch>/<preset-name>
args:    [<dur>?] [c:<n>?]
target:  [selector…]           (existing target chips, groups by name per F1)
```

It never reaches the wire verbatim. At send time the dashboard expands it into
the per-param `/p/*` (or `morph`) messages, to the same targets. The Monitor's
Outgoing tab shows the expansion, which is the honest record of what was sent.

By-reference, not flattened, because it is the only variant that (a) keeps the
preset the single source of truth when it is re-saved, and (b) participates in
the ratified `{name, fingerprint}` drift mechanism. The message therefore also
carries the schema fingerprint it was authored against, and the Show tab warns
— non-blocking — when it no longer matches.

**Flatten-to-messages** is offered as an explicit editor action on the message
(one preset message → N literal `/p/*` messages) for when a step needs
hand-editing. That is the escape hatch, not the default.

### Pill encoding

One additive ninth category alongside the ratified flat eight: `preset`, code
**`PRE`**. A preset message with a duration reads as a morph and may take the
modulation ink, consistent with `04-event-fire-affordance` widening cyan to
"something is driving this, continuously or discretely".

### Capture-as-step

Control tab → one button → a new show step whose messages are the current
target→preset arrangement, by reference, one message per target that has a
preset applied (dirty or not — the asterisk is a UI truth, not a capture
rule).

**Targets with no preset applied are omitted**, and the button says so before
it commits ("3 of 5 targets have a preset applied; the other 2 will not be
captured"). Capturing them would mean silently minting anonymous
value-snapshot messages, which is the flattened form the design deliberately
makes an explicit choice. → **Fork F3 below.**

Placement: the capture button belongs on the Control tab's target-filter
chrome, not inside the per-card preset row — it is an operation over the whole
arrangement, not over one card's preset. The per-card row keeps
`new`/`save`/`del` from the shipped provisional slot.

---

## 7. Editor save flow and node sync (Q7)

- **Save destination**: `patches/<patch>/presets/<slug>.json`, written
  atomically by the dashboard through the same host-side path that writes
  `bopos.patch.json`. The patch being edited is the patch whose presets the
  panel lists; the Control tab lists the presets of the patch that owns the
  card's schema (fleet patch, or a pinned device's own patch —
  `live_scope_patch` already answers this).
- **From the editor**, save captures seat 0 (the audition engine the editor
  drives), which is the same selector `set_editor_param` writes to.
- **From the Control tab**, save captures the card's target under the mixed
  ⇒ omitted rule (§1).
- **Nodes never receive presets.** Apply is dashboard fan-out; a node has no
  preset concept, no preset state, and no preset verb. This is what makes the
  distribution exclusion safe and the contract delta small.

---

## 8. Migration (Q8) — ruled: retire

Venue presets retire with this thread (F2; the store is empty, no migration):
delete the `presets` key from installation state and its rename/renumber
handling in `state.py`, remove the `save_preset`/`load_preset` websocket
commands and `preset_scope_seats`, and remove the facilitator preset shelf.
The shipped provisional preset row (`7-preset-slot`) becomes live and is the
only preset UI in the system.

---

## 9. Contract amendment (proposed v1.17, additive)

1. **§3.3** — add the `morph <dur> <spec…> [c:<n>]` form: argument-vector
   interpolation, kind coercion, discrete args take the destination at start,
   catch-up sends the current interpolated spec.
2. **§8/§9** — name `presets/` a host-only patch subdirectory: authored
   content that travels with the patch in git, excluded from the distribution
   manifest, the fingerprint, and prune-to-manifest convergence.
3. **§8** — one sentence: a preset captures declared params only; events are
   never captured (already stated), and master/mute/positions/assignments are
   site-layer, not preset material.

Nothing else is wire-visible. Presets themselves are not in the contract.

**§14 compliance.** Two rejected designs are load-bearing here and the
proposal stays on the right side of both. *Runtime parameter dump/query is
rejected* — so a save captures from the dashboard's own durable state (seat
params plus the automation table), never by asking a node what it currently
holds. *Envelope-carrying events are rejected, "crossfades are dashboard param
automation"* — so morphing is a `/p/*` grammar form evaluated by `bopos.py`,
not anything the event plane learns to do.

---

## 10. Forks — all four RATIFIED by Bob, 2026-07-28

**F1 — `presets/` exclusion, or accept the restage? → RATIFIED: exclude.**
The alternative is that every preset save marks the fleet patch stale and
refetches it — which would break the very workflow the thread exists for.
Naming the exclusion in the contract is the cost.

**F2 — `morph` (argument-vector), or the mix function? → RATIFIED: `morph`.**
It preserves one-slot/one-owner, costs one lerp per param per tick, and
derives Bob's own "depth to zero, swap, depth up" from a single coercion rule.
The mix function stays authorable as two steps if a literal shape crossfade is
ever missed.

**F3 — does capture-as-step include targets with no preset applied? →
RATIFIED: no.** The count is stated before committing. Including them means
minting flattened value-snapshot messages, which the design makes an explicit,
separate action. A checkbox ("also snapshot un-preset targets") is a small
later addition if the omission proves annoying in practice.

**F4 — how does a target say which preset it is on? → RATIFIED: position 3,
stored provenance with derived dirtiness.**

The marker exists for two consumers: the panel's preset dropdown needs a
selected value, and capture-as-step needs the target→preset arrangement.
Hard takeover guarantees the marker can go stale the instant anyone nudges a
fader, so the question is what it *means* when it does.

Three positions:

1. **Marker means equality; any write clears it.** Honest but useless in
   practice: the first fader nudge blanks the dropdown, and capture-as-step
   loses the arrangement exactly when you have finished tuning it — which is
   when you want to capture. It also throws away true information ("this came
   from Dawn") to avoid stating a false one.
2. **Marker means provenance; a stored dirty bit tracks divergence.** The
   hardware-synth and plugin idiom (`Dawn *`). But a sticky bit lies in the
   other direction: nudge a fader and put it back, and the target is equal to
   the preset while still flagged modified. It is also a second copy of a
   truth the dashboard can already compute.
3. **Marker means provenance; dirtiness is derived (recommended).** Store
   `{patch, name}` only. Compute `dirty` at render by comparing the preset's
   captured entries against the target's current durable values and automation
   entries. Cleared only by recalling another preset or choosing none.

Position 3 is the ruling. It is the same rule the entity review already ratified as R5
(**verdicts derived, never stored**) and the same shape as patch drift and the
device badges — one fewer piece of state to keep honest, and it self-corrects
when a value returns to its preset position. The dashboard holds everything
the comparison needs, so it costs one pass over a card's params per render.

Details it implies: compare at the precision the UI sends (the existing
6-significant-figure / integer rounding), not raw float equality; a generator
entry compares by argument list, which is already how the drawer signatures
work; a morph in flight reads dirty until it settles, then clean, which is
informative rather than a bug; params the preset does not capture never
contribute. Provenance is runtime state, forgotten on dashboard restart like
automation state — the dashboard cannot know what happened while it was down,
and the derived check would only re-confirm it anyway.

---

## 11. Implementation stitches (sketch — laid out after the review)

`2-proposal-review` runs first (Bob, 2026-07-28): another agent reviews this
proposal in detail before anything is built. The stitches below are therefore
a **sketch, not created yet** — the review may reshape their boundaries, and
laying them out now would freeze a decomposition the review exists to test.

1. `3-contract-amendment` — §3.3 `morph`, `presets/` exclusion, §8 sentence;
   contract revision history (v1.17).
2. `4-preset-store` — the patch-folder store: read/write/list/delete, slug
   rules, schema fingerprint, drift resolution, `presets/` exclusion in
   `python/identity.py` (with the node-side prune check).
3. `5-panel-preset-row` — the shipped provisional row becomes live: list,
   `new`/`save`/`del`, per-row include/exclude on save, applied provenance and
   derived dirty asterisk, drift warning inline.
4. `6-morph-engine` — `morph` in `bopos.py` and `tools/simfleet.py`, argument
   coercion, catch-up, int quantization, take-over. Browser-free guards.
5. `7-show-preset-message` — the `/preset/*` message family, expansion at
   send, `PRE` pill, drift warning, flatten-to-messages, capture-as-step.
6. `8-venue-preset-retirement` — remove the old store, commands, and shelf.

The contract amendment gates everything; the store and the morph engine are
parallel after it; the panel row needs the store; the show message needs both
the store and the morph engine; the retirement is last so nothing references a
retired path mid-flight.
