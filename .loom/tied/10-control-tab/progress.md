# 10-control-tab — done

Dashboard is now **Control**, with a reusable target filter, cues above the
surface, and a preset shelf that follows the target.

## What shipped

- **Rename.** `Dashboard → Control` in the tab label, ids
  (`#tab-button-control` / `#tab-control`), `data-tab`, `TAB_NAMES`, and the
  heading. **`#dashboard` still resolves** through a `TAB_ALIASES` map, applied
  on load *and* on `hashchange` — renaming a route without that silently breaks
  every existing link and bookmark.
- **`dashboard/static/js/seat-filter.js`** — the reusable All / Groups / Seat
  component: renders into any host, owns its own roving-tabindex keyboard
  behaviour, reports the chosen target back, and leaves what to do with it to
  the host. Loaded by both pages.
- **The surface follows the filter.** `renderCards` now shows the aggregate
  card, the group cards, or exactly one Seat card. This replaces the old
  two-way `All & Groups | Seats` toggle, which is gone.
- **Presets follow the target.** `save_preset` / `load_preset` take a scope, and
  `preset_scope_seats` resolves it. A save captures only the Seats in scope; a
  load applies only to them. Presets saved before this change carry no scope and
  still behave as whole-venue — checked by falling through to "every seat".
- **Cues** already sat above the surface in `facilitator.html`; the ratified
  placement is now pinned by a check so a later layout change cannot quietly
  move them.

## Correction carried into code

The Control tab hosts **no patch deployment** — the picker stays on the Patches
tab. The verifier asserts both halves: no picker inside `#tab-control`, and the
picker still present on `#tab-patches`.

## Two shelves would have been two shelves

The embedded surface has its own preset section and the Control tab has
`#preset-bar` with *Save as…*. Rather than showing both, the Control tab's
shelf stays the one and became scope-aware; the iframe's own shelf remains a
standalone-only affordance.

That left a cross-document problem: the filter lives inside the iframe, the
shelf outside it. Solved with **shared storage plus a `storage` event** — the
filter writes its mode and Seat, the parent document listens and re-renders. The
same shared key is what makes "the global selected seat" real: `selectSeat()` on
the Seats tab writes it, so choosing a Seat there is the Seat the Control filter
lands on. That is also the honest limit of "global" here — the surface is a
separate document, so a shared key is the mechanism, not a shared variable.

## Bug found by the verifier

Adding the shelf refresh to `activateTab` introduced a **temporal dead zone**
crash: `activateTab(activeTab, false)` runs at line 108, but `presetNames` was
declared with `let` at line 249. Opening straight onto the Control tab (which
`#dashboard` now does) threw a `ReferenceError` and killed the whole script —
the page just never connected. `presetNames` moved up to the other module-level
state where it belonged.

## Verification

- **`tests/verify_control_tab.py` — new, 15/15 green.** The rename and the old
  bookmark; no picker on Control and the picker still on Patches; the filter is
  the reusable `window.SeatFilter`, offers All/Groups/Seat, and each mode scopes
  the surface; cues above the surface (by document position); the filter follows
  a Seat chosen on the Seats tab; the shelf names the target and a Seat-scoped
  save captures that Seat only.
- `verify_control_surface_component` 11/11 — updated: it used to expect the All
  and group cards together, which the filter no longer shows at once, so it now
  walks the filter.
- `verify_generator_drawer` 38/38, `verify_device_control_panel` 12/12,
  `verify_live_param_checkbox` 10/10.

## Noted for the next reader

A Seats-roster row's centre is its name `<input>`, and the row's click handler
deliberately ignores clicks inside inputs — a Playwright `click()` on the row
selects nothing. Aim at the `small` (ID label) instead.

## Provisional by Bob's own framing

"Let's try cues up the top." The cue strip is kept a self-contained block so it
can be relocated without touching the surface below it.
