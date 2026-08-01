# Implementation spec — named section dividers (stitch 04)

Repo: /Users/bob/repos/bopOS. Read first: `instructions.md` in this stitch
directory (it carries Bob's 2026-07-21 ruling), `/Users/bob/repos/bopOS/CLAUDE.md`,
and the mockup `.loom/tied/01-layout-review/wireframes.html` (divider
presentation reference).

Work ONLY on:
- `dashboard/show_model.py` (+ its doc header if it enumerates item fields)
- `dashboard/server.py` (only if a new/extended op is needed for divider alias patching)
- `dashboard/static/js/show.js`
- `dashboard/static/css/style.css`
- a new verifier `verify_named_dividers.py` in this stitch directory

Do not touch loom state, `.pd` files, other tabs, `facilitator.*`.

## Model (additive)

- Divider items gain `alias` (text or null, default null). `clean_divider`
  preserves it; `add_divider` mints with `alias: None`. Older documents
  without the field load fine.
- Alias patching follows the existing step-alias path (partial patch op;
  reuse/extend the existing update op rather than inventing a parallel
  one). Undo, persistence to the show file, and second-client broadcast
  must behave exactly like step aliases — these come from the existing
  document plumbing; do not build new mechanisms.
- `duplicate_item` on a divider keeps copying the whole dict (alias copied,
  fresh uid) — verify, don't reimplement.

## Row rendering

- Named divider: the name centred, horizontal rule lines flanking it either
  side (per wireframes.html), both themes via existing CSS variables. The
  row may grow a little taller than today's 10px rule to fit the text
  (small, dim, uppercase-free — don't let CSS text-transform change what
  tests read via inner_text).
- Unnamed divider: exactly today's plain gradient rule.
- Long names truncate/ellipsize; no page widening. Drag reorder, click
  select, Delete/Backspace, and the `.focused` outline keep working
  unchanged. NO inline editing on the row itself (ruled).

## Inspector editing (the ruled click-to-edit pattern)

Reference implementation: step names (`stepNameEdit`, `data-show-step-name`,
`data-show-step-name-input`, the keydown/blur handlers, and
`commitStepName`). Generalize rather than copy-paste three times if clean.

- **Divider inspector:** replace the static `<h3>Divider inspector</h3>`
  with the click-to-edit bold title: shows the alias, or an "Untitled
  section"-style placeholder when unset; single click/tap or Enter/F2
  while focused swaps in a selected input; Enter/blur commits, Escape
  restores, blank commits null (back to untitled). Keep the
  "Section divider" context line.
- **Message inspector:** remove the visible `alias` labelled input; the
  `<h3>Message inspector</h3>` becomes the click-to-edit title showing
  `message.alias`, with the derived `messageLabel(message)` as the
  unset-state placeholder text. Same commit/cancel/blank semantics. The
  persisted field stays `alias`; `pillColourClass` hashing is untouched —
  same alias must yield the same pill colour class as before this change,
  and a rename re-hashes exactly as the old input did.
- Titles sit inside the (new, from stitch 02) `.show-inspector-panel`,
  which reserves `padding-right:34px` on first-child titles for the
  collapse toggle — keep the new titles clear of that button.

## Verifier

`verify_named_dividers.py`, conventions from the newest tied verifier
`.loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py` (repo root
by marker, non-default ports, real server + simfleet, teardown,
screenshots retained here). Run with `~/.venvs/bopos/bin/python`. Cover at
least: divider naming via click-to-edit (commit / Escape-cancel / blank →
untitled; pointer and Enter/F2 paths); message alias via the new title
with identical semantics; pill colour class equality for same alias before
rename and re-hash after rename; named-row lines-either-side rendering in
light+dark (screenshots); unnamed row unchanged; persistence across
reload; a second page (two contexts) sees the alias broadcast; duplicate
divider copies alias with fresh uid; truncation without horizontal
overflow at 768px; drag/selection still work; re-run guard: also run
`.loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py` and
`.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py`
UNMODIFIED.

Playwright house rules (generalize — they bit previous sessions):
elements in non-active tab panels need `state="attached"` waits; never
rely on actionability/stability waits or `scroll_into_view_if_needed`
(heartbeat re-renders + CSS animation) — one-shot `page.evaluate` scrolls
and fresh `bounding_box()`; gather compared rects in one `page.evaluate`;
one type-aware dialog handler; `wait_for_function(expr, arg=value)`;
`inner_text` applies `text-transform`.

## Acceptance checks (run them; report real output)

```sh
cd <repo-root>
~/.venvs/bopos/bin/python .loom/threads/18-show-chrome-density/04-named-section-dividers.stitching/verify_named_dividers.py
~/.venvs/bopos/bin/python .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
```

All must end `0 failure(s)`. Summarize what changed, how verified, and
anything you could not do — say so explicitly rather than faking results.
