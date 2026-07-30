# Expert consult — the calm-ops / IA / accessibility lens

Outside review of the N-column Control tab for `08-control-tab-columns/1`.
Everything asserted about behaviour was read off `main` at 2026-07-31 and is
cited. Where I am giving professional judgment rather than reporting code, I
say so.

---

## 0. The rule I am judging against

One rule governs almost everything below, so I will state it once:

> **Duplication that forces a choice is noise. Duplication that forces no
> choice is reach.**

Three columns each showing a `gain` slider is fine — the operator already knows
which target each column drives, and the sliders are not alternatives to one
another. Three columns each carrying a **Capture as Show step** button is not
fine, because the operator must now decide *which one to press*, and — as §1
shows — the decision is close to meaningless. That is the difference between an
instrument with three faders and a dialog with three OK buttons.

The corollary is the count discipline: every affordance added to a column is
added N times. The mockup was costed against one panel. Nothing in the shipped
card was costed against three.

---

## 1. The primary question: who owns capture-as-step

### Answer: neither. Capture is a venue-wide document command, and its home is the Show tab's edit bar.

Not per column. Not "the whole tab's arrangement" either — because *"the whole
tab's arrangement"* is not a thing the code has, and pretending it is would
invent state that does not exist. Let me take the two candidate answers apart in
order.

### 1.1 Per column is not merely redundant — it is currently a lie

`presetScope()` (`facilitator.js:381-397`) reduces a picker selection to three
coarse values, and `_capture_show_seats` (`server.py:1804-1812`) turns each into
a seat set. Line them up:

| column target | `presetScope()` sends | seats the server captures |
|---|---|---|
| `all` | `{scope:"all"}` | every seat |
| one seat, `7` | `{scope:"seat", id:7}` | seat 7 |
| seats `1`,`2` | `{scope:"all"}` (line 395) | **every seat in the venue** |
| group `Left` | `{scope:"groups"}` (line 396) | **every seat in any group** |
| `Left` + seat `9` | `{scope:"groups"}` | every grouped seat; **seat 9 dropped if ungrouped** |

Read row 4 again. A column whose sticky header says **Left** has a button whose
effect is *every grouped seat in the venue, including Right*. Row 3 is worse: a
column headed `1+2` captures the whole venue. Row 5 loses a target the operator
explicitly selected.

