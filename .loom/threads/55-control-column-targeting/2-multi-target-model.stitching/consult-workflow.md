# Consult — workflow altitude

*Q1–Q4, weighted to the operator's arc: set up columns → target groups → apply
presets → tweak → capture → repeat. Grounded in `control-column.js`,
`control-host.js`, `control-surface.js`, `target-picker.js`, `show-capture.js`,
`server.py:2043/1830/1758`, `preset_application.py`, `show_model.py`, and the
two screenshots already in this thread.*

---

## 1. Recommendation

### Q1 — A column targets exactly one thing. `multiple: false`.

**Yes/no: restrict the Control target picker to a single entry — `all`, one
group, or one seat — and delete the card-per-entry path.** This is shape (d).

Three workflow arguments, in order of force.

**(i) Multi-select is a worse duplicate of "+ column".** `A-multi-target.png` is
the proof: a three-target column is three 40-row panels stacked inside 342px,
with the rest of a 1440px screen empty. `B-two-columns.png` is the same
information, legible, side by side. Stacked cards cannot be reordered, removed
individually, labelled individually, or given their own sticky header —
columns can do all four. Two affordances for one job, one strictly worse.

**(ii) It costs traffic, which is the point of the system.** `apply_preset`
coalesces to a single datagram only when the selector is `all` or `gN`
(`server.py:2130-2138`); every other resolved set fans out per seat. A column
holding seats 1, 3, 5 sends three messages per fader move and three per preset
entry, where a group sends one. **Targeting shape, not preset sparsity, is the
dominant traffic term** — the brief files this under Q2, but it is a Q1 fact.

**(iii) It produces steps that cannot travel.** `capture_target` degrades an
ad-hoc union to literal seat ids — `show-capture.js` already labels those rows
*"site-bound — Seat ids, not a group name"*. Hemming the picker in pushes the
operator toward making a group on the Seats tab, which is the durable,
portable, coalescing object. The interface should make the cheap thing the
easy thing.

Two riders:

* **A hand-added column starts with NO target.** `addColumn()`'s `["all"]`
  default (`control-host.js:210`) is the cause of the report Bob closed in
  `3-cross-column-preset-report`, and it contradicts D5's own rule that empty
  is safe and All is not. The unresolved state and its *"choose a target"*
  button already exist (`control-column.js:345`). The bootstrapped first column
  keeps `all` — a fresh operator needs a working surface.
* **The card head collapses into the column head.** With one target, `Control
  target  Front` and `Front  g0 · 2 Seats` are the same sentence twice. One
  title bar: target, member count, preset state (see Q3).

`mixed` machinery stays — a group card is still N seats that may disagree. It
goes only where it was *elective*.

### Q2 — A step is a preset reference plus the deviations from it.

**Yes/no: capture emits, per cluster, one `reference` message followed by the
`/p/<identity>` messages that differ from that preset — deviation sparsity, not
mixed sparsity.** Clusters key on (patch, preset) as today, then sub-cluster by
distinct deviation vector so each sub-cluster gets its own `capture_target`.
This matches Bob's stated intuition exactly and is sparse by construction.

**The load-bearing consequence the brief misses: playback must not dirty the
venue.** A show reference plays through `apply_preset`
(`server.py:1743`), which writes `applied_preset` and clears `preset_dirty`;
`refresh_preset_dirtiness` then re-derives dirtiness on *every* `public_state`.
So a step of preset + deviations marks every seat it touches dirty the instant
it plays, and Q3's marker becomes noise precisely during a show. The fix is
small and mandatory: **the provenance marker carries the deviations** —
`applied_preset: {patch, name, overrides: {identity: args}}`, and
`preset_dirty` compares against preset ∪ overrides. Then capture → play →
capture is a fixed point, which is the property that makes the whole model
trustworthy.

**Seats with no preset applied capture literally, not as nothing.** The current
`continue` (`server.py:1846`) turning a dialled-in room into an empty step is
the worst outcome in the arc and must go. They capture as plain `/p/*`
messages against `capture_target`. The cost is made loud, not hidden: the
ambient count becomes `9 preset · 3 literal`, and the armed preview gains a row
per literal cluster with its message count. The preview is the hemming-in
device — you see 120 messages before you commit, and can go apply a preset
instead.

**No, capture must not let you pick which values are sent.** *Correcting the
brief:* preset **save** already offers exactly that — per-identity checkboxes
in the save drawer (`control-surface.js:336`), honoured by `include`
(`server.py:2009`). So the two would not diverge; they should still differ.
Save authors a reusable object, where omission is meaningful. Capture records a
room you can hear, where the value is that it is one click. Editing belongs
after the fact, in the step inspector — which already offers *Flatten to
parameter messages* (`show.js:740`), so literal values are an existing,
first-class post-capture act rather than something capture must invent.

