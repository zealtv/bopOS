# Implementation spec — collapsible inspector sidebar (stitch 02)

Repo: /Users/bob/repos/bopOS. Work ONLY on:
- `dashboard/static/js/show.js`
- `dashboard/static/css/style.css`
- a new verifier at
  `.loom/threads/18-show-chrome-density/02-inspector-sidebar.stitching/verify_inspector_sidebar.py`

Do not touch loom state (no claim/tie), no `.pd` files, no other dashboard
tabs, not `facilitator.*`. Full context: `instructions.md` and `decisions.md`
in the same stitch directory (read both first).

## Behavior

The Show tab's inspector (`.show-inspector-shell`, rendered by
`renderLoadedShow()` in show.js) becomes a collapsible sidebar.

- **State:** a module-level boolean in show.js (e.g. `inspectorOpen`,
  default `true`). Session-only: survives every `render()`, resets on page
  reload. No localStorage, no server persistence.
- **Expanded:** current inspector rendering, width 300px (unchanged), with
  one addition: an icon toggle button in the sidebar's top-right
  ("Hide inspector", `aria-expanded="true"`, `aria-controls` the panel).
- **Collapsed:** the sidebar renders as a ~40px vertical rail that is one
  big button — vertical "Inspector" text label, keyboard-focusable,
  "Show inspector", `aria-expanded="false"`. The step list reclaims the
  width (workspace grid second column 300px → 40px).
- **Focus while collapsed (ruled by Bob):** single click on a step row,
  divider row, or message pill selects silently — focus state updates, the
  sidebar stays collapsed. **Double-click** on any of those expands the
  sidebar showing that item's inspector (set focus AND open). Enter/Space
  on a focused row keeps its existing meaning (select, stay collapsed).
  Keyboard path to expand is the rail button itself.
- Preserve untouched: inline step-name editing, message builder, wire
  preview, pill ⌘C/⌘X/⌘V/Delete, undo, edit bar semantics, the two-element
  UI guard, the target-picker `<details>` open state, the console panels.

## Footprint stability (the point of the stitch)

Expanding/collapsing, or inspector content growth (long message builder,
many then-actions, big target roster), must NEVER move the OSC consoles
(`#show-consoles`) or the step list vertically. Mechanism: take the
sidebar out of the document-height equation — the `.show-workspace` row
height must be driven by the step-list shell only; the inspector panel is
viewport-capped (it stays `position:sticky; top:72px`, add
`max-height:calc(100vh - 90px)`) and scrolls internally
(`overflow-y:auto`). Suggested approach: make `.show-workspace`
`position:relative` with right padding for the sidebar width, and the
`aside` absolutely positioned (`top:0; right:0; bottom:0`) with the sticky
scrolling panel inside it — but any mechanism passing the acceptance
checks is fine. Keep the existing container query
(`container-name:show-inspector`) working on the panel that has the width.

## Responsive

- ≤1020px (single-column workspace): inspector below the list, static, as
  today. Toggle still works; collapsed renders as a slim horizontal
  "Inspector" bar. Don't regress the 768px layout or the console
  twin-column/stacked behavior from `03-responsive-osc-terminals`
  (Chromium `::details-content` note in that tied stitch's
  `verification.md`).
- Light and dark themes both styled via the existing CSS variables; no
  hard-coded colors.
- No page-level horizontal overflow at 1280px or 768px.

## Verifier

Write `verify_inspector_sidebar.py` copying the conventions of
`.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py` (repo
root by marker — walk up until `tools/simfleet.py` exists; non-default
ports; real `dashboard/server.py` + `tools/simfleet.py`; teardown;
screenshot retention into the stitch dir). Run it with
`~/.venvs/bopos/bin/python`. It must check at least:

1. Terminals keep their viewport position (compare `#show-consoles`
   bounding rect, same scroll state) while the inspector grows: focus a
   message, add many raw args / then-actions, rect unchanged.
2. Collapse → step list/console widths grow; expand → restored; state
   survives a re-render (trigger any document change) but page reload
   resets to expanded.
3. Collapsed + single click on a row: focus changes (row gets `.focused`),
   sidebar stays collapsed. Double-click on a step row and on a message
   pill: sidebar expands showing that inspector.
4. Toggle button reachable and operable by keyboard; `aria-expanded`
   correct both ways.
5. All of the above at 1280px; sanity layout + no horizontal overflow at
   768px; light and dark screenshots retained.

## Playwright house rules (generalize; they bit previous sessions)

- Anything inside a non-active tab panel resolves but never becomes
  visible — wait with `state="attached"` for ANY such element.
- The app re-renders on heartbeats and CSS-animates some controls:
  never rely on actionability/stability waits or
  `scroll_into_view_if_needed`; use one-shot `page.evaluate` scrolls and
  fresh `bounding_box()` reads.
- Compare bounding rects only from ONE scroll state; gather all rects in
  a single `page.evaluate`.
- One type-aware `page.on("dialog")` handler (prompt→text, else accept).
- `page.wait_for_function(expr, arg=value)` — keyword-only.
- `inner_text` applies CSS `text-transform`.

## Acceptance checks (run these; report actual output)

```sh
cd <repo-root>
~/.venvs/bopos/bin/python .loom/threads/18-show-chrome-density/02-inspector-sidebar.stitching/verify_inspector_sidebar.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
~/.venvs/bopos/bin/python .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
```

(Confirm the two tied verifier filenames by listing those directories; run
them UNMODIFIED.) All must end with 0 failures. When done, summarize what
you changed, how you verified it, and anything you could not do. If you
could not complete something, say so explicitly — do not fake results.
