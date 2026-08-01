# Verification -- 02-edit-bar-and-inline-step-name

## What changed

- `dashboard/show_model.py`: new `duplicate_item(show, uid)` pure model
  operation. Deep-copies the step (or divider), mints a fresh uid for the
  item and, for a step, every nested message; inserts the clone immediately
  after the original. `then_actions` (including `goto` targets) are copied
  verbatim -- they reference existing step uids that stay valid.
- `dashboard/server.py`: wires WS op `duplicate_item` through the existing
  `apply_show_mutation` funnel (same persist-then-broadcast-then-undo-stack
  path as every other structural edit).
- `dashboard/static/js/show.js`:
  - New persistent `.show-edit-bar` rendered inside `.show-list-shell`,
    immediately above `.show-rows-box` (`renderEditBar`, `editBarButton`).
    `+ Step` / `+ Divider` left, flexible centre spacer, Duplicate / Delete
    right. Duplicate/Delete disable (not hide) when nothing structural is
    selected or a message is focused; `+ Step`/`+ Divider` always stay
    enabled.
  - `selectedStructuralItem` / `structuralAnchorUid` / `insertionAfterUid`
    implement the ratified insertion rule: relative to (after) the selected
    structural row, falling back through a focused message's parent step,
    falling back to append at the end.
  - `duplicateSelected` sends the new `duplicate_item` op and reuses the
    existing `pendingItemAdd` focus/scroll-to-new-row tracking.
  - `deleteItem` no longer calls `confirm()` -- ratified: no delete
    confirmation, undo covers mistakes.
  - Removed: the bottom `.show-add-bar`, `renderArrange` and its call sites
    in the step/divider inspectors, and the old `#show-step-alias` visible
    input field. `data-item-add`, `data-item-add-end`, `data-item-delete`
    click handlers are gone (replaced by `data-edit-bar-action`).
  - Inline step name: `stepNameEdit` module state; the step inspector's
    bold `<h3 class="show-step-name">` is click/tap/Enter/F2-editable,
    swapping to `<input data-show-step-name-input>`. Enter and blur commit
    (mapping blank to the null/"Untitled step" state); Escape restores.
    No per-keystroke saves -- the value only round-trips on commit, same
    `updateStep(uid, {alias: ...})` path the old field used. A draft-
    preservation pattern mirrors the existing `#show-cue-lead` handling so
    an unrelated broadcast mid-rename can't wipe uncommitted text.
  - Message pills, their `⌘C/⌘X/⌘V/Delete` keyboard flow, the message
    inspector, and the step inspector's "Add message" button are untouched
    (hard retention constraint from `01-layout-review/decisions.md`).
