# Reusable-component inventory — desktop UI unification (2026-07-30)

Stage A of the component-first program Bob set on 2026-07-30. This is a
**ledger, not a proposal**: what exists, how many divergent implementations of
each, who would consume a unified one, and how hard the lift is. Design calls
belong in the per-component stitches that follow.

Scope: `dashboard/static/` — 9.8k lines across `js/` (7 surfaces + 6 shared
modules), `css/style.css` (376 lines), `css/control-panel.css` (1624 lines),
`css/facilitator.css` (117 lines).

Authority for the target style: `.loom/tied/2-control-panel-design/` —
`design-language.md` (ratified v1), `control-panel-design.md`, and the living
prototype `mockup-control-panel.html`. Bob's original Excalidraw is the
north star; see `.lore/items/2026-07-27-control-panel-ui-and-architecture-braindump/`.

---

## 0. The headline finding: two disjoint token systems

> **RESOLVED 2026-07-30 by `02-token-promotion`.** There is one metric layer
> now. `--chrome-*` is deleted; its 83 consumers in `style.css` point at
> `--row-h` / `--gap` / `--radius-*` (plus `--pad-control`, `--pad-panel` and
> `--header-h`, declared beside them), so the app chrome runs at 24px controls
> and 6px rhythm — chrome above content went 118px → 73px. Off-hue
> `--feature`/`--feature-line` are retired with it, and the light ground is one
> `#f8f0fc`. Bob then ruled the held item in the same day, so the app-wide light
> panels are the mockup's **neutral** grey scale too — see the tied stitch's
> `decisions-2-neutral-light.md`. The section below is the as-found record.

The app has **two complete, non-overlapping design token layers**, and this is
the mechanical root of every complaint in Bob's brief.

| | `css/style.css` (app-wide) | `css/control-panel.css` (panel-scoped) |
|---|---|---|
| control height | `--chrome-control-height: 32px` | `--row-h: 24px` |
| gap / rhythm | `--chrome-gap: 12px` | `--gap: 6px` |
| panel padding | `--chrome-panel-pad: 12px` | (drawer indent 12px; rows padless) |
| control padding | `--chrome-control-pad: 4px 8px` | value box 58px fixed |
| radii | `--chrome-radius-panel/control/small` | `--radius-panel/control/small` + `--radius-momentary: 7px` / `--radius-toggle: 1px` |
| light `--bg` | `#f4f1f8` (lavender) | `#f4d7eb` (pink pastel) |
| modulation ink | — | `--mod`, `--mod-fill`, `--mod-hatch`, `--mod-soft` |
| button semantics | one flat button style | momentary = round, latching = square (PD heritage) |

Usage is cleanly separated and **zero files use both**:

```
--chrome-* :  style.css  10 hits,  control-panel.css 0
--row-h/--gap : control-panel.css 30 hits, style.css 0
```

`control-panel.css` binds its tokens under exactly two selectors — `.live-card`
and `.device-control` — which was the correct scope discipline for
`01-control-panel` (the file says so in its header) and is now precisely the
thing to widen. The rollout is not "invent a design system"; it is **promote
`--cp-*` to `:root` and retire `--chrome-*`**, surface by surface.

**The light-theme row is already resolved (2026-07-30) — see §4.4.** Neither
of the two values in the table survived: Bob ruled the pink is a *ground*, not
a panel colour, and the light scheme is now a neutral grey scale (`#f8f9fa`
panels, `#e9ecef` subpanels, `#ffffff` inputs) on a pale pink ground
(`#f8f0fc`), sampled from the mockup. Both stylesheets carry that ground now,
and since Bob's same-day ruling both carry the neutral panel scale too, so light
is no longer a source of divergence — and neither are the metrics.

---

## 1. Component ledger, ranked

Rank = (number of surfaces that would consume it) × (how far the current
implementations have drifted). Effort is a rough T-shirt.

### Rank 1 — Control panel (`ControlSurface`)

**Status:** exists, shared, ratified. `js/control-surface.js` (1151 lines),
3 consumers via `ControlSurface.create()`.

| consumer | file | uses shared panel? |
|---|---|---|
| standalone facilitator + Control-tab iframe | `facilitator.js:18` | yes |
| Devices tab control panel | `dashboard.js:1376` | yes |
| Patches tab — patch editor | `dashboard.js:1365` | **preset row only** |
| Show tab — inspector | — | **no** |

