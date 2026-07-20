# Ratified layout decisions — 2026-07-20

Design session run with Bob (dashboard autopilot session). Starting point was
`ui-review.md`; the recommended shape there is adopted except where noted.

## Edit bar (feeds `02-edit-bar-and-inline-step-name`)

- **Placement/grouping** (per ui-review): one persistent toolbar immediately
  above `.show-rows-box`, inside `.show-list-shell`. `+ Step` and `+ Divider`
  grouped left, flexible centre reserved for future lane controls,
  Duplicate/Delete right. Positions stable; unavailable actions disable, never
  hide. Icon + short text at wide widths, icon-only below the narrow
  breakpoint, always with `aria-label`, tooltip, visible focus, touch-sized hit
  target.
- **Insertion point** (per ui-review): additions insert relative to the
  selected structural row; append to the end when nothing is selected.
- **Message-focus targeting** — **RATIFIED: Disabled.** When a message row is
  focused, Duplicate and Delete grey out. The bar acts only on structural rows
  (steps/dividers); message-level operations stay in the inspector. Zero
  ambiguity is worth the extra click.
- **Divider duplicate** — **RATIFIED: allowed.** Duplicating a divider clones
  it in place (fresh UID).
- **Delete confirmation** — **RATIFIED: none.** Deleting a non-empty step does
  not confirm; undo covers mistakes (QLab-style terse operation).
- Duplicating a step mints fresh UIDs for the step and every nested message
  (per ui-review, unchanged).
- Bottom add bar and inspector Arrange section are removed only after the new
  bar has full parity (per ui-review, unchanged).

## Inline step name (feeds `02-edit-bar-and-inline-step-name`)

- **RATIFIED: single click/tap** on the bold inspector title swaps in a
  selected single-line input. Enter or blur commits, Escape restores the prior
  value, blank commits to the untitled/null state (renders `Untitled step`).
  The title is keyboard-focusable; Enter or F2 while focused also opens edit.
  No per-keystroke saves. Persisted field remains `alias`; UI label is
  **name**. Message aliases untouched.

## OSC terminals (feeds `03-responsive-osc-terminals`)

- **RATIFIED: breakpoint 900px, fixed expanded height ~320px.** Two
  equal-width columns at viewport widths ≥ 900px; below that, stack outgoing
  then incoming, each full width. Expanded terminals share the same fixed
  ~320px overall height (~12 monospace log lines); summary and filter/action
  rows stay fixed while the log fills the remainder and scrolls internally.
  Collapsed terminals stay summary-height and expand independently. Live
  traffic never changes panel or page geometry; long frames scroll/wrap inside
  their own log.

## Message infrastructure — explicitly retained (Bob review point)

Bob flagged the coloured message pills and their attached infrastructure
during wireframe review. Confirmed against `dashboard/static/js/show.js` and
recorded as a hard constraint on `02`:

- Coloured message pills in step rows stay exactly as they are (colour hashed
  from message alias; `show-message-pills` / `pillColourClass`).
- Message keyboard copy/cut/paste/delete on a focused pill (⌘C/⌘X/⌘V/Delete,
  clipboard carries alias+address+args+target) stays untouched. No collision
  with the edit bar: bar Duplicate/Delete are disabled on message focus, so
  the pill Delete-key path remains the only message-delete affordance there.
- The message inspector (alias input, target picker, payload builder, wire
  preview) is untouched; it has no Arrange section. Message aliases are not
  renamed or restyled — only the *step* alias presentation changes.
- The step inspector's "Add message" button stays.

`02`'s removals are exactly: the bottom `.show-add-bar` and the Arrange grid
in step/divider inspectors — nothing message-related.

## Out of scope (reaffirmed)

No show-schema changes; no lanes/scenes work — that stays with
`scene-sequencing/show-lanes-and-scenes-design.waiting`.

## Wireframes

`wireframes.html` in this stitch renders the compact desktop (≥900px) and
narrow (768px) layouts reflecting these decisions. Reviewed by Bob before tie.
