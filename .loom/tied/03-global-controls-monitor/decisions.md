# Decisions — 03-global-controls-monitor

Implemented Bob's ratified direction: master fader, MUTE ALL, and the event
lead time now share a **Globals** panel in the Monitor dock. Behaviour and wire
semantics are unchanged — this was relocation only.

## Calls made

**The controls are authored in `index.html` and adopted by the dock.**
`dashboard.js` binds `#master`, `#master-out`, and `#mute-all` at parse time and
loads *before* `monitor.js`. Rebuilding those nodes inside `monitor.js` would
have broken every existing binding and forced a script reorder. Instead
`#global-controls` is authored (hidden) in `index.html` and `monitor.js` moves
the live nodes into `#monitor-panel-globals`. Element ids are preserved, so
`renderHeader()`, the master throttle, and the mute handler are untouched, and
`tests/verify_device_control_modes.py` still drives the same ids.

**Globals is the first Monitor tab.** `MONITOR_TABS` gained `"globals"` at the
head; the default active tab stays `"out"`. Stored layouts from before this
change filter out unknown kinds and append missing ones, so existing operators
pick up the panel without losing their split/pane arrangement.

**Muted state is never invisible.** The dock header is always on screen (45px
when collapsed), so it carries a red `MUTED — UNMUTE` flag, hidden unless muted.
Clicking it delegates to `#mute-all`'s existing handler rather than duplicating
the mute semantics. `renderHeader()` in `dashboard.js` is the single writer of
the flag's visibility — it already runs on both the optimistic local toggle and
the server `mute_all` broadcast, so there is no lag and no second source of
truth.

**The Show transport loses event lead entirely — no read-only indication.**
The stitch allowed keeping one "if losing it hurts". It does not: the Monitor
dock is app-wide and one click from the Show tab, whereas a read-only echo would
be a second place to look at a number that can only be changed elsewhere. This
also retired the Show tab's `eventLeadDraft` re-render preservation dance; the
dock control is not rebuilt on broadcasts, so a focus guard is enough.

The standalone facilitator page keeps its own `#event-lead` control. That
surface is a separate tablet-first view with its own constraints and no Monitor
dock.

## Carried forward

- **"Monitor" may want renaming.** Bob's 2026-07-27 note: the dock will likely
  grow a seat map and other visualizations, so the name may stop fitting. Not
  acted on here; a future naming pass should find this.
- Adding the Globals panel touched the dock's header/tab chrome, which
  `01-control-panel/8-manifest-reorder` and `02-app-wide-rollout-design` also
  rewrite. Both should treat the Globals panel as part of the surface they
  restyle.

## Verification

`tests/verify_global_controls_monitor.py` (new living journey, 17 checks): the
three controls are absent from header / Control tab / Show transport, present
and grouped in the Globals panel, functional (master → `set_master`, lead →
`set_event_lead`, MUTE ALL → muted), the mute flag is visible and operable with
the dock collapsed, and the Globals selection survives a reload.

`./tools/run-tests.sh fast` — 196 tests OK.
`./tools/run-tests.sh browser` — all 14 journeys PASS, including
`verify_device_control_modes.py`, whose two MUTE ALL clicks now go through a
`click_mute_all()` helper that opens the Globals panel and re-collapses the dock
so the fixed dock does not cover later targets.