Two gaps, both named by Bob:

1. **Patch editor runs its own parameter tree.** `dashboard.js:898-927`
   (`editorControl` / `editorParamTree`) hand-rolls `<label><span>name</span>
   <output><input type=range>` rows, a `.toggle` checkbox variant, and a text
   variant — with its own hierarchy accordion. The code comment at
   `dashboard.js:1362` is honest about why: *"The patch editor keeps its own
   parameter tree (it drives one audition engine and predates the shared
   surface), but its PRESET row is the shared, ratified one."* This is the
   clearest instance of Bob's "anywhere there is a control for a patch should
   present the same control panel". No generator drawer, no mixed-state
   encoding, no marker line, no event rows.
2. **Show inspector has no control panel at all** — see rank 3.

**Reflow defects** (Bob's brief, confirmed in `control-panel.css`): parameter
rows must stay atomic — `[value 58px][name-in-slider flex][∿ 18px]` never
wraps — and the generator drawer must not reflow, which makes the drawer's
fixed width the panel's `min-width`. `design-language.md` §7 already says
"the row may wrap before boxes shrink"; that sentence is the bug.

**Effort:** M (editor integration) + S (reflow rules).

---

### Rank 2 — Target selector

**Status:** two unrelated implementations, neither adequate for what Bob wants.

| implementation | file | model | selection |
|---|---|---|---|
| `SeatFilter` | `js/seat-filter.js` (117 lines) | All / Groups / Seat radio tabs + a seat `<select>` | **single**, mode-exclusive |
| Show target picker | `js/show.js:287` (`renderTargetPicker`) | `<details>` disclosure, chip grid: All + group chips + seat-number chips + a removable summary row | **multi-select, mixed** |

`SeatFilter` is documented as "deliberately not a widget belonging to the
Control tab" but has exactly **one** real consumer (`facilitator.js:90`);
`dashboard.js:1136` only calls its `selectSeat` storage helper. The Show
picker is the one that actually does what Bob describes — a mixture of all,
groups, and seats — and it is welded into `show.js`.

The unified component is closer to the Show picker (multi-select, pop-out
disclosure, terse summary when closed) than to `SeatFilter`. Consumers:
Show inspector, Control-tab columns (rank 6), Devices, Patches deployment row.

**The device/seat split is real.** Bob's instinct is right and the tied entity
architecture review backs it: seats/groups are the *site* layer, physical
devices are the *hardware* layer. `#patch-target` (`index.html:83`) and
`#asset-target` (`index.html:130`) select **devices**; every other target
selector selects **seats/groups**. One component, two domains — same chrome,
different roster source and different wire selector — is the shape to design
toward.

**Effort:** M. This is the second component precisely because rank 6 depends
on it.

---

### Rank 3 — Generator / modulation drawer

**Status:** fields are already shared; the **chrome is not**.

`js/param-generator.js` (369 lines) exports `fields()`, `preview()`,
`segmentRow()`, `unitOptions()`. Both hosts call it:

- `control-surface.js:231` `generatorDrawer()` — wraps the fields in the
  ratified drawer: LFO/loop/fade latching tabs, `--subpanel` face, 12px
  indent, pointer up to the ∿ icon, cyan active tab.
- `show.js:786-789` — wraps the *same fields* in a bare
  `<label>generator <select>` stack inside `.show-inspector-section`, with a
  plain `<option>` list for value/fade/loop/lfo/stop.

So the Show inspector already renders the identical generator *fields* in
non-conforming chrome. Lifting `generatorDrawer()` out of `control-surface.js`
into `param-generator.js` (or a sibling) makes the Show inspector match the
mockup essentially for free. Bob's observation that the inspector is a narrow
column is exactly right: the drawer's fixed width is the inspector's width.

**Effort:** S–M. Highest value-per-line in the whole ledger.

---

### Rank 4 — Numeric entry (value box)

**Status:** shared helper exists, thinly adopted.

`js/precision-field.js` (88 lines, `PrecisionField.attach`) — click-to-type,
clamps to min/max, rounds to 6 significant figures (the PD 32-bit float house
rule). **Three call sites total:** `control-surface.js:945`,
`dashboard.js:1040`, `dashboard.js:1060`.

Against that, raw `type="number"` inputs, none of them precision fields:

```
index.html            9
control-surface.js    1
dashboard.js          9
param-generator.js   16
show.js              12
```

The 16 in `param-generator.js` are the drawer arg boxes (`min`/`max`/`period`,
segment `to`/`in`) — the mockup shows these as the standard 58px value box, and
`design-language.md` §4 names 58px as "**the** standard number-box width —
every numeric entry box … unless a box must hold visibly longer values". The
12 in `show.js` are inspector fields. Neither set is styled as a value box and
neither gets click-to-type semantics beyond what the browser gives.

This is the single most repeated primitive in the app and the one where a
consistent style buys the most.

**Effort:** M (many call sites, each trivial).

---

### Rank 5 — Page chrome: heading blocks, section heads, toolbars

**Status:** consistent *with itself*, inconsistent with the design language,
and carrying dead text.

- `.eyebrow` + `<h2>` heading blocks: 5 instances
  (`index.html:26,82,128`, `show.js:455,487`). Bob has explicitly killed two
  of them — "Live control / Control" (`index.html:26`) and "Single-device
  delivery / Assets" (`index.html:128`) — as text that isn't doing anything
  when the tab bar already says where you are.
- `.section-head`: 29 instances (10 `index.html`, 10 `dashboard.js`, 9 CSS
  rules). A genuine shared pattern, just built on `--chrome-*` metrics.
- Footer/action toolbars: `index.html:76` (`Forget offline unbound`,
  `Reboot All`, `Shutdown All`, `Update bopOS`), `#editor-session-actions`,
  `.fleet-patch-actions`, `.mode-actions`. All full-text 32px buttons. These
  are the "big high padding bloated buttons" — the desktop language wants
  icon buttons with tooltips in a toolbar strip.
- Disclosure: 8 `<details>` across 5 files, no shared styling.
- Status/empty text: 52 `class="dim"`, 5 `class="empty"`.
- Badges/pills/chips: ~12 unrelated class families (`badge`, `patch-badge`,
  `device-binding-badge`, `group-legend-chip`, `show-message-pill`,
  `show-target-chip`, `live-gen-pill`). The Show message pills are ratified
  (`25-message-pill-encoding`) and stay; the rest are ad hoc.

**Effort:** S per item, L in aggregate. Best split into a "chrome
reclamation" stitch (the deletions and the tab-bar move, which are cheap and
immediately visible) and a "controls repaint" stitch.