So the "easiest" option is not the safe one. A per-column capture button is a
control whose label (its column's target) contradicts its behaviour in the two
most likely column configurations — groups, and small seat mixtures. Multiply by
N and you have three buttons, all mislabelled, all producing nearly the same
step, differing only in a filter that mostly does not filter.

Making per-column capture *honest* would require sending an explicit seat-id
list — i.e. **widening** the server vocabulary. The instructions warned about
widening as the cost of the whole-tab answer; it is in fact the cost of the
per-column answer. The ground truth has this right (§5b, §6.1) and I confirm it
independently.

### 1.2 "Whole-tab arrangement" is a phantom

`_captured_show_preset_messages` (`server.py:1838-1880`) never looks at a
picker, a column, or a selection. It groups seats by their `applied_preset`
marker and asks `preset_application.capture_target` (`preset_application.py:246-261`)
for the most portable selector shape per group of seats — `all`, else
`group:<name>`, else an explicit id list.

The arrangement therefore lives **on the seats**, not on the screen. A capture
at `scope:"all"` already emits the full multi-message step. There is no
information in "the arrangement across all columns" that a venue-wide capture
does not already have, and there is information in the seats that no column
arrangement can express (a seat carrying a preset that no open column happens to
show). A whole-tab capture is not a richer capture — it is the same capture with
a decorative justification.

Which means the honest framing of the choice is not *one column vs. all
columns*. It is: **capture is venue-wide; the only real question is where the
button lives.**

### 1.3 Where it should live: the Show tab's edit bar

`renderEditBar()` (`show.js:512-525`) is already a `role="toolbar"` containing
`✛ Step` and `╱ Divider`. Capture is a third way to make a step. It belongs
there as `✛ Capture`, in the same glyph family, in the same group as `✛ Step`.

Five reasons, in descending strength:

1. **The result is only visible there.** Today the operator clicks capture on
   Control, answers a `confirm()`, and *nothing happens on screen*.
   `capture_show_preset_step` → `apply_show_mutation` (`server.py:1428-1453`)
   persists and broadcasts `show`; `facilitator.js` registers no `show` handler
   (its full handler list is lines 212-270). A document mutation with two
   possible `alert()`s, one `confirm()`, and zero success feedback is the
   textbook calm-ops failure, and it is shipping right now. On the Show tab the
   new step simply appears in the list. Placement solves the feedback problem for
   free — no toast, no new indicator, no new control.
2. **The step needs naming, immediately.** `capture_preset_step`'s alias
   defaults to `"Captured presets"` (`show_model.py:859`) and the server never
   overrides it (`server.py:1888-1889`). Capture three arrangements in a session
   and the Show tab holds three identically named rows appended at the end. The
   Show tab already has click-to-edit step names; capturing there means the new
   step can be selected and renamed in the same gesture. Capturing from Control
   means going to the Show tab later and guessing which identical row is new.
3. **Insertion position is a document decision.** Capture always appends
   (`show_model.py:882`, `items + [step]`), while `✛ Step` inserts after the
   selection (`show.js:1472`, `addItem("step", insertionAfterUid())`). An
   operator building a show wants the captured step *where they are working*.
   That only has meaning on a surface where a selection exists.
4. **It removes N buttons from Control** and adds one to a toolbar that already
   holds four. Net affordance change on the busy surface: −N.
5. **It matches what the command is.** Control is the live surface; Show is the
   document. Capture writes to the document. Putting the write on the live
   surface is why it currently has no visible result.

### 1.4 If Bob wants the one-click path from Control anyway

He may — the "I have the arrangement in my hands right now" argument is real and
I expect the live-operator lens to press it. My concession, and its exact shape:

- **Exactly one button**, in a Control-tab toolbar row, not in any column.
- It sends **no scope at all**. Delete the `scope`/`id` arguments from
  `preview_show_preset_capture` and `capture_show_preset_step`. Per §1.1 the
  only non-inert value is `seat`, and per §1.2 nothing on Control should be
  narrowing a venue-wide fact. This is a *removal*, not a widening.
- It is the **same command with the same words** as the Show-tab entry —
  `✛ Capture`. Two entry points, one unparameterised meaning, no choice to make:
  reach, not noise (§0).
- It replaces the `confirm()` with the panel's own idiom. The preset apply report
  is explicitly *"one compact line with a disclosure — never a modal"*
  (`control-surface.js:289-290`, ratified in `41/07`). Capture should obey the
  same ruling: the button shows its own preview inline — `capture · 4 of 9
  targets` — and a second click commits. Arm-then-fire, no dialog, and the count
  that the `confirm()` string currently carries becomes ambient instead of
  blocking.
- It gains a success line in the same slot: `captured → "Captured presets"`.

The two `alert()`s (`facilitator.js:252`, `:256`) become the same inline line
(`no show loaded`, `nothing applied to capture`) with the button disabled. An
`alert()` on a surface an operator may be driving mid-show is indefensible at
N=1 and worse at N=3.

### 1.5 One live defect in the current button, which N multiplies

`render()` calls `targetPicker.render()` then `renderShowCapture()` on **every**
heartbeat (`facilitator.js:284-289`), unguarded by `interacting` (the guard
exists only inside `renderCards`, line 332). `targetPicker.render()` replaces
`host.innerHTML` wholesale (`target-picker.js:322`), so the capture button is
destroyed and rebuilt, and its `onclick` reassigned, several times a second
(`facilitator.js:294-296`). A pointerdown/pointerup that straddles a re-render
lands on a node that no longer exists. This is CLAUDE.md gotcha 16 in production
rather than in a test. It should be fixed by delegation (one listener on a
stable ancestor) whatever the placement ruling is — and note that N columns give
this failure N chances to bite.

---

## 2. Column widths, the 1400px cap, add/remove

### 2.1 Fixed floor, no resize handles

`control-panel.css:145-149` sets `min-width:calc(320px + 2 * var(--pad-panel))`
= 340px with the ratified reasoning that the drawer is *"an instrument face, not
a responsive form"*. A column is that face plus its gutter.

**Position: columns are a fixed track — `minmax(340px, 400px)` — never
resizable.** A resize handle is:

- a control that exists to solve a layout problem the design should not have;
- new persisted per-column state, in a layout object that already has enough;
- a *horizontal drag target sitting adjacent to a column full of horizontal
  drag targets*. The panel is sliders. A grab that misses the divider by 4px
  moves a parameter on live speakers. That alone settles it.

The 400px ceiling is judgment, not code: past roughly 400px the row grammar
(`design-language §5`, `[58px value][flexible slider][18px ∿]`) gives the slider
a length wildly out of proportion to the fixed elements, and a 12px monospace
parameter name floats in the middle of an empty trough. The panel was designed
narrow; letting it sprawl because there is screen left is how the "swimming in
empty space" complaint (§12) got made in the first place.

### 2.2 The 1400px cap: drop it on this tab, and left-align

`.tab-panel{max-width:1400px;margin:0 auto}` (`style.css:44`). Two rulings:

**Drop the cap for `.dashboard-tab`.** With a fixed floor and no reflow, the cap
does not protect anything — it only decides how many columns are reachable
without scrolling:

| viewport | usable (−32px pad) | columns at 340 + 16 gutter, capped | uncapped |
|---|---|---|---|
| 1280 | 1248 | 3 | 3 |
| 1680 | 1368 | 3 | **4** |
| 2560 | 1368 | 3 | **7** |

The cap exists for reading-measure surfaces. A rack of instrument faces has no
measure to protect.

**Left-align the column row; do not centre it.** This is the more important half
and I hold it strongly. `margin:0 auto` means that adding a fourth column *moves
columns one through three sideways*. Every control the operator has built muscle
memory for changes position because they added an unrelated column. Positional
stability across an add/remove is an operating requirement; centring is an
aesthetic. Left-aligned, adding column 4 moves nothing.

### 2.3 Overflow: scroll intact, never reflow, never auto-collapse

When N columns do not fit, the tab scrolls horizontally with
`scroll-snap-type:x proximity` snapping to column starts. This is not my
invention — it is `06`'s ratified rule applied one level up: *"a narrower
viewport scrolls the intact panel instead of rearranging the drawer"*
(`control-panel.css:145-149`, `design-language §7`). Auto-collapsing overflow
columns into rails would move the operator's instruments without being asked,
which is worse than a scrollbar.

Consequence that must ship with it: **each column scrolls its own body
independently, and its header is sticky.** Today one `main{flex:1;overflow-y:auto}`
scrolls the whole card list (`facilitator.css:27`). If that survives into
columns, a long column drags the short ones off-screen. And a column whose target
label has scrolled out of view is a mis-target waiting to happen — with three
columns of near-identical rows, the target label is the *only* thing telling you
which speakers you are about to move. Sticky header, non-negotiable.

### 2.4 The picker defaults CLOSED in a column

`TargetPicker.create` defaults `defaultOpen = true` (`target-picker.js:239`) and
Control does not override it (`facilitator.js:101-112`). An open picker costs an
All chip row, a group chip row, and a 132px scrolling seat roster
(`target-picker.css`, `.target-picker-roster{max-height:132px}`) — call it 180px
of a 340px-wide column, spent on a control that is set once and then not touched
again, times N.

**Position: a Control column passes `defaultOpen: false`.** The closed
disclosure's terse output (`target-picker.js:206`, producing `all` or `Left+7`)
becomes the column's title and its sticky header in one element. This is the
single largest signal-to-noise win available in the whole design and it is one
argument.

It does not contradict `07`'s comment (*"a host whose whole job is choosing a
target opens by default"*): a column's whole job is driving parameters, not
choosing a target. The operator's own collapse still persists either way.

### 2.5 Add and remove

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌╌╌┐
│ ▸ Target   all ✕ │ │ ▸ Target  Left ✕ │ │ ▸ Target     7 ✕ │ ┆  ┆
├──────────────────┤ ├──────────────────┤ ├──────────────────┤ ┆  ┆
│ dusk *      [∨]  │ │ bloom       [∨]  │ │ — none —    [∨]  │ ┆+ ┆
│ ┌──┐             │ │ ┌──┐             │ │ ┌──┐             │ ┆  ┆
│ │.72│ gain    ∿  │ │ │.40│ gain    ∿  │ │ │.61│ gain    ∿  │ ┆  ┆
│ └──┘             │ │ └──┘             │ │ └──┘             │ ┆  ┆
│ ...              │ │ ...              │ │ ...              │ ┆  ┆
└──────────────────┘ └──────────────────┘ └──────────────────┘ └╌╌┘
        ↑ ground shows only in these gutters (§12)              ↑ ghost rail
```

**Remove** is a `✕` icon button at the right of the column header — the icon
treatment `03-chrome-reclamation` already established. At N=1 it is
`visibility:hidden`, not removed and not `disabled`: it holds its space so the
header does not reflow when the second column appears, and it is not a dead
control sitting there inviting a click.

**Add** is a **ghost rail** — a ~28px full-height dashed card after the last
column with a centred `+`. Not a toolbar button, because a single button in an
otherwise empty toolbar row would be a control painted directly on ground, which
§12 forecloses; and not a per-column `+`, because that is N affordances for one
command (§0). The rail also *is* the width feedback: if it has been scrolled off,
you can see the row is full. Judgment, not code.

---

## 3. A column that resolves to no seats

Two cases that behave very differently, and one of them is a safety bug.

### 3.1 Deleted seat — today the column silently becomes an All column

`prune()` (`target-picker.js:271-287`) drops selectors with no chip, and if
nothing survives **and `allowAll` is true, it returns `["all"]`** (line 283).
`resolve()` then persists that (lines 305-308).

So a column targeting Seat 7 silently widens to *every seat* the moment Seat 7 is
deleted or renumbered. At N=1 that is a mild surprise. With three columns open,
one of which the operator is not currently looking at, the next slider drag in
that column hits the whole venue. Broadening a target without being asked is the
one direction a live control surface must never fail in.

**Position: a Control column's pruning fallback is empty, not `all`.** The
column keeps its dead selector and renders an explicit unresolved state:

```
┌──────────────────┐
│ ▸ Target     7 ✕ │
├──────────────────┤
│ Seat 7 is no     │
│ longer in this   │
│ venue.           │
│  [ re-target ]   │
└──────────────────┘
```

No controls rendered — not disabled controls, *no* controls, because there is
nothing they could act on. An empty column is safe; an All column is not.

This needs a component change: `prune` today reaches `[]` only via
`built.allowAll === false` (lines 283-287), which would also remove the All chip
from the picker. The component needs to separate "All is offerable" from "All is
the fallback" — e.g. `pruneFallback: "empty"`. Small, and `07` is the right
owner of the shape.

### 3.2 Empty group — keep the column, disable the controls, say why

A group with no members is a normal transient authoring state. `liveCard` already
passes `empty` into `surface.tree(...)` (`facilitator.js:189`) so the rows render
disabled, and the meta line already reads `g3 · 0 Seats` (line 187). That is
right; preserve it.

One accessibility fix: `.empty-group{opacity:.72}` (`facilitator.css:30`) is a
purely visual channel. The meta text carries the fact, so this is reinforcement
rather than the sole signal — but the region should also carry `aria-disabled` so
the state is announced, not inferred from a count buried in a `<small>`.

---

## 4. Two columns showing the same seat

**Position: overlap is legitimate, must not be prevented, and needs no new
signalling.**

The ground truth is right that this is perceptual only: provenance is derived
per seat at render (`control-surface.js:275-287`; dirtiness derived, never
stored — `preset_application.py:264`). Two columns reading seat 3 cannot
disagree. An All column plus a Seat-7 column is the canonical *context + detail*
pair and is one of the best reasons to have columns at all.

What I would *not* do: cross-column linking, flashes, or "this seat is also
shown in column 2" markers. Three columns twitching in sympathy every time the
operator moves something is precisely the anti-calm outcome. The propagation is
a change the operator caused, arriving on the next heartbeat, in a place they
can see. That is enough.

One thing already correct and worth protecting: the apply report renders on a row
only when the report's targets *exactly* match the row's members
(`facilitator.js:73-79`). So an apply from a Seat-3 column does not also print a
report inside the All column. Keep that predicate; do not loosen it to
"overlaps".

The genuine overlap hazard is elsewhere, and it is not about presets being shown
twice — it is about **`del` being shown twice**; see §6.2.

---

## 5. `followFocusSeat` with N columns

**Position: none of them. Retire `followFocusSeat` on Control and replace it
with an explicit verb.**

`facilitator.js:104` sets `followFocusSeat: true`; `adoptFocusSeat`
(`target-picker.js:289-299`) *replaces* the selection with `[String(seat)]` and
persists it.

- **Move every column** — destroys the arrangement the operator deliberately
  built, and destroys it *persistently*, because `adoptFocusSeat` calls
  `persist()`. One click on an unrelated tab wipes the layout. Unacceptable.
- **Move one column** — requires a notion of "the active column": new invisible
  persistent state, and any rule for choosing it (first / last-touched /
  most-recently-focused) is unguessable from the screen. An operator cannot
  predict where their click will land, which makes the feature worse than
  nothing.
- **Move none** — costs one click and is completely predictable.

The workflow being preserved (Seats → Control lands on the same seat, from
`37/10`) is better served by an explicit action in the Seats inspector:
**"Open in Control"**, which adds — or reuses — a column targeting that seat and
switches tabs. Deliberate, visible, non-destructive, and it does the tab switch
too, which the ambient version never did.

There is no plumbing argument for keeping the ambient behaviour: today the
adoption arrives as a cross-document `storage` event (`target-picker.js:365-367`),
and `storage` does not fire in the writing document, so `3-iframe-retirement`
must rewrite the delivery regardless (ground truth §2). Both options cost new
code; only one of them is unambiguous.

**Acceptable fallback if Bob wants the old feel:** follow applies **only when
N == 1**. That is a rule, not a control; single-column operators get today's
behaviour byte for byte, and the ambiguity never arises because there is nothing
to be ambiguous between. I would still ship "Open in Control" alongside it.

`bopos.selected-seat` stays as the Seats tab's own selection key
(`target-picker.js:28`); Control simply stops reading it.

---

## 6. Duplicated-identity hazards — specific collisions in the current source

CLAUDE.md gotchas 12 and 17 are the same failure twice: an identifier that
stopped being unique the moment a thing rendered more than once. N columns render
*everything* more than once. Here is what breaks, by kind.

### 6.1 Hard `id` collisions

| id | source | with N columns |
|---|---|---|
| `target-picker-host` | `facilitator.html:23` | N hosts; must become a class |
| `cards` | `facilitator.html:24` | N card lists |
| `event-status` | `facilitator.html:22` | one live region for N columns' preset-save and event-schedule messages (`facilitator.js:240`, `:269`) — unattributed |
| `venue-name`, `ws-status` | `facilitator.html:21` | column chrome that should not be per column at all |
| `master`, `master-out`, `silence` | `facilitator.html:26-28` | **already collide with `index.html:11,14`** the moment `facilitator.js` runs in the parent document |

The last row is `3-iframe-retirement`'s problem, but it is the same disease and
it lands first. Rule for `4`: **no `id` attribute anywhere inside a column.** A
browser-free source guard can assert this — `05d` set the precedent for exactly
this kind of check (`tests/test_css_component_ownership.py`).

### 6.2 `data-` attribute collisions

- **`data-preset-key` lookup is document-wide.** `bindPresets` does
  `root.querySelector('[data-preset-key="…"]')` (`control-surface.js:443`) with
  `key = scope:id` (line 269). Two columns both targeting Seat 3 produce two
  `seat:3` rows; the second column's save drawer binds to the *first* column's
  row and reads its `scope`/`id`. Latent while the values match, live the moment
  key derivation changes. Fix: `bind()` must be given the column root, and
  `facilitator.js:356`'s `surface.bind(document)` must become
  `surface.bind(columnEl)`.
- **`data-target-picker="control"`** (`target-picker.js:205`, id from
  `facilitator.js:103`) becomes N identical values. Nothing in the component
  queries it globally today — the `toggle` listener uses `closest` scoped to the
  host (line 358) — but it is precisely what a test or a later feature will
  query, and that is gotcha 17 pre-loaded. Give each column a minted picker id
  (`control-c3`), and guard uniqueness.
- **`data-live-scope`/`data-live-id`** on cards, rows, event rows and drawers
  (`control-surface.js:245-246, 513, 532`; `facilitator.js:206`) are target
  identifiers, not element identifiers. They are *correctly* non-unique. Any new
  selector must be `columnRoot` + these, never these alone. This is the
  successor to gotcha 12 and should be written into CLAUDE.md as **gotcha 19**
  when `4` lands.

### 6.3 Per-instance state that is not per-column, and vice versa

`ControlSurface.create` holds `openDrawers`, `drafts` (lines 56-57),
`openSaveDrawers`, `saveExclusions` (lines 266-267) — all keyed by `scope:id`.
Two consequences:

- **One surface instance shared by N columns is wrong**: opening the generator
  drawer for `seat:3` in column A opens it in column B, because the key is the
  target, not the column. So: one instance per column.
- **But one instance per column breaks the fade animator**, which is
  document-wide: `document.querySelectorAll('[data-fade-anchor][data-automated="true"]')`
  at `control-surface.js:764`, `:788`, `:792`. N instances each start a rAF loop
  that walks *every* column's anchors and writes their readouts — N loops doing
  N× the work and racing each other's `output.value` writes. Either scope those
  three queries to the bound root, or hoist the animator to a module singleton.
  Whichever, it must be decided in `2-control-column-component`, not discovered
  in `4`.

`bopos.control.collapsed-branches` (`control-surface.js:29`) should stay
**global across columns**. Its own comment says the operator is pruning the
manifest, not a card; that reasoning holds a fortiori across columns. Do not
per-column it — that is state added for symmetry rather than for need.

### 6.4 localStorage shape

**Position: one key for the whole layout, not N picker keys.**

```
bopos.control.columns = [
  {"id":"c1","target":["all"],"open":false},
  {"id":"c2","target":["g3"],"open":false},
  {"id":"c4","target":["7"],"open":true}
]
```

Why not `bopos.target.control.<index>`: remove the middle column of three and
every subsequent column's stored selection shifts by one — the exact class of
bug that N-of-everything produces. Order also cannot be expressed by N
independent keys, and reconciling "which keys exist" against "which columns
exist" on every add/remove is bookkeeping nobody will keep correct.

Column identity is a **minted id, never an index** — indices renumber on remove
and would silently re-point both storage and every `aria-labelledby` reference at
the wrong column.

This fits the component as shipped: `storageKey` is optional
(`target-picker.js:255, 262-264` both no-op without it), so the column owns
persistence and drives the picker through `set()` (line 373) and `onChange`.
Retire `bopos.target.control` and `bopos.target.control.open` with a one-time
read-and-migrate so an existing operator's target becomes column 1.

### 6.5 ARIA, live regions, and keyboard order

- **Double announcement.** `liveCard` emits an `aria-live="polite"` output per
  card carrying `surface.announcement(cardKey)` (`facilitator.js:208`), and
  takeover messages are stored under `scope:id`
  (`control-surface.js:857-859`). Two columns showing Seat 3 both render the same
  message on the next re-render, so a screen-reader user hears it twice, from two
  regions, with no way to tell which column acted.
  **Position: one live region per column, not per card, and the message is
  prefixed with the column's target** — *"Left: gain automation stopped, set to
  0.4"*. Without attribution the announcement is unusable at N > 1.
- **Regions.** `<main id="cards" role="region" aria-label="Live controls">`
  (`facilitator.html:24`) becomes N. Make each column a
  `<section aria-labelledby="…">` pointing at its own header, so region
  navigation reads *"all", "Left", "Seat 7"* — which is the AT equivalent of the
  sticky header, and the reason a blind operator can work this tab at all. It
  needs a generated header id, hence §6.4's minted column id.
- **Keyboard order is already correct — do not "fix" it.** DOM order is
  column 1's rows, then column 2's. Tabbing from the bottom of column 1 to the
  top of column 2 looks like a jump but is the correct reading order for
  columns. **Never introduce positive `tabindex`.** The right mitigation is not
  reordering but *escape*: the region landmarks above, plus putting the column's
  picker and `✕` first in DOM within the column, so an operator can reach the
  next column's target without traversing forty parameter rows.
- One more, from the ratified palette: the picker's chips already carry
  `aria-pressed` (`target-picker.js:159`), which is what keys their square radius
  (`design-language §8`). A column's `✕` and the ghost rail's `+` are momentary,
  so they must **not** carry `aria-pressed` — otherwise they silently take the
  latching shape.

### 6.6 CSS ownership

If the column becomes a card (§7.1), the panel token binding at
`control-panel.css:122` (`.live-card, .device-control`) needs a third selector,
and a new `.control-column-*` prefix must be registered in
`tests/test_css_component_ownership.py`'s `COMPONENTS` map (line 39-46) — its own
header says *"a component whose classes cannot be told apart from its host's is
the very problem this guard exists to catch"*. Register it in `4`, not after.

Also for the sweep's benefit: `facilitator.css:71`'s
`main[data-live-view=aggregate] .all-card{grid-column:1/-1}` is **dead** —
`selectionMode` (`facilitator.js:324-329`) only ever returns
`all`/`groups`/`seats`/`mixed`. The only multi-column rule in the codebase today
has an inert span exception. Do not port it forward as if it were working prior
art.

---

## 7. The real risk the brief did not ask about

### 7.1 N columns multiply chrome, not content — and the chrome is already losing

Count the interactive elements in one Seat card as shipped, before a single
parameter row:

| element | source |
|---|---|
| `Send all` | `facilitator.js:168-170` |
| preset `<select>` | `control-surface.js:399` |
| `new` / `save` / `del` | `control-surface.js:389-394` |
| `Device setup` disclosure | `facilitator.js:177` |
| *(inside it)* Update bopOS / Reboot / Shutdown | `facilitator.js:175`, `:399` |

Six interactive elements of chrome per card, plus the column's own picker and
`✕`. A column holding a three-seat mixture renders three cards
(`facilitator.js:341`, `selection.map(selectedCard)`) — eighteen. Three such
columns: **fifty-four chrome controls before the operator reaches the thing they
came for.** Every one of them devalues every parameter row around it.

**This is the risk that decides whether the design succeeds.** If `4-n-columns`
ships the current card verbatim × 3, the Control tab gets *worse*, and the
mockup's calm will not have survived contact with multiplication. Three cuts,
in order of how strongly I hold them:

1. **Delete device commands from the Control column.** Update bopOS, Reboot and
   Shutdown, behind a hold-to-confirm, inside a live parameter panel, is a
   category error at N=1 — the Devices tab owns device lifecycle. At N=3 it is
   three copies of a destructive fleet action sitting one disclosure away from
   the faders. `07` already established the hand-off pattern ("Set patch…").
   Use it. *(Judgment. Nothing in the code requires them here.)*
2. **Demote `new`/`save`/`del` behind one disclosure, keep the `<select>`.**
   Applying a preset is the live act and belongs in the row. The other three are
   authoring. This also fixes a real IA lie: **`del` is patch-scoped, not
   target-scoped** — `deletePreset({patch, slug, revision})`
   (`control-surface.js:425`) removes the preset from the store for the whole
   installation, while sitting inside a row whose every other control acts on
   this column's target. It is `confirm()`-guarded (line 424), but the
   *placement* implies a locality it does not have, and N columns give you N
   copies of a store-mutating button each dressed as a local one.
3. **`Send all` moves to an overflow.** It is a rescue action for a returning
   node, not a live gesture, and it is rendered on every All and Seat card
   (`facilitator.js:207`).

### 7.2 The column is the card — the per-target boxes stop being cards

§12 says columns are cards on the ground, and the per-target sections cannot
*also* be cards without nesting panel-on-panel or letting ground show inside a
column's footprint — both of which §12 forbids ("If you can see ground *inside*
a card's footprint… it is wrong").

**Position: the column carries `--panel`; a mixed selection renders per-target
*sections* separated by a 1px `--line` rule, not by bordered boxes with their own
padding.** Concretely, `liveCard`'s `<article class="live-card">`
(`facilitator.js:206`) loses its border, radius and background inside a column
and keeps only its header line.

This is not only a §12 compliance move. At 340px, four bordered cards each with
`padding:18px 20px` (`facilitator.css:29`) spend roughly a quarter of the column
on borders and padding that carry no information the header line does not. It is
also the single change that makes cut §7.1 affordable.

### 7.3 Duplicate-target columns

Nothing prevents two columns from carrying the identical target. **Position:
allow it.** A rule preventing it costs more than the rare duplicate, and the
operator may well want two views of the same target at different scroll
positions. But it makes §6.2's `data-preset-key` collision real rather than
latent, and §6.5's double announcement real rather than theoretical — so both
must be fixed on their own merits, not deferred on the grounds that duplicates
are unlikely.

---

## 8. Where I expect to disagree with the other lenses

**With the live-operator/performance lens, on capture placement (§1).** I expect
"the operator is on Control when the arrangement exists; sending them to the Show
tab breaks flow." The flow argument is real and I have conceded to it in §1.4 —
but only as *one unparameterised button*. Where I will hold the line: a
per-column capture button is not a flow win, it is a decision the operator now
has to make three times a session about a filter that, per §1.1, silently
captures targets outside the column in the two commonest cases. Adding a choice
is not adding speed.

**With the live-operator lens, on `followFocusSeat` (§5).** I expect "I clicked
the seat, I want the panel on it." My counter: with N columns, ambient follow is
*destructive* — `adoptFocusSeat` overwrites and persists a selection
(`target-picker.js:294-297`). Destroying a persisted layout to save one click is
the wrong trade at any N > 1. The N==1 rule in §5 is where I will settle.

**With the show-authoring/document-semantics lens, probably in agreement, and I
want to reinforce one point they own.** A single-seat capture emits raw seat-id
selectors — `capture_target` returns `{"scope":"seats","ids":[…]}` when no group
matches exactly (`preset_application.py:261`), which `server.py:1865` renders as
`["3"]`. The ratified entity model says portable shows target groups **by name**.
So per-column capture from a Seat column is not merely mislabelled (§1.1), it
produces the *least* portable step shape available. Venue-wide capture, by
contrast, maximises the chance that `capture_target` finds `all` or
`group:<name>`. That is a document-semantics argument arriving at the same answer
as my count argument, which is usually a sign the answer is right.

**With both, on §7.1.** I expect resistance to deleting device commands from the
Control column — someone uses them. My position is that "someone uses it" is the
argument that produced fifty-four chrome controls, and it is exactly the argument
a calm-ops review exists to refuse.

---

## 9. Positions, in one place

| # | question | position |
|---|---|---|
| 1 | capture ownership | **Neither.** Venue-wide command; home is the Show edit bar as `✛ Capture`. Optional single tab-level button on Control, **no scope argument**, inline arm-then-fire, no `confirm()`, no `alert()`. Per-column is mislabelled by construction. |
| 2 | column width | Fixed `minmax(340px, 400px)`. No resize handles. |
| 3 | 1400px cap | Dropped on `.dashboard-tab`; column row **left-aligned**, not centred. |
| 4 | overflow | Horizontal scroll with snap, columns intact. Each column scrolls its own body; header sticky. Never auto-collapse. |
| 5 | picker default | `defaultOpen:false` in a column; the terse label is the header. |
| 6 | add / remove | `✕` icon in the column header (`visibility:hidden` at N=1); add is a ghost rail after the last column. |
| 7 | deleted seat | Prune to **empty**, never to `all`. Explicit unresolved state, no controls. Needs `pruneFallback` on the component. |
| 8 | empty group | Keep the column, disabled controls, `aria-disabled` plus the existing count. |
| 9 | overlap | Legal, encouraged, no new signalling. Keep the exact-match report predicate. |
| 10 | `followFocusSeat` | **None.** Explicit "Open in Control" from the Seats inspector. Fallback: follow only when N==1. |
| 11 | storage | One `bopos.control.columns` layout key with minted ids; host-owned persistence via the picker's optional `storageKey`. Branch collapse stays global. |
| 12 | identity | No `id` inside a column; scope every selector to the column root; unique `data-target-picker`; new CLAUDE.md gotcha 19; register `.control-column-*` in the ownership guard. |
| 13 | a11y | One live region **per column**, target-prefixed; columns are labelled regions; no positive `tabindex`; picker and `✕` first in DOM. |
| 14 | the real risk | Chrome multiplies. Cut device commands from the column, demote `new`/`save`/`del`, move `Send all` to overflow, and make the **column** the card so per-target blocks become ruled sections. |
