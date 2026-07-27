# Progress

2026-07-27 — Complete. The fourth slice of the ratified control-panel design:
every non-float manifest kind now renders in the shared `ControlSurface`, so
the Control tab, the Device-tab panel and the standalone facilitator get them
at once.

## What shipped

**One kind dispatch.** `paramKind(declaration)` in `control-surface.js` is now
the single decision — event / string / enum / toggle / numeric — and the row
wrapper carries a `live-param-<kind>` class. Enum is tested *before* toggle,
because a two-option enum also spans 0..1 and it is the `options` list, not
the range, that says "this integer names its values".

**Toggle** (int, min 0, max 1). The checkbox is gone; a 0/1 param is a
latching `<button aria-pressed>` with the name inside it, sharp-radiused off
the existing `button[aria-pressed]` rule (PD: a toggle is a square box). It
spans the value + slider columns so the ∿ icon stays in the same 18px column
down the whole panel. Under a generator it wears the doubled `--mod` outline
and, for an LFO, flashes at the generator's own period, phase-anchored by
`--auto-elapsed` exactly like the slider marker — see the open question
below. Mixed hatches in the ratified two inks.

**Integer.** Already correct from `4-row-regrind` (step-1 slider,
right-aligned value box); this stitch only added the living wire assertion
that an integer row steps by one to the node.

**Enum.** A `<select>` over the option index, plus the parameter name beside
it. `options` is a new additive manifest field on a `type: "i"` param;
`min`/`max` are **derived** from the option count, which is what makes
generators work with no new machinery — Q2's "enums automate like ints" fell
out rather than being implemented. Verified end to end: an LFO applied to an
enum arrives at simfleet as whole indices inside the declared range.

**Event.** A top-level `events` list in the manifest, validated (name/path,
arity 1–3, optional labels/defaults, no collision with a param identity) and
rendered as the ratified row — 1–3 58px boxes, `sync`, `send` — with every
control **disabled** and no `data-live-param` anywhere on it, so the row
cannot send. Events travel beside `declarations` in `live_controls.events`
rather than inside it, so nothing else that consumes declarations (replay,
presets, the Show message builder) ever sees them; the two hosts fold them
back in at the point of render.

## Verification

- `tools/run-tests.sh fast` — green apart from the standing red
  `45-device-enabled-replay-red` (pre-existing, its own stitch).
- `tests/test_manifest.py` — new cases for the derived enum range and the
  event declaration, including the invalid shapes.
- `tests/verify_control_surface_component.py` — the kinds render (button not
  checkbox, sharp radius, option labels, event arity/inert buttons) and an
  enum sends its integer index.
- `tests/verify_generator_drawer.py` — a generator on an enum runs on the
  node and its ticks are whole indices in range.
- `tests/verify_live_param_checkbox.py` → renamed
  `tests/verify_live_param_kinds.py`: the thread-43 "Event object reached the
  wire" regression is a property of the *binding*, so it is now re-pinned for
  every kind that binds — toggle, slider, integer, enum — each with its wire
  value, disk persistence and heartbeat survival.
- Whole browser tier run twice. Note: `verify_control_surface_component.py`'s
  three accordion **reload**-persistence checks are flaky on clean `main`
  (reproduced by stashing this work: 1 pass / 2 fail in three runs). Not
  caused by this stitch; flagged separately.

Screenshots of the panel with all kinds, unified and mixed, dark and light,
were taken against a real dashboard + simfleet and reviewed. Two defects
found that way and fixed before tie: the event row's `empty` box class
collided with the facilitator's global `.empty` message utility (8vh margin,
96px-tall rows) — renamed `blank`; and the `auto·mixed` legend had no cell in
the new grids, wrapping the ∿ icon onto a second line — retired, since the
hatch plus the accessible name already carry the state, which is what the
numeric row already decided.