---

### Rank 6 — Control-tab column workspace *(new surface, not an extraction)*

Today: `index.html:25-28` is a heading, a link, and **one iframe**
(`#dashboard-live-view` → `/facilitator?embedded=1`), with `SeatFilter`'s
All/Groups/Seat radios living inside the iframe.

Bob wants N columns, each a control panel with its own pop-out target
selector, add/remove, minimum one. Consequences worth naming now:

- It retires `SeatFilter`'s mode-exclusive model in favour of the unified
  multi-select picker (rank 2) — hence the ordering.
- **The iframe is the obstacle.** `control-panel.css`'s header calls out that
  the Control tab is a separate document and `localStorage` is the only
  channel the two share (CLAUDE.md Playwright gotcha 15 exists because of
  this). N columns in one tab is a strong argument for hosting
  `ControlSurface` directly in the parent document and keeping
  `/facilitator` standalone-only. That is a real architectural call, not a
  layout tweak, and it should be made explicitly in the stitch.
- Column layout needs a persistence home (localStorage, consistent with
  `bopos.control.collapsed-branches` and `bopos.device-control-open`; or
  server-side if it should survive a machine change).
- Interaction with the applied-preset marker per column is undefined.

**Effort:** L. The biggest single item, and the one most worth designing
before building.

---

### Rank 7 — Patches-tab fleet deployment row

`index.html:83`: `.fleet-patch-deploy` stacks `.fleet-patch-choice`
(patch `<select>` above target `<select>`) over `.fleet-patch-actions`
(`Deploy as fleet patch`, `Revert`). Bob wants patch, target, and buttons on
one line.

Blocked on rank 2's **device**-domain picker. Small once that exists.

