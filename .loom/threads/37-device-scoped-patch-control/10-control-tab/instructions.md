# 10-control-tab

Rename the Dashboard tab to **Control**, give it a reusable target filter, move
cues to the top, and reserve the Presets shelf.

**Authority:** `.loom/tied/6-control-tab-rename-design/decisions.md` (Bob,
2026-07-25).

**Depends on:** `07-control-surface-component`.

## Scope correction — read first

**Bob:** "the dashboard is what is being renamed to control, not patches. patch
deployment to the fleet or to a pinned device happens on the patch tab."

This tab hosts **no patch deployment**. The bite-2 target picker stays on the
Patches tab and does not move. The proposal's mockup implied otherwise; the
ratified record corrects it.

| Tab | Owns |
|---|---|
| Patch | patch deployment — fleet *and* per-device pin |
| Control | live control only (the renamed Dashboard tab) |

## Ratified

1. **Dashboard → Control.** Tab label, `TAB_NAMES` entry
   (`dashboard.js:59`), the `#tab-button-dashboard` / `#tab-dashboard` ids and
   `data-tab` hooks in `index.html:9,16`, the heading at `index.html:17`, and
   `location.hash` handling. **Keep a hash/route fallback** so an existing
   `#dashboard` bookmark still lands on the tab.
2. **Target filter (All / Groups / Seat) as a reusable component** — not a
   one-off widget. It reuses the global selected seat. Today the equivalent is
   `[data-live-scope-view]` in `facilitator.js:385` (a two-way
   aggregate/seats toggle); this generalises it and makes it available to other
   surfaces.
3. **Cues at the top**, above the surface. Bob's "let's try" is provisional —
   keep the cue strip a self-contained block that can be relocated without
   touching the surface below it.
4. **Presets shelf reserved**, and **presets follow the target filter**: saving
   under "All" is a different preset from saving under "Seat 2". Placement and
   that scoping rule are settled here; *what* a preset captures, how it loads,
   and generator interpolation stay with thread **41**.

## Structural reality

The Dashboard tab is an **iframe** onto `/facilitator?embedded=1`
(`index.html:22`), and `/facilitator` is also a standalone entry. Restructuring
inside `facilitator.html` keeps one implementation for both; replacing the
iframe is a much larger move and is **not** authorised by this ratification.
Whichever you choose, say why in `decisions.md`.

Note `renderPresets()` (`facilitator.js:568`) currently hides the preset section
when embedded — the reserved shelf changes that assumption.

## Verification

`tests/` (thread-27 policy). Cover: the tab reads Control and old hash routes
still resolve; the filter scopes the surface for all three targets; cues render
above the surface; the preset shelf is present and scoped by the filter.

**Trap (CLAUDE.md gotcha 8):** elements in a non-active tab panel resolve but
never become visible — wait with `state="attached"`.
