# Proposal — the N-column Control tab

**Bob decision gate.** This is the ratification document for
`08-control-tab-columns/1-columns-design`. Ruling it produces `decisions.md`
and unblocks `4-n-columns`.

Supporting material in this stitch:

| file | what it is |
|---|---|
| `ground-truth.md` | the code-grounded brief, with two corrections to the stitch instructions |
| `expert-live-operator.md` | UX consult — performance-instrument lens |
| `expert-show-authoring.md` | UX consult — document-semantics lens |
| `expert-calm-ops.md` | UX consult — IA / count / accessibility lens |
| `judgment.md` | adjudication of the three, with everything re-verified against source |
| the `mockup-*.png` files here | 1280 / 1680 / 2560 / 760 / armed-capture, dark + light |
| `mockup.py` | the generator — boots the real app and composes the real rendered surface |

**The mockups are not drawings.** `mockup.py` boots `dashboard/server.py` +
`simfleet`, renders the actual control surface once per column target, and
composes the real markup into the proposed shell with the shipping stylesheets.
Every card, row, picker, preset row, mixed hatch and dirty marker in those shots
is what the code produces today. Only the column shell is new.

---

## The headline: the consult question had a wrong premise

You asked whether a Show step is captured from **one column's target** or from
**the whole tab's arrangement**, noting *"per column seems perhaps easiest."*

All three lenses independently answered **neither**, and tracing the code shows
per column is not merely harder — **it is wrong today**:

| a column targeting… | sends | the server actually captures |
|---|---|---|
| All | `all` | every seat ✔ |
| one seat `7` | `seat` | seat 7 ✔ |
| seats `1`,`2` | `all` | **the whole venue** |
| group `Left` | `groups` | **every grouped seat, including Right** |
| `Left` + seat `9` | `groups` | every grouped seat; **seat 9 dropped if ungrouped** |

A capture button inside a column headed `Left` would append a step containing
`Right`. Three of five column shapes are unfaithful, and the two unfaithful
*group* shapes are the ones columns exist to express.

The reason is that **the arrangement was never carried by the picker.**
`_captured_show_preset_messages` groups seats by their `applied_preset` marker
and derives the most portable selector per group (`all` → `group:<name>` →
seat ids). The scope you send is only a filter over *which seats are
considered*. So:

- The stitch instructions' warning — that an all-column capture would need "a
  widened server vocabulary, which `41` deliberately declined" — is **backwards**.
  Widening is the cost of the *per-column* answer. Venue-wide capture is a
  **removal**: delete `scope`/`id` from two verbs and delete `presetScope()`.
- **F3 is already the scoping mechanism.** Targets with no preset applied are
  omitted, so "only part of the room is in play" is handled without a scope
  argument at all.
- `scope:"groups"` is an **active defect today**: it drops ungrouped seats that
  *do* hold presets.

---

## Decisions for ratification

### D1 — Capture is venue-wide and takes no scope argument ★

One unparameterised command. `scope` and `id` leave the wire;
`_capture_show_seats` collapses to every seat; `presetScope()` is deleted.

**Reachable from two places, same words, same behaviour:** `✛ Capture` in the
Show tab's edit bar (beside `✛ Step`), and one `capture step · 12/16` control in
a new thin Control-tab strip. Never inside a column, never more than one per
surface. Two entry points for a command with no arguments is reach, not a
choice.

### D2 — No dialogs. Arm, preview, commit, undo ★

The two `alert()`s and the `confirm()` come out. They block the entire document
— the Monitor dock stops updating and the heartbeat re-render stops — which on
a surface whose job is telling you what the room is doing is a blackout.

```
capture step · 12/16                    ← ambient count, always visible
   ↓ click (arms — nothing is committed)
┌ Capture arrangement — 3 messages, 4 seats omitted ─────────┐
│  PRE dusk  → group “Left”     portable                     │
│  PRE bloom → group “Right”    edited since applied          │
│  PRE solo  → seats 7, 9       site-bound                   │
│  —   (none)→ 4 seats          not captured                 │
│                              [ Cancel ]  [ Capture ]       │
└────────────────────────────────────────────────────────────┘
   ↓ commit
captured “dusk + bloom + solo” · undo    ← ~8s, same slot
```

See `mockup-armed-*.png`. Three supporting points:

