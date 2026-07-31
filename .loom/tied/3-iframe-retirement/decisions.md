# Decisions — 3-iframe-retirement

Ruled by Bob 2026-07-30: retire the Control-tab iframe. No design gate. N stays
1; `4-n-columns` carries the ratified column layout.

## What moved

`index.html:31`'s `<iframe id="dashboard-live-view" src="/facilitator?embedded=1">`
is `<div id="control-column-host">`, and `js/control-host.js` mounts
`ControlColumn` in it against `dashboard.js`'s existing socket and state.
`/facilitator` is the standalone **Remote** view only; `js/facilitator.js` is
now that page's bootstrap and nothing else.

Gone with it: a second websocket, a second copy of the installation state, the
`embedded` URL parameter and its four consumers, `body.embedded`, and the
document boundary four browser journeys reached through.

## The column owns its markup, not just its state

`2-control-column-component` gave the column its instance state but left it
reading `#cards`, `#target-picker-host` and `#event-status` out of the host's
HTML. Mounting in a second document would have meant authoring that skeleton
twice, and mounting N of them would have meant duplicate ids. So `create()`
now writes its own DOM — `.control-column-head` / `.control-column-picker`,
`.control-column-cards`, `.control-column-status` — and nothing inside is
addressed by id. `4-n-columns` adds a column by adding a mount point.

## The card chrome belongs to the CONTROL PANEL, not to the column

The stitch found (via `1-columns-design`'s `mockup.py`, by building rather than
reading) that `.live-card`, `.live-card-head`, `.name`, `.dot`, `.send-all`,
`.promoted-controls`, `.empty` and `.live-param-branch` were all declared in
`css/facilitator.css` — which `index.html` does not load. Invisible while the
tab was an iframe of the page that does; unstyled the moment it wasn't.

The instructions proposed a component stylesheet the *card* owns. Working it
through, that is half right and the half that is wrong is load-bearing:

**`.live-card` is the control panel's root, not the column's**, per the
registry in `tests/test_css_component_ownership.py`. Writing
`.control-column .live-card{…}` would have been one component restyling another
from its host — the exact rule that guard exists to enforce — and it would have
failed the guard, correctly. So the split is:

- **`control-panel.css` §18** — the card face, anchored on `.live-card` itself,
  travelling to every host the panel is ever mounted in. `control-panel.css` is
  already loaded by both documents, so this needed no new plumbing.
- **`css/control-column.css`** (new, the app's fifth component stylesheet) —
  the column *shell*: the card it paints on the ground, its head, its cards
  region, the two empty states, the status output, and the per-Seat device
  command disclosure it renders.

This is the fifth occurrence of `05e`'s pattern and the first one where the
right owner was not the component that renders the markup. Worth carrying: the
column *emits* `.live-card`; it does not *own* it.

## Design-language §12, delivered

Both `#dashboard-live-view` declarations in `style.css` are deleted and
**nothing replaces them** — not moved onto the column container. The iframe set
`background:var(--bg)` inside a border, which is §12's named mistake and Bob's
"the control panel is swimming in empty space". The column is a card
(`--panel`, `--group-line`, `--radius-panel`, `--pad-panel`); the tab paints
nothing; the ground shows only as gutter. See `before/` vs `after/`.

## D1 adopted now rather than deferred to `4`

The card face had to be written in this stitch either way, and `1-columns-design`
D1 ("the column IS the card") says what it should be. So `.live-card` is flat —
transparent, borderless, unpadded — with `.live-card + .live-card` separated by
a `--group-line` rule, and the column supplies the panel and padding. Writing
today's double-bordered face and then rewriting it in `4` would have been two
changes to reach one ratified answer.

What is NOT adopted: the fixed 342px track, the horizontal columns row, the tab
strip, and D8's demotions. At N=1 the column fills its host. Those all need
something to sit beside, which is `4`.

`.live-card`'s `min-width` had to split from `.device-control`'s at the same
time: §3 computed `320px + 2 × --pad-panel` because the card carried its own
padding. It no longer does, so counting it would count the column's twice.

## D7: Control never follows the focus Seat

`followFocusSeat` is dropped from the column's picker, per D7 (Bob, 2026-07-31,
"never" at every N). `verify_control_tab.py` asserted the opposite behaviour;
under CLAUDE.md's supersession rule that assertion is superseded, not
authoritative, so it was inverted in place with a comment naming this ruling —
it now checks that selecting a Seat on the Seats tab leaves Control's target
alone, and that a chip click still aims it. The Seats → Control workflow returns
as an explicit "Open in Control" action, owned by `4`.

The `storage`-event listener in `target-picker.js` needed no same-document
replacement: it fires only for *other* documents, so sharing a document with
the Seats tab would have silenced it regardless.

## Remote gets its own target key

`bopos.target.control` stays with the Control tab; Remote persists under
`bopos.target.remote`. They were one key only because they were one document.
Per-host selection is already the component's ruling (`07`), and it is what lets
`4` give each column its own.

## Two host-difference notes

- `renderShowCapture`'s button read "Capture As Show Step" in the dashboard
  document, because `style.css` capitalizes every button and `facilitator.css`
  did not. Fixed on the component with `text-transform:none`.
- The event **fire** button reads "Fire" in the dashboard document for the same
  reason — but it already did on the Device tab, so the two panel hosts now
  agree rather than diverge. Left alone deliberately; if it is wrong it is wrong
  app-wide, which is `11-ground-and-card-audit`'s question.

## The Remote delta, measured

`remote_delta.py` (in this stitch) measures the live Remote page before and
after: 55 controls, 30 changed width only (page gutter 22px → 12px), and
**four** changed anything else — the card box, its head, its name, and
`Send all` (88 × 44 → 54 × 24, the one real tap target lost). Every parameter
row measured identical, for `05e`'s reason: `control-panel.css` §17b had
already restated their metrics for both hosts. Recorded in
`feature-backlog/49-remote-ipad-restyle`.
