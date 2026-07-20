# 04-named-section-dividers

Dividers mark sections, so sections can be named: give dividers a name and
the mockup's presentation — the name centred with horizontal lines either
side (see `.loom/tied/01-layout-review/wireframes.html` and lore
`2026-07-20-show-chrome-density-braindump`).

## Outcome

- Additive `alias` field on divider items in the show document
  (`dashboard/show_model.py`), defaulting to null/untitled; persistence,
  undo, duplicate (fresh UID, alias copied), and second-client broadcast
  behave like step aliases.
- Divider row renders the name with the lines-either-side styling in both
  themes; unnamed dividers render a plain rule (current look).
- **Editing surface (ruled by Bob, 2026-07-21):** the step inspector's
  click-to-edit name pattern is the pattern. The divider inspector renders
  the name as the bold title; single click/tap (or Enter/F2 while focused)
  swaps in a selected input; Enter/blur commits, Escape restores, blank
  returns to untitled. No inline editing on the row itself.
- **Same ruling extends to messages:** replace the message inspector's
  visible `alias` input with the click-to-edit bold title (the alias, or
  the derived message label as placeholder when unset), identical
  keyboard/commit semantics. The persisted field stays `alias`; pill
  colours (hashed from message alias) must be unaffected by the
  presentation change. Do this here so all three inspectors ship the one
  pattern together.
- Long names truncate/ellipsize without widening the page; dividers stay
  drag-reorderable and selectable exactly as today.

## Verification

Focused Playwright: divider and message naming via the click-to-edit title
(commit/cancel/blank semantics matching step names, pointer + touch +
Enter/F2); pill colouring behaves exactly as with the old input (same alias
→ same colour; a rename re-hashes as today); persistence + second-client;
duplicate
copies the alias with a fresh UID; themed rendering with lines either side;
truncation at narrow width; drag/selection regressions; no horizontal
overflow. Re-run the tied edit-bar suite unmodified. Retain screenshots.
