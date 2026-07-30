# 3-iframe-retirement

**Ruled by Bob, 2026-07-30: RETIRE THE CONTROL-TAB IFRAME.** Mount
`ControlColumn` directly in the parent document; `/facilitator` becomes the
standalone **Remote** view only. No design gate.

**N stays 1.** This stitch moves the surface between documents and changes
nothing about how many columns there are — that is `4`. Needs `2` done first.

## Why

It removes the cross-document coordination that `control-panel.css`'s header
and CLAUDE.md Playwright gotcha 15 both exist because of, and it retires the
app's clearest **design-language §12** violation in the same edit.

## What to touch

- `index.html:31` — `<iframe id="dashboard-live-view" src="/facilitator?embedded=1">`
  becomes the column's mount point in `#tab-control`.
- `css/style.css:44` — the `#dashboard-live-view` rule sets
  `background:var(--bg)` **and** a border, which is exactly §12's named
  mistake: a bordered region painted in the ground colour, so the panel
  *"swims in empty space"* (Bob). **Delete the declaration with the iframe;
  do not port it to the column container.** The ground shows only as gutter.
  There is a second declaration in the `max-width:860px` block at
  `css/style.css:46`.
- `js/facilitator.js` — split page bootstrap from surface hosting. The
  `embedded` fork (`:3`) and its four consumers become the difference between
  the two hosts rather than a URL-parameter read:
  - `:125` full manifest vs `dashboard: true` filtering
  - `:143` the same for events
  - `:200` the preset row — Bob's `41` Q4 ruling is that Remote carries **no**
    preset affordance at all, removed not inert
  - `:292` `renderShowCapture`
  `body.embedded` and `css/facilitator.css:72` go away with it.
- The dashboard host now needs what the iframe's page used to provide the
  column: state from `dashboard.js`'s socket rather than a second `BopSocket`.
  Do not open two sockets. Master/mute already live in the Monitor dock
  Globals panel for this document (`03-global-controls-monitor`) — do not
  bring `#master-row` / `#silence` across; Remote keeps its own footer.
- `#event-status` — the column's status output has no home in `index.html`
  yet. Give the column its own, or route to the dock.

## Tests

Migrate the four living journeys off the frame boundary:

- `tests/verify_control_tab.py:145`
- `tests/verify_event_control_panel.py:177`
- `tests/verify_manifest_param_visibility.py:199`
- `tests/verify_preset_control_surface.py:145` — plus four raw
  `contentDocument` evaluates at `:287`, `:299`, `:328`, `:348`

Expect gotcha 17 to bite the moment the surface shares a document with the rest
of the app: scope every selector to the Control host.

**Delete Playwright gotcha 15 from CLAUDE.md** once it stops being true, and
update the `#dashboard-live-view` references in CLAUDE.md (`:297`, `:881-882`)
and `.notes/component-inventory-2026-07.md:243`.

`.loom/dropped/friction-0-docs/shoot_docs.py:93` also frame-locates. It is
dropped work — leave it.

## Verify

`tools/run-tests.sh fast` and `browser` green. Screenshot the Control tab
before/after in light and dark at 1280 and 1680 (the tied `02-token-promotion`
stitch's `shoot.py` is the working harness — and note its recorded bug: it
wrote `bopos.theme` while `theme.js` reads **`bopos-theme`**, so check the shot
is actually in the theme you asked for).