- `dashboard/static/css/style.css`: new `.show-edit-bar*` rules (icon+text
  wide, icon-only + hidden label below 900px, touch-sized 40px targets,
  disabled-state dimming); new `.show-step-name` / `.show-step-name-input`
  rules (bold, un-transformed -- overriding the global `h3{text-transform:
  uppercase}` rule, which would otherwise shout the operator's typed name).
  Removed the now-dead `.show-add-bar` and `.show-arrange-grid` rules.

## Commands run

```
node --check dashboard/static/js/show.js
python3 -c "import ast; ast.parse(open('dashboard/show_model.py').read()); ast.parse(open('dashboard/server.py').read())"
~/.venvs/bopos/bin/python .loom/threads/show-layout-polish/02-edit-bar-and-inline-step-name.stitching/verify_edit_bar.py
~/.venvs/bopos/bin/python .loom/tied/6-message-editing/verify_show_editing.py
~/.venvs/bopos/bin/python .loom/tied/p4-step-list-scrollbox/verify_show_scrollbox.py
~/.venvs/bopos/bin/python .loom/tied/p5-inspector-defaults/verify_show_inspector_defaults.py
~/.venvs/bopos/bin/python .loom/tied/p6-drag-and-keyboard-editing/verify_show_drag_editing.py
~/.venvs/bopos/bin/python .loom/tied/6b-show-management/verify_show_management.py
~/.venvs/bopos/bin/python .loom/tied/5-inspector/verify_show_inspector.py
~/.venvs/bopos/bin/python .loom/tied/p3-global-transport-and-cue-lead/verify_show_transport.py
```

## Results

**New verifier -- `verify_edit_bar.py`: all 52 checks PASS.** Covers (no
simulated fleet needed; this stitch never touches Seat/device state):

- desktop (1280px) and narrow (768px, `has_touch=True`) layouts; edit bar
  placement (immediately above `.show-rows-box`, inside `.show-list-shell`);
  icon+text at wide vs. icon-only + preserved `aria-label`/`title` below
  900px; touch-sized (>=40px) hit targets at both widths
- Duplicate/Delete disabled with nothing selected and on message focus;
  `+ Step`/`+ Divider` stay enabled in both cases
- insertion after the selected structural row vs. append with nothing
  selected
- `duplicate_item`: step clone gets a fresh uid and every nested message
  gets a fresh, disjoint uid, with content (aliases) carried over; divider
  duplicate allowed with a fresh uid
- Delete raises **no** confirm dialog, even for a non-empty step
- undo reverses duplicate and delete cleanly
- persistence to the show JSON file and second-client (two-page) broadcast
  parity
- inline step name: click opens a focused, pre-selected input; Enter
  commits; Escape restores the prior value; blur (moving focus to a sibling
  field in the same step editor) commits; blank commits to the
  `Untitled step` state; F2 opens edit from keyboard focus; touch tap opens
  edit; rename persists across reload
- regression coverage: message pill `Ctrl+C`/`Ctrl+V` keyboard flow, and
  mouse drag reorder of a structural row, both still work
- no page-level horizontal overflow at 1280px or 768px
- zero console/page errors on both the wide and narrow clients

Screenshots retained in this stitch directory: `review-1280-show.png`,
`review-768-show.png`.

**Adjacent tied Show editing/scrollbox verifiers (unmodified), re-run:**

| Verifier | Result | Notes |
|---|---|---|
| `6-message-editing/verify_show_editing.py` | 7/8 checks pass, then fails | Pill copy/cut/paste/move, keyboard copy+paste, keyboard delete, keyboard undo all **pass**. Fails at `page.locator('[data-item-add-end="step"]').click()` -- that selector no longer exists (bottom add bar removed per ratified design). |
| `p4-step-list-scrollbox/verify_show_scrollbox.py` | 1 check passes, then errors | Console collapse/counter check passes. Errors reading `.show-add-bar` geometry -- selector removed. |
| `p5-inspector-defaults/verify_show_inspector_defaults.py` | 13/13 checks pass, then fails | All then-action-row and target-picker/disclosure checks (headless model + browser) pass. Fails at the same `[data-item-add-end="step"]` click at the very end. |
| `p6-drag-and-keyboard-editing/verify_show_drag_editing.py` | **all checks pass** | Message and structural-row drag reorder, keyboard cut/paste/delete/undo, reload persistence -- no regressions; this stitch never touched the drag machinery. |
| `6b-show-management/verify_show_management.py` | 2/3 checks pass, then fails | Show creation/switching passes. Fails at the same `[data-item-add-end="step"]` selector while checking a newly-created show starts with an "add affordance." |
| `5-inspector/verify_show_inspector.py` | fails immediately | First browser assertion in this script is `page.fill("#show-step-alias", ...)` -- that field is exactly what `02` replaces with inline click-to-rename. |
| `p3-global-transport-and-cue-lead/verify_show_transport.py` | 1 check passes, then fails | Legacy-show-loads check passes. Fails at the same `#show-step-alias` fill. |

All seven failures above trace to two selectors that the ratified
`01-layout-review/decisions.md` design explicitly retires: `.show-add-bar`
/ `[data-item-add-end]` (replaced by `.show-edit-bar` /
`[data-edit-bar-action]`) and `#show-step-alias` (replaced by the inline
`h3.show-step-name` / `[data-show-step-name-input]` rename flow). This is
the expected, intended consequence of the ratified redesign, not a
regression -- every behavior those old scripts were exercising up to that
point (message pill drag/copy/cut/paste/keyboard flow, structural drag
reorder, then-action rows, target picker/disclosure, show
creation/switching, legacy-show loading) still passes, and `verify_edit_bar.py`
covers the replaced surface with equivalent-or-stronger checks. Nothing
here needs Bob -- it's the direct, ratified consequence of `02`'s brief
("once feature parity exists, remove both `.show-add-bar` ... and the
Arrange section"). These old scripts are frozen acceptance snapshots of
earlier stitches; a future docs/loom-hygiene pass could retire or update
their now-superseded assertions, but that's out of this stitch's scope.

## Unverified boundaries

- No real Pi / hardware involved; not applicable to this stitch (pure
  dashboard UI + show-model surface).
- Did not attempt to update or retire the seven pre-existing tied verifiers
  above; they are frozen historical acceptance artifacts for already-tied
  stitches, and instructions ask only to re-run them and report.
- Did not add automated coverage for every intermediate viewport between
  768px and 1280px; the two ratified breakpoints (900px bar threshold,
  1280px/768px review widths) are exercised directly.