**Effort:** S (after rank 2).

---

### Rank 8 — Tab bar

`index.html:16-23`, six left-aligned tabs. Bob wants the standalone-view link
moved here, right-aligned, replacing the `Open standalone dashboard` anchor at
`index.html:26`.

Naming: `Live` is my recommendation — short, right-aligns cleanly, reads as
"the running-show surface", no collision with Control or Show. Alternatives:
`Stage`, `Remote`, `Panel`. **Bob's call.**

Note the tab bar must keep `role="tablist"` semantics for the six real tabs;
the standalone link is an `<a>` that opens a different document, so it sits
*beside* the tablist, not inside it, or screen readers will announce a tab
that isn't one.

**Effort:** S.

---

## 2. Not in scope, deliberately

- **Standalone facilitator / iPad view** keeps its tablet-first constraints.
  `control-panel.css:90` already handles this correctly with
  `@media (pointer:coarse) { --row-h: 34px }` — same row grammar, bigger
  target. That is the model for "style mobile differently where needed": a
  metric override, not a parallel layout.
- **Show message pills** — ratified in `25-message-pill-encoding` with a
  deliberate eight-colour semantic set. They are the one legitimate
  exception to the grayscale-plus-two-hues rule and should not be repainted.
- **Status colours** (green/amber/red) — reserved for connectivity, warnings,
  errors per `design-language.md` §11. Never controls.
- **Spatial map** (`spatial.js`, 774 lines) — its own visual domain; touched
  only for token colours.

## 3. Sequence implied by the ledger

Dependencies, not preferences:

```
rank 3 (generator drawer)  ─┐
rank 4 (value box)         ─┼─→ rank 1 (editor integration)
                            │
rank 2 (target selector) ───┼─→ rank 6 (control columns)
                            └─→ rank 7 (patches deploy row)

rank 5 + 8 (chrome) — independent, cheap, do early for visible progress
rank 0 (token promotion) — underlies everything; do it first, scoped
```

## 4. Open questions — ALL ANSWERED by Bob, 2026-07-30

1. **Standalone-view tab name → `Remote`**, right-aligned in the tab bar. The
   manifest tab's `dashboard` checkboxes are renamed to match (the flag is
   unchanged; only the label). Shipped.
2. **The Control-tab iframe → RETIRE IT.** `ControlSurface` hosts directly in
   the parent document; `/facilitator` stays as the standalone Remote view.
   Rank 6 owns the change; CLAUDE.md Playwright gotcha 15 should be deleted
   once it stops being true.
3. **Column layout → `localStorage`**, alongside
   `bopos.control.collapsed-branches` and `bopos.device-control-open`. Bob:
   *"with a chip picker it should be easy to spin up whatever control panel
   targets one needs."*
4. **Light theme → app-wide, but the pink is a GROUND, not a panel colour.**
   Bob corrected the shipped panel against the mockup. Sampled from
   `mockup.png`: ground `#f8f0fc`, panel `#f8f9fa`, subpanel and manual fill
   `#e9ecef`, inputs/buttons `#ffffff`, ink `#212529`. A neutral grey scale on
   a pale pink ground — `--cp-bg` is the only pink token. **Shipped
   2026-07-30**, ahead of rank 0, so `02-token-promotion` is now density and
   `--chrome-*` retirement only — **both of which then shipped the same day**,
   including the missed `:root[data-theme="light"]` ground (the toggle had kept
   the old lavender while the OS preference got the pink).

   **Light is DONE app-wide (2026-07-30).** Bob saw the before/after pair and
   ruled *"I'd like to try the grey neutrals on the panels"*, so `style.css`
   and `facilitator.css` light columns now carry the mockup's neutral scale
   (panel `#f8f9fa`, subpanel/recessed `#e9ecef`, inputs `#ffffff`, hover
   `#f1f3f5`, lines `#ced4da`/`#495057`, ink `#212529`), `--bg` still the only
   pink. `--dim` is `#6c757d` app-wide for contrast, against the panel's
   ratified `#868e96`.

   **The cyan delta is CLOSED.** It was my note, not Bob's ask; he ruled
   *"I don't want to change the highlights. Leave `--mod-fill` as it is for
   now."* Do not re-raise it.
