# 1-columns-design

> **STATUS 2026-07-31 — work complete, `.waiting` on Bob's ratification.**
> Read `proposal.md`; it is the ruling document and lists the nine decisions.
> The UX consult ran with three lenses (`expert-live-operator.md`,
> `expert-show-authoring.md`, `expert-calm-ops.md`) over the code-grounded
> `ground-truth.md`, and `judgment.md` adjudicates them.
>
> **The consult question had a wrong premise.** All three lenses independently
> answered *neither* per-column nor whole-tab: capture is **venue-wide** and
> should take no scope argument. Per-column capture is not "easiest" — it is
> wrong today, because `presetScope()` sends `groups` for a group column and the
> server then captures every grouped seat in the venue. And §5's warning below
> about a "widened server vocabulary" is backwards: widening is the cost of the
> *per-column* answer; venue-wide capture is a removal.
>
> Mockups are in the `mockup-*.png` files here at 1280/1680/2560/760 plus the armed capture state,
> dark and light. `mockup.py` generates them by booting the real dashboard and
> composing the real rendered surface — only the column shell is drawn.
>
> Two findings were handed to siblings rather than settled here: the fade
> animator's document-wide queries (`2-control-column-component`) and the card
> chrome that lives in `facilitator.css`, which `index.html` does not load
> (`3-iframe-retirement`). Both are written up at the end of `proposal.md`.
>
> One decision is a live safety defect that exists **today at N=1**: `prune()`
> silently widens a column that lost its target to All (D5).
>
> On ratification: record Bob's calls as `decisions.md`, then un-`.waiting`
> `4-n-columns` and carry the ratified calls into its instructions.

Design the N-column Control tab. **Bob decision gate**: produce a written
proposal plus mockups, mark this stitch `.waiting`, surface it to Bob, then tie
it with the ratified design as `decisions.md`. Same pattern as
`01-dock-design` and `automation-4-waveform-ux-gate`.

Do not implement past ratification. `2` and `3` are structural and need no
design — they can proceed in parallel with this stitch. Only `4` is gated on it.

## Already ruled by Bob (2026-07-30) — design *within* these, don't reopen

- The control panel *"works really well when it's a relatively narrow column"*,
  so the tab hosts **N columns**, each a control panel with its own pop-out
  target picker, each targeting all / a selection of groups / a selection of
  seats / a mixture.
- **Simple add and remove, minimum one** — the tab is never empty.
- The All/Groups/Seat radio row at the top is gone (already true: `07` replaced
  `SeatFilter` with `TargetPicker`).
- **Column layout persists in `localStorage`**, consistent with
  `bopos.control.collapsed-branches` and `bopos.device-control-open`. Bob:
  *"with a chip picker it should be easy to spin up whatever control panel
  targets one needs"* — cheap re-creation is the argument against durable
  server-side layout.
- **Design-language §12 — ground and card.** Columns are cards on the ground;
  `--bg` shows only as the gutter *between* them, never inside a column's
  footprint. See the parent for the violation this retires.

## To settle

1. **Column widths** — fixed at the panel's minimum, or resizable? `06`
   measured the panel's floor: a 320px generator face that never reflows inside
   a 340px card minimum. Rows are atomic (`06`, `06b`); a column narrower than
   the floor is not a design option.
2. **A column whose target resolves to no seats** — an empty group, or a seat
   that was deleted. Today `renderCards()` falls back to
   `<p class="empty">No Seats</p>` and `liveCard` has an `empty-group` state.
3. **The applied-preset marker and its derived dirtiness** (`41-preset-primitive`
   R5) when two columns' targets overlap — the same seat visible in an All
   column and a Seat column, one of them applied against.
4. **`followFocusSeat` with N columns.** `07` ruled the target selection is
   per host (`bopos.target.<host>`) but the **focus Seat is one shared key**, so
   the Seats-tab → Control workflow survives. The Control host is currently one
   picker with `storageKey: "bopos.target.control"` and `followFocusSeat: true`
   (`facilitator.js:101-104`). With N columns: does picking a Seat on the Seats
   tab move every column, one of them, or none? The per-column storage key
   follows from the answer. `07`'s rule that a picker adopts the focus *when it
   moves, not on load* still holds.
5. **Which column owns capture-as-step** — see below.

## Capture-as-step: convene a UX consult (Bob, 2026-07-30)

Today `renderShowCapture()` (`facilitator.js:290`) appends one
`Capture as Show step` button to the picker host, and `presetScope()`
(`facilitator.js:390`) reduces that one selection to a coarse server scope
(all / groups / one seat) before sending `preview_show_preset_capture`.

Bob: *"per column seems perhaps easiest — but if an all-column capture-as-step
workflow makes sense it's worth considering."* So this is **not** a default to
rubber-stamp. Get a UX-designer eye on it the way
`automation-4-waveform-ux-gate` did: two or three named expert lenses writing
`expert-<lens>.md` in this stitch, then a `judgment.md` recommending one, then
Bob ratifies. Suggested lenses: the live-operator/performance lens (what a
facilitator is doing with two hands mid-show), the show-authoring lens (what a
captured step should *mean* when replayed), and the calm-ops lens (how many
capture buttons can be on screen before none of them is the obvious one).

The question they should answer: is a Show step captured from **one column's
target**, or from **the whole tab's arrangement across all columns**? The
second reading is the interesting one — N columns *are* an arrangement of
targets, which is exactly what a step is. Note the constraint it runs into:
`preview_show_preset_capture` takes a single coarse scope, so an all-column
capture either reduces the union (losing the arrangement it was trying to
capture) or needs a widened server vocabulary — which `41-preset-primitive`
deliberately declined once. Say which, and what it costs.

Ground the lenses in the real code, not in the abstract: `41-preset-primitive`'s
tied `proposal.md` + `decisions.md` (R5, Q6 capture-as-step), the
`entity-architecture-review` ratified model (shows target groups **by name**;
collections start as show steps), and `presetScope()`'s existing reduction.

## Deliverable

`decisions.md` in this stitch, mockups at 1280/1680/2560 (the mockup at
`.lore/items/2026-07-27-control-panel-ui-and-architecture-braindump/content/mockup.png`
is the north star, qualified by `mockup-fidelity-notes.md` beside it), the
`expert-*.md` + `judgment.md` set for the capture question, and a lore item if
the whole artifact is worth keeping. Then un-`.waiting` `4-n-columns` and
record the ratified calls in its instructions.
