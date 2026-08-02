# decisions — 2-multi-target-model

**Bob ruled, 2026-08-02, after a three-lens UX consult.** The question this
stitch asked ("should a multi-target column be one aggregate panel?") is
answered by a larger simplification that supersedes the framing: there are no
multi-target columns, because there are no columns.

## The rulings

**R1 — A column becomes a CARD, and a card targets exactly one thing.** All,
a group, or a seat. The multi-select target picker is retired on this surface.

**R2 — Cards sit in a grid that overflows DOWNWARD.** Not a horizontal track.
You scroll down to reach further cards.

**R3 — No drag-to-reorder.** Cards are ordered `all`, then groups, then seats —
the target picker's own ordering. This was Bob's amendment to his own first
sketch (which had drag): a derived order needs no persistence, no reorder
affordance, and no touch story, and it retires the concern that drag is
hostile on the iPad.

**R4 — Control and Remote become the same surface**, deliberately. Bob,
asked directly whether this was intended rather than an accident: *"yes,
intended."* Remote's cards come out naturally shorter because the manifest's
`dashboard:` flag gates Remote only, while Control shows every declared param
(`1-full-manifest-visibility`). Same component, no divergent code.

This supersedes Bob's earlier same-session ruling — *"remote works and i like
that it separates each target - i don't want that behaviour to change whilst we
work on the control tab"* — in the gentlest possible way: **one target per card
IS "it separates each target."** What he asked to protect is what R1 makes
universal. The constraint recorded in `1-column-scroll/decisions.md` (that a
shared `ControlSurface` would propagate Control's model onto Remote) is
therefore **dissolved rather than worked around**, and is no longer a hazard.

**R5 — `Capture as step` is REMOVED.** Bob: *"capture to step … isn't the
usability boon that I had initially planned, since adding preset messages to
show steps isn't particularly arduous. And when varying parameters start to
become involved, I think we're getting into quite messy territory."* Steps are
hand-authored from the Show inspector.

## What R5 settles, and what it does not

**Settled by deletion.** The whole of this consult's Q2 — preset reference
versus flattened values versus reference-plus-deviations, `omit` lists,
auto-generated presets, deviation sub-clustering, capture-time value picking —
is moot. None of it needs designing. The "a hand-dialled state captures as
nothing" defect goes with the feature that had it.

**NOT settled — two live defects survive R5**, both verified in code this
session, both independent of capture:

1. **Reference/param ordering in playback.** `_emit_messages`
   (`show_engine.py:146`) iterates synchronously; a `reference` message calls
   `queue_show_preset`, which **spawns a task and returns immediately**
   (`server.py:1694`), while a `/p/*` message sends synchronously in the same
   loop turn. So in a hand-authored step holding a preset reference AND a param
   message, the param lands first and the preset overwrites it. With a fade
   duration the §3.3 fade keeps writing for the whole duration, so no authored
   ordering fixes it. This breaks "a preset with modifications" — the exact
   workflow Bob called natural and kept — for hand-authored steps.
2. **`preset_dirty` conflates three unrelated causes into one appended `*`**:
   a value moved, the preset file could not be read
   (`server.py:1980` catches the store error and sets `True`), or the seat is
   running a foreign patch (`preset_application.py:269-271`). Different causes,
   different operator actions, one mark. It is computed for the display on
   every `public_state`, so removing capture does not touch it.

Both are carried into `56-simplify-cards-and-steps`.

## Consult disposition

Three consultants (interaction, workflow, systems) at
`consult-interaction.md`, `consult-workflow.md`, `consult-systems.md`, briefed
by `consult-brief.md`. Their Q1 answers were 2-to-1 for one-target-per-column,
reached independently and for a reason that survives into R1: `apply_preset`
coalesces a fan-out to one datagram per param only for a single `all`/`gN`
selector (`server.py:2126-2137`), so one target per card is the traffic-minimal
shape as well as the clearer one. Their Q2 answers are superseded by R5. Their
Q3 findings feed `56/3` and `53-ui-niggles/3`.

**One correction the consult produced, recorded because it was stated wrongly
to Bob mid-session:** the brief claimed there is no way to choose which params
a preset stores. There is — the save drawer renders a checkbox per identity
(`control-surface.js:336`) and the server honours an `include` allowlist
(`server.py:2008`). Two consultants caught it independently.
