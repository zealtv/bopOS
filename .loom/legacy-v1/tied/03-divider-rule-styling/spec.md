# Implementation spec — divider rule styling (stitch 03)

Repo: `/Users/bob/repos/bopOS`. Read first: this stitch's `instructions.md`
and `decisions.md` (the ruled design — implement it, do not redesign), the
thread's `../instructions.md`, and `/Users/bob/repos/bopOS/CLAUDE.md` (house
rules + the Playwright gotcha list under "Dashboard browser tests").

## The change

`dashboard/static/css/style.css` only. The relevant existing rules (find them
all — they are spread across several appended blocks, including a
`.show-tab`-scoped block near the end of the file):

```
.show-divider-row{position:relative;display:flex;height:18px;align-items:center;justify-content:center}
.show-divider-row{height:10px;margin:2px 0;border:0;border-radius:0;background:linear-gradient(90deg,transparent,var(--strong-line) 16%,var(--strong-line) 84%,transparent);opacity:.85}
.show-tab .show-divider-named{height:auto;min-height:26px;padding:5px 8px;gap:8px;min-width:0;background:none;opacity:1}
.show-tab .show-divider-named .show-divider-line{flex:1 1 auto;min-width:8px;height:1px;background:var(--strong-line)}
```

Implement exactly what `decisions.md` rules:

1. Named divider rules → `flex:0 0 28px` (fixed length), row stays centred.
   Long names still truncate with ellipsis; the rules stay 28px and stay
   adjacent to the name.
2. Unnamed divider → drop the gradient background entirely; draw a flat 1px
   `var(--strong-line)` rule via an absolutely positioned `::after` on the
   already-`position:relative` row, vertically centred, inset so it does not
   run under the `.show-divider-drag` grab handle. Keep the row height and
   the handle as they are. Make sure the `::after` does not eat pointer
   events (`pointer-events:none`) and does not conflict with the existing
   `.show-drop-before` / `.show-drop-after` box-shadows or the `.focused`
   outline.

Prefer editing the existing declarations over appending new overriding
blocks where that is clean; if you must append, scope with `.show-tab` like
the surrounding density block does.

## Constraints

- CSS only. If you believe JS is required, STOP and report why.
- Do not edit anything under `.loom/tied/` or `.loom/dropped/`, any `.pd`
  file, `facilitator.*`, or loom state. Artifacts go in your stitch dir:
  `.loom/threads/19-show-chrome-fixes/03-divider-rule-styling.stitching/`.
- Both variants keep their `aria-label`s, focus outline, drag behaviour, drop
  indicators, and (named) click-to-edit name.
- Prefer existing `--chrome-*` / colour tokens over new one-off values.

## Verifier

Write `verify_divider_rules.py` in this stitch directory, conventions copied
from `.loom/tied/05-compact-chrome/verify_compact_chrome.py` (repo root by
marker, real `dashboard/server.py` + `tools/simfleet.py` on non-default
ports, headless Chromium, teardown, retained screenshots). Run with
`~/.venvs/bopos/bin/python`. Assert at least:

1. Named divider: each `.show-divider-line` has a **bounded** width — assert
   it equals 28px and is far less than the row's width, with a short name and
   again with a very long name (the long name must truncate, not stretch the
   rules). Gather all rects in a single `page.evaluate` (gotcha 9).
2. Named divider: the name element is horizontally centred within the row
   (within a small tolerance) and the two rules flank it — one entirely left
   of the name, one entirely right.
3. Unnamed divider: computed `background-image` is `none` (no gradient), and
   the `::after` rule exists with height 1px and does not overlap the grab
   handle's rect.
4. Named divider name is still click-to-edit (click it, an input appears,
   commit a new name, the row shows it).
5. Both rows still expose their existing `aria-label`s.
6. Retained screenshots of both divider states, light and dark.

Then re-run these tied suites **unmodified** and report their output:

```
.loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
.loom/tied/04-named-section-dividers/verify_named_dividers.py
.loom/tied/05-compact-chrome/verify_compact_chrome.py
.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
.loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
.loom/tied/02-step-and-divider-icons/verify_step_divider_icons.py
```

Re-running them regenerates their retained screenshots — afterwards run
`git checkout -- .loom/tied/` to restore those artifacts. Delete any
`__pycache__/` your runs create inside stitch directories.

Playwright house rules that bit previous sessions: elements in a non-active
tab panel need `state="attached"` not visible; `#ws-status` is an empty span
when online (also `state="attached"`); no `scroll_into_view_if_needed` or
actionability waits on Show rows (heartbeat re-renders + CSS animations make
them perpetually unstable) — use a one-shot `page.evaluate` `scrollIntoView`
then a fresh `bounding_box()`; compare rects gathered from ONE scroll state;
one type-aware `page.on("dialog")` handler; `page.wait_for_function(expr,
arg=value)`; `inner_text` applies CSS `text-transform`.

## Deliverables

- the edited `style.css`
- `verify_divider_rules.py`
- `verification.md` — exact commands run, real output tails, any deviation
  from spec/decisions with reasoning
- retained screenshots (both states, both themes)

## Acceptance checks (run them; paste real output)

```sh
cd /Users/bob/repos/bopOS
~/.venvs/bopos/bin/python .loom/threads/19-show-chrome-fixes/03-divider-rule-styling.stitching/verify_divider_rules.py
~/.venvs/bopos/bin/python .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
~/.venvs/bopos/bin/python .loom/tied/04-named-section-dividers/verify_named_dividers.py
~/.venvs/bopos/bin/python .loom/tied/05-compact-chrome/verify_compact_chrome.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
~/.venvs/bopos/bin/python .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
~/.venvs/bopos/bin/python .loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
~/.venvs/bopos/bin/python .loom/tied/02-step-and-divider-icons/verify_step_divider_icons.py
git checkout -- .loom/tied/
```

Every suite must end `0 failure(s)`. If a tied suite asserts something this
change legitimately alters (e.g. the 04 suite asserting the rules stretch),
STOP and report the exact assertion — do not edit a tied suite. Do not
commit; leave the tree for the orchestrator.
