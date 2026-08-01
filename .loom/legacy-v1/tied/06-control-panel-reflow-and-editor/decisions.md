# Decisions — 06-control-panel-reflow-and-editor

Date: 2026-07-30.

## Reflow is bounded by the instrument face

The numeric row remains one three-column grid:
`58px value | flexible slider | 18px modulation`. The slider is the only
column that contracts. The generator drawer remains a fixed 320px face and its
argument row no longer permits wrapping. That face plus shared card padding
sets a 340px panel minimum.

Measured in Chromium at a 360px phone viewport, the three row controls share
one vertical centre, the drawer is exactly 320px, its args use `nowrap`, and
the panel minimum is 340px. This is reasonable on a phone. Narrower containing
blocks scroll the intact panel.

This supersedes design-language §7's old “row may wrap before boxes shrink”
sentence. The ratified design-language record now names the supersession.

## The editor is one ControlSurface member

The audition engine is represented as one seat-shaped member with:

- `id: 0`, because that is its private OSC selector;
- `automation_key: "editor"`, preserving the existing isolation from real
  Seat 0;
- the editor's own `params`, preset provenance, and dirtiness.

One member is always solid, so mixed-state presentation appears only when a
real aggregate disagrees. No editor-only aggregate semantics were invented.

The editor's hand-built `editorControl` / `editorParamTree` renderer and its
duplicate declared-event rows are deleted. Parameters, hierarchy, precision
entry, generators, and declared events now come from `ControlSurface`.
The scratch preview retains only the deliberately different “try undeclared
event” affordance.

## Remote metadata stays in authoring

The `dashboard` compatibility field still appears as the `Remote` checkbox in
the manifest editor, where it is authored. Its badge is removed from runtime
parameter rows: the field gates Remote visibility and is not runtime state or
part of the shared panel grammar.

## Editor automation uses resolved targets

Adopting the drawer exposed two pre-existing boundary assumptions:

1. `set_live_automation` was globally blocked during Patch Edit. An
   editor-scoped generator is an audition-engine control, like editor-scoped
   preset recall, so it is now allowed while other scopes remain blocked.
2. `OSCBridge.set_param(0, ...)` re-derived real Seat 0 from the selector.
   The editor is not that Seat. `set_param_for()` records an already-resolved
   target list before sending, and ordinary selector-based calls delegate to
   it unchanged. Editor generator and manual-takeover writes use the editor
   pseudo-target, preserving the `editor` automation key.

## Ground and card

`#editor-params` is an explicit `--panel` card with border, radius, padding,
and horizontal overflow. It is neither transparent nor painted with `--bg`.
The same component-root minimum is ready for the parent-document Control host
that stitch `08-control-tab-columns` will add; this stitch does not retire the
existing iframe.
