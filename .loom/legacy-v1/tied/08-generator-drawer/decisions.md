# Decisions — 08-generator-drawer

## The open question the instructions named: how a live generator reaches the wire

**Decided: a new ws verb, `set_live_automation`.**

`set_live_param` cleans its value through `clean_editor_value`, which is
scalar-only by construction (it clamps to min/max and rounds ints). A §3.2
generator is an *argument list*, so it could not travel that path without
loosening the scalar guarantee for every ordinary write.

But nothing below that needed inventing. `osc.set_param(selector, name, value)`
(`dashboard/osc_bridge.py:282`) already accepts a list, parses it with the
shared grammar, records the automation entry per seat with the phase anchor,
handles the fade-destination case, and **clears** the entry when the message is
`stop`. And `live_param_target(scope, id)` already resolves the same scopes.

So the new verb is a **validation boundary, not a mechanism**:

1. resolve the declaration and target exactly as `set_live_param` does;
2. validate every argument with `show_model.clean_arg` — the same cleaner the
   Show model uses, so the two authoring paths cannot drift;
3. validate the whole message with `paramgen.parse_message` against the
   declared type, rejecting with a clear ws error rather than emitting;
4. hand the list to `osc.set_param`.

**Deliberately no `seat["params"]` write.** A running generator's durable value
is whatever the node last emitted; `osc.set_param` already owns the one case
where a durable value *is* implied (a fade's destination). Writing the seat
params here would have fought it.

The verb joins both `serialized_mutations` and `edit_blocked_mutations`,
matching `set_live_param` — a generator is an execution control and has no
business running during Patch Edit.

## Two-state switch, drawer as a sibling

The switch is `value ▸ gen`, strictly two states, per the ratification. The
drawer is rendered as the **grid sibling** of the row's `<label>`, not a child:
a `<label>` must not wrap a form region of its own, and `.promoted-controls` is
already a grid, so a sibling lands directly beneath its row with no layout work.

**Trap found and guarded:** the switch buttons sit *inside* the row's
`<label>`, so a plain click also activates the labelled control — clicking
"gen" on a boolean row would have toggled the very checkbox the operator was
opening a drawer for. The handler calls `preventDefault()`. Pinned by the
"underlying control is still usable" check.

## Drawer state lives in the component, not the DOM

Heartbeats re-render the cards, so open-drawer state and the in-progress
argument list are held in the component (`openDrawers`, `drafts`) and
re-rendered from there. Field edits compile to args and store the last **valid**
list, so a half-typed period cannot clobber a good draft. The drawer also sets
the host's `interacting` guard on `focusin` — the same guard the precision
field uses — so typing survives a heartbeat.

Switching generator kind **resets to that kind's defaults** rather than trying
to reinterpret the previous kind's fields. Reinterpretation was the source of
the Show-inspector write-through trap recorded as CLAUDE.md gotcha 10.

## Mixed aggregates: nothing special

Per the ratification, there is **no `mode === 'gen'` branch**. The aggregate is
never disabled by disagreement; it renders its existing mixed indication, and
committing a generator sets every member. The verifier runs its whole scenario
twice — once with agreeing seats, once with disagreeing ones — and asserts the
gen switch is *not* disabled in the mixed case.
