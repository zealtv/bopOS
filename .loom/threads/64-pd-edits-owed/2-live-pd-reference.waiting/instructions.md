# 2-live-pd-reference

**Status:** Bob's (glean `never-edit-pd`) · approach OK'd 2026-11-05 · needs `1`
**Goal:** one live, current Pd reference for every bopOS feature, edited in
one place, so new and old patches never depend on a stale copied example.

Bob, 2026-11-05: *"ideally the template is some sort of subpatch so I can
edit it in one place and it updates in other patches … at the moment I'm
finding that as I create a patch, I'm using the stuff that comes in with the
template as a reference and it's going stale."*

Build from `1-pd-feature-inventory`'s `inventory.md`. Its staleness test
keeps this current afterwards.

## Approach (proposed 2026-11-05; Bob OK'd the same day)

**A help patch, `pd/bopos~-help.pd`, plus a thin template.**

- Pd's own mechanism: right-click `[bopos~]` → Help opens `bopos~-help.pd`
  from the same directory. It lives in `pd/`, so it updates with the
  framework (git), not with each patch, and every patch that declares
  `../../pd` reaches it.
- It only runs when opened, but it's live when it does run: opened beside a
  running patch, its `[r bopos-*]` sections show real values. Demo sound off
  by default; admin messages (reboot, shutdown) shown but not connected, or
  behind a deliberate gate.
- The template shrinks to the skeleton a patch needs (`declare`s,
  `[bopos~]`, the `catch~`/outs, one `throw~` example) and a comment
  pointing at `bopos~`: right-click → Help for how to work with bopOS in Pd
  (Bob, 2026-11-05).

**Why not a shared abstraction instanced in every patch** (the literal
"subpatch" reading):

- It *runs* inside every patch, on every Pi: its receivers, `loadbang`s,
  `metro`s, `throw~`s and admin messages would be live in every
  installation.
- Editing it changes the behaviour of every patch on the fleet at the next
  framework update. A reference that patches depend on stops being a
  reference and becomes framework code.
- Help patches give "edit in one place" without either problem.

Existing patches keep their stale copied sections; deleting those is Bob's
choice, patch by patch.

## Folded in (2026-11-05)

- **Keys and mouse examples**: from `84-key-input/4-pd-reference-patches`
  (dropped, folded in) and the matching `64` checklist item. Bob's
  requirement still holds: *"i want to make sure io keys is referenced in the
  pd template that feeds a new patch"*. With the help-patch approach, the
  template's pointer to Help satisfies it; if Bob prefers, the template also
  keeps a small keys section. Exact spellings and the simulator checks:
  `keys-and-mouse.md`.
- **Template retired `update-patch` message**: from the `64` checklist. It
  goes with the template rewrite.
- Do `64`'s event-bus `[list]` edit first, so the reference can show the
  plain `[r bopos-event] → [route <name>]` idiom.

## Verify

- Right-click `[bopos~]` in a new patch from the template (Patches tab
  **New patch**) → Help opens the reference.
- With the patch running in Patch Edit (input *simulated*), each section of
  the reference shows live values: params, events, points, context, keys
  and mouse (Modules tab key · mouse panel), I2C io.
- `1`'s staleness test is unskipped and passes.
- A new patch from the template still makes sound and has no `update-patch`.