- **The round trip disappears.** The client already holds `applied_preset` on
  every seat, and after `3-iframe-retirement` the Control tab is the same
  document that receives `show`/`shows`. `preview_show_preset_capture` exists
  only because the iframe could see neither fact.
- **"No show loaded" and "nothing applied" become disabled states with the
  reason in place** — visible before reaching, not after clicking.
- **The preview says what the confirm never did**: which rows are dirty
  (capture takes the preset, not the hour of fader work past it) and which are
  site-bound seat-id targets rather than portable group names. Both are ratified
  behaviour that nothing currently says out loud.

### D3 — Captured steps get a real name

Every capture today is aliased `"Captured presets"` and appended at the end.
Three captures give three identical rows. Derive the alias from content
(`dusk + bloom + solo`) and hand the new step to the Show tab's existing
click-to-edit rename. This is a defect regardless of how D1 is ruled.

### D4 — Columns are fixed 342px cards, left-aligned, uncapped

- **342px** = the 320px generator face + 2 × `--pad-panel` + 2 × 1px border. The
  column *is* the card; the per-target blocks inside it become ruled sections,
  not nested bordered boxes (design-language §12 forbids both nesting cards and
  showing ground inside a card's footprint).
- **Never resizable.** A resize handle is a horizontal drag target sitting
  beside a column of horizontal drag targets; a grab that misses by 4px moves a
  parameter on live speakers.
- **Never elastic.** Sharing leftover width would mean adding a fourth column
  resizes the first three. Fixed width is what makes add/remove positionally
  stable.
- **Drop `max-width:1400px` on this tab** and **left-align** the row. Measured:
  1280 → 3 columns, 1680 → 4, 2560 → 7. The cap costs a whole column at 1680 for
  no benefit; centring would slide existing columns sideways every time one is
  added.
- **Overflow scrolls horizontally, intact** — `06`'s ratified rule one level up.
  Never auto-collapse.
- **Each column scrolls its own body under a sticky header**, and that header is
  the column's own target picker, **closed by default**. Its terse readout
  (`all`, `Left+7`) is the column's title. An open picker costs ~180px of a
  342px column, times N, for a control set once.

### D5 — A column that loses its target goes inert, never widens ⚠

**This is a live safety defect today, at N = 1.** `prune()` falls back to
`["all"]` and persists it, so a column targeting Seat 7 silently becomes a
column targeting **every seat** the moment Seat 7 is deleted. The fader that
drove one seat now drives the venue, with no confirmation and no announcement.
All three lenses found it independently.

- **Deleted seat/group** → the Control host prunes to **empty**. The column keeps
  its slot and its dead selector and renders `Seat 7 is no longer in this venue`
  with a re-target action and **no controls at all**.
- **Emptied group** (group exists, zero members) → keep the column and its
  target, rows disabled, meta reading `g3 · 0 Seats`, plus `aria-disabled`. See
  the fifth column in `mockup-2560-*.png`.
- Needs a `pruneFallback: "empty"` option on `TargetPicker`; the Assets tab's
  advance-to-next-eligible behaviour is deliberate and must be preserved.

### D6 — Overlapping columns need nothing

Two columns showing the same seat cannot disagree — provenance is per seat and
dirtiness is derived at render. Overlap is the console idiom (a channel on its
own strip and under its VCA) and it is the only place the system shows its own
aggregation rule working: pull the All column's fader and watch the seat column
follow, which is hard takeover made visible.

No dedupe, no "primary column", no overlap warning. One small win adopted: make
`mixed` carry its content (`dusk +2` rather than the bare word), so an All
column beside a group column stops reading as a contradiction.

### D7 — No column follows the Seats tab ambiently

Ambient follow *replaces and persists* a selection, so one click on the Seats
tab would destroy a four-column arrangement durably, with no undo.

Replace it with an explicit **"Open in Control"** action in the Seats inspector:
focus an existing column already targeting that seat if there is one, else
append one, then switch tabs. Explicit, additive, and it performs the tab switch
the ambient version never did.

**Compatibility:** ambient follow still applies when exactly one column exists,
so a single-column operator sees no change. *This is the ruling I hold most
loosely — say if you would rather it be "never".*

### D8 — Cut chrome from the Control column ⚠ behaviour change

Counted per seat card, before a single parameter row: `Send all`, the preset
`<select>`, `new`, `save`, `del`, and the `Device setup` disclosure holding
Update bopOS / Reboot / Shutdown. **Six chrome controls per card.** A column
holding a three-seat mixture renders three cards; three such columns render
**fifty-four chrome controls before the operator reaches a parameter.** The
panel was costed against one card; nothing in it was costed against three.

1. **Device commands leave the Control column** — Update bopOS / Reboot /
   Shutdown behind a hold-to-confirm, inside a live parameter panel, one
   disclosure from the faders, times N. The Devices tab owns device lifecycle.
   **They stay on Remote**, where an iPad away from the rack is exactly where a
   per-device reboot earns its place.
2. **`new`/`save`/`del` demote behind one disclosure**; the `<select>` stays in
   the row, because applying is the live act and the other three are authoring.
   This also corrects a real mislabelling: **`del` is patch-scoped** — it removes
   the preset from the store for the whole installation — while sitting in a row
   whose every other control acts on this column's target.
3. **`Send all` moves to an overflow.** It is a rescue action for a returning
   node, not a live gesture.

This is the one decision that changes behaviour you may rely on, which is why it
is flagged rather than folded in.

### D9 — Layout persistence

One `bopos.control.columns` key holding an ordered list of
`{id, target, open}` with **minted ids, never indices** — indices renumber on
remove and would silently re-point both storage and `aria-labelledby` at the
wrong column. `bopos.target.control` migrates once into column 1.
`bopos.control.collapsed-branches` stays global across columns: the operator is
pruning the manifest, not a card.

---

## Two findings that belong to sibling stitches

Neither needs ratification; both would be discovered late and expensively.

**For `2-control-column-component`:** one `ControlSurface` instance per column is
*required* (`openDrawers`/`drafts` are keyed by target, not column, so a shared
instance opens the same drawer in two columns) — **but** the fade animator is
document-wide (`animateFades` queries `document.querySelectorAll` three times),
so N instances start N rAF loops that each walk every column's anchors and race
each other's writes. Either scope those queries to the bound root or hoist the
animator to a module singleton. `bind(root = document)` is already
parameterised, so the binders are cheap; the animator is the only genuinely
global piece.

**For `3-iframe-retirement`:** `.live-card`, `.live-card-head`, `.name`, `.dot`,
`.send-all`, `.promoted-controls` and `.empty` are all declared in
`css/facilitator.css` — which `index.html` **does not load**. That is invisible
today because the Control tab is an iframe of `facilitator.html`. The moment the
iframe goes, the parent document has no card chrome at all. This is `05e`'s
pattern for the fourth time, and the replacement should be written at desktop
metrics rather than porting the tablet-first 44px/19px values. (Found by
building the mockup, not by reading the files.)

Also: `facilitator.css:71`'s `main[data-live-view=aggregate] .all-card` rule is
**dead** — `selectionMode` never returns `aggregate`. The codebase's only
existing multi-column rule has an inert exception in it. Do not port it forward
as prior art.

---

## One thing worth saying plainly

The consult surfaced an asymmetry nobody set out to look for:

| action | guard | audible | reversible |
|---|---|---|---|
| capture as step | 2 alerts + a confirm | no | yes |
| **apply a preset** | **none** — a bare `<select>` | **instantly, across the whole target** | **no** |

The app guards the safe, silent, reversible action with three dialogs, and
leaves the loud, irreversible one bare — and N columns multiply the bare one.

No lens asked for a confirm on apply; a modal in the audio path is worse than
the mistake. But it is the strongest argument in the consult for D2, and it is
worth your eye independently of this stitch.

---

## Ruling checklist

| # | decision | ★ = the consult question |
|---|---|---|
| D1 | venue-wide capture, no scope; Show edit bar + one Control strip control | ★ |
| D2 | no dialogs; arm → preview → commit → inline undo | ★ |
| D3 | derive the captured step's name; open the inline rename | |
| D4 | fixed 342px columns, left-aligned, cap dropped, sticky closed picker | |
| D5 | prune to empty, never to All; inert column | ⚠ live defect |
| D6 | overlap needs nothing; make `mixed` informative | |
| D7 | no ambient focus-seat follow; explicit "Open in Control" | held loosely |
| D8 | cut device commands / demote preset authoring / overflow `Send all` | ⚠ behaviour change |
| D9 | one layout key, minted ids | |
