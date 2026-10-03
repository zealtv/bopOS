# 1-preset-inventory

**Status:** ready
**Goal:** a complete removal plan, so `2` is mechanical.

## Do

- List every preset surface (parent has a starting map; grep is not enough —
  check CSS, ws message types, show schema, saved JSON in `dashboard/shows/`
  and `dashboard/installations/`).
- Separate what goes from what stays because something else uses it. Likely
  shared: the parameter-schema fingerprint, `/p/*` fan-out helpers, Show step
  machinery.
- Decide what happens to existing data: preset files in patch dirs, `PRE`
  steps in saved shows, the `presets` key in installation files. Prefer a
  clean break over a shim; say what a stale file does on load.
- Draft the §8.1 retirement text and §15 entry (proposed, not written).
- Split `2` into child stitches if the plan is more than one clean change.

## Ask Bob only if

A removal changes something he'd notice beyond "presets are gone" — for
example, a Show step kind disappearing from existing shows.

## Deliver

`plan.md` in this stitch: surfaces, keep/remove, data handling, test changes,
order.
