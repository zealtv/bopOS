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

## The card chrome has no home in the parent document — found 2026-07-31

From `1-columns-design` (ratified), found by *building* the mockup rather than
by reading files, which is why nothing before this noticed.

`.live-card`, `.live-card-head`, `.name`, `.dot`, `.send-all`,
`.promoted-controls`, `.live-param-branch` and `.empty` are all declared in
**`css/facilitator.css` (lines 26-52)** — a stylesheet `index.html` does not
load. `index.html:3` loads `style.css`, `param-generator.css`,
`control-panel.css`, `value-box.css`, `target-picker.css`, and nothing else.

Today that is invisible because the Control tab is an iframe of
`facilitator.html`, which *does* load it. **The moment the iframe goes, the
parent document has no card chrome at all** — the surface renders unstyled
above the parameter rows.

This is `05e`'s pattern for the fourth time: component rules written onto a host
stylesheet. So the fix is the `05e` fix — a component stylesheet the card owns,
loaded by both documents — **not** a copy-paste of `facilitator.css`'s values.
Those are tablet-first (44px rows, 19px card names, 18px/20px padding) and would
drag Remote's metrics onto the desktop. Write it at desktop metrics
(`--row-h`, `--gap`, `--pad-panel`), per Bob's 2026-07-30 *"let facilitator
collapse — we will restyle remote for iPad as a standalone pass"* ruling, and
measure the Remote delta with `cascade_probe.py --doc facilitator`, recording it
in `feature-backlog/49-remote-ipad-restyle` the way `05e` and `07` did.

`1-columns-design`'s `mockup.py` contains a working desktop-metric version of
exactly this block, written against the real markup — start from it.

Related, while you are in that file: `css/facilitator.css:71`'s
`main[data-live-view=aggregate] .all-card{grid-column:1/-1}` is **dead**.
`selectionMode` (`facilitator.js:324-329`) only ever returns
`all`/`groups`/`seats`/`mixed`. The codebase's one existing multi-column rule has
an inert exception in it — do not port it forward as prior art.

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
- **Do not wire the focus seat into the Control host.** `1-columns-design` D7
  (Bob, 2026-07-31) retires `followFocusSeat` on Control **outright, at every
  N** — so `targetPicker.create` here drops the flag, and the cross-document
  `storage`-event listener (`target-picker.js:365-367`) needs no same-document
  replacement for this consumer. That listener fires only for *other* documents,
  so once Control shares a document with the Seats tab it would have gone silent
  anyway; D7 means there is nothing to restore. The Seats → Control workflow
  returns as an explicit "Open in Control" action, owned by `4`.

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