Auto-generated presets at capture: **no**, for the brief's own two reasons
(dropdown pollution, `presets/` travels with the patch), both of which the
deviation shape avoids.

Retire the phrasing *"edited since applied — captures the preset, not the
edits"* (`show-capture.js:214`). Under this model it becomes false.

### Q3 — Three states at a glance, the rest on inspection.

The full space at card level: (1) no provenance; (2) clean preset; (3) preset +
deviations; (4) targets disagree on preset; (5) agree on preset, some dirty;
(6) preset deleted from the store; (7) schema drift; (8) automation on top;
(9) seat runs another patch. Nine is not a glance vocabulary.

The operator asks one question at a glance: **will capture record what I
hear, and cheaply?** That is three states — clean preset (yes, one message),
preset + deviations (yes, few messages), no provenance (yes, expensively).
Mixed is a fourth only because it is genuinely ambiguous. States 5–9 are
inspection: they already have homes (the `⚠`/`schema changed` mark, the apply
report, the cyan ∿).

**Treatment: words in the column header, plus one non-colour edge.** With one
target the column *is* the card, so a column-level treatment is finally
truthful — today, with N stacked cards, a column border would be lying, which
is a further Q1 argument. The header currently spends two words on *"Control
target"*; spend them instead:

```
Front  g0 · 2 Seats  ·  dusk              clean
Front  g0 · 2 Seats  ·  dusk +3 edits     deviations
Front  g0 · 2 Seats  ·  dusk +2 others    mixed
Front  g0 · 2 Seats  ·  no preset         free
```

Redundantly encoded as a 2px left edge on the header in the existing ink scale
— solid / dashed / hatched (the app's established mixed idiom) / none — so it
reads peripherally across a row of columns. **Add no colour.** Cyan is
modulation by ratified decision and a second semantic hue would break a
grayscale language that has held for four threads. This also answers the
legibility item `3-cross-column-preset-report` left unruled: an All column
reading `dusk` now says *why* in the same line.

### Q4 — What patch switching does to this model

A step is already patch-scoped: the reference carries `content.name`, and
deviation `/p/<identity>` messages are meaningless without a manifest. So the
model does not foreclose a patch-switching step. It needs two things from
whatever `34` decides: **a per-step declaration of the patch in force**, so
deviations and drift warnings resolve against the right manifest; and a rule
that **capture never crosses a patch boundary within one step** — which holds
free, since clusters key on (patch, name). Note that a patch switch is not
instantaneous (restaging, fingerprint convergence), so the show engine will
need a readiness gate before the following step's messages fire; that is `34`'s
problem, but it is the model's dependency.

---

## 2. What this forbids

* **Ad-hoc unions as a live target.** Want Front + Back? Make a group. The
  answer is a durable, portable, single-datagram object.
* **A new column silently owning the whole venue.** It owns nothing until aimed.
* **Capture producing an empty step.** Structurally impossible once
  un-provenanced seats capture literally.
* **Choosing values at capture time.** One click, then edit the step.
* **A second semantic colour.** State is words plus one non-colour edge.
* **Two titles per column.** The card head merges into the column head.

## 3. The weak point

**Single-target loses cheap "set these three seats to the same thing".** Today
one column, three chips, one drag of a fader writes all three; tomorrow it is
three columns and three drags, or a trip to the Seats tab to author a group for
something momentary. That is a real regression for exploratory work, and the
honest answer is that it is being traded for portability and traffic the
operator cannot see. Mitigations exist — "Open in Control" already appends a
column, and group authoring could be reachable from the picker — but if Bob
finds himself repeatedly making throwaway groups, the ruling was wrong and
shape (a), aggregate-over-union with per-seat fan-out accepted, is the fallback.

*Second-order:* aggregate-over-union (a) is **not** subsumed by (d) as the brief
states. (a) changes wire behaviour and capture portability; it is a capability
choice with costs, not only a hemming-in choice.

## 4. What it needs from `34-fleet-patch-global-state`

One authoritative answer to *"what patch is this venue running"*. Capture today
re-derives it per seat via `effective_patch_for_seat`, and a venue can be
heterogeneous (pinned devices), so a captured step records a patch name it
inferred rather than one the system asserted. This model wants to **record the
answer beside the step** at capture time and resolve later steps against it —
which needs the fleet patch to be a fact something owns, whichever way `34`
rules on first-class versus projection.
