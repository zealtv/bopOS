# Judgment — capture-as-step ownership and the N-column open questions

Judge-synthesizer, 2026-07-31. Three lenses were convened per the stitch brief:
`expert-live-operator.md` (performance instrument), `expert-show-authoring.md`
(document semantics), `expert-calm-ops.md` (IA / count discipline / a11y).

I read all three, and I re-derived every load-bearing claim from the source
rather than taking it on faith. Where a lens is wrong or overreaches I say so.
Where they agree but for different reasons, the agreement is worth more than
either argument — I say that too.

---

## 1. The consult question, and why all three refused the fork as posed

The brief asked: **one column's target, or the whole tab's arrangement?**

All three lenses independently answered *neither*, and converged on **capture is
venue-wide**. Independent convergence from a performance lens, a document lens,
and a count lens is the strongest signal this consult produced, so it is worth
being precise about what each one actually contributed, because the three
arguments are not the same argument:

| lens | why venue-wide |
|---|---|
| show-authoring | `applied_preset` is a **total, single-valued function over seats**. The arrangement *is* that function. Both column readings are lossy filters over it, subtracting on a criterion — "what I had on screen" — the document cannot record or recover. |
| live-operator | The artifact is a venue state, not a viewport state. Two operators with the same room in the same state but different numbers of columns open would produce **different steps**. Presets also arrive from outside the columns (the Device tab, a column closed ten minutes ago) and column scoping silently omits them. |
| calm-ops | "The whole tab's arrangement" is a **phantom** — no code holds it. And N buttons differing only by a filter is a decision the operator must make with no right answer. |

I adopt all three, and I add the finding that settles it independently of taste.

### 1.1 The finding: per-column capture is not "easiest", it is currently wrong

Two lenses traced this separately and got the same table; I verified it a third
time against `facilitator.js:381-397` → `server.py:1804-1812`:

| column target | scope sent | seats the server actually captures |
|---|---|---|
| All | `all` | every seat ✔ |
| one seat `7` | `seat` | seat 7 ✔ |
| seats `1`,`2` | `all` (`:395`) | **every seat in the venue** |
| group `Left` | `groups` (`:396`) | **every grouped seat, including Right** |
| `Left` + seat `9` | `groups` (`:396`) | every grouped seat; **seat 9 dropped if ungrouped** |

Three of five column shapes are unfaithful, and the two unfaithful *group*
shapes are the ones columns exist to express. A capture button inside a column
headed `Left`, labelled by that column, would append a step containing `Right`.

So "per column seems perhaps easiest" — the premise Bob offered — does not
survive contact with the code. Per column is either **wrong**, or a server
change. That reverses the brief's framing entirely.

### 1.2 The instructions' warning is backwards, confirmed three times

The stitch instructions warned that an all-column capture "either reduces the
union (losing the arrangement) or needs a widened server vocabulary — which
`41-preset-primitive` deliberately declined once."

Every lens independently confirmed ground-truth §6: this is false.
`_captured_show_preset_messages` (`server.py:1838-1880`) never reads a picker.
It groups seats by their `applied_preset` marker and asks `capture_target`
(`preset_application.py:246-261`) for the most portable selector per group —
`all`, else `group:<name>`, else explicit ids. The arrangement was never carried
by the scope.

calm-ops sharpened it into the cleanest form of the correction: **widening the
vocabulary is the cost of the _per-column_ answer, not the whole-tab one.**
Making a column-scoped capture honest requires sending an explicit seat-id list
— exactly the widening the instructions warned about, attributed to the wrong
option. Venue-wide capture, by contrast, is a **removal**: delete `scope` and
`id` from both verbs, delete `presetScope()`, collapse `_capture_show_seats` to
`list(self.state.seats.values())`.

### 1.3 "But how do I capture only part of the room?" — already answered

show-authoring owns the decisive rebuttal to the one real objection: **F3 is
already the scoping mechanism.** Ratified F3 omits targets with no preset
applied, so a venue where four of twelve seats are in play captures four
messages. `scope` is a second, worse scoping mechanism layered on top — and
`scope:"groups"` actively drops ungrouped seats that *do* hold presets
(`server.py:1809-1811`), which is content removal on a criterion the operator
never stated.

I rule `scope:"groups"` an **active defect in the authoring loop today**,
independent of columns.

### 1.4 Ruling on the primary question

> **Capture is a venue-wide command. It takes no scope argument. There is
> never more than one capture affordance on the Control tab, and it is never
> inside a column.**

Columns are a lens, not a container (live-operator §1). Nothing in bopOS is
owned by a view: values, provenance and derived dirtiness all live on seats. A
capture button placed inside a column asserts by placement a subject it does not
have.

---

## 2. The one genuine disagreement: where the button lives

This is the only substantive split, and it is worth resolving rather than
splitting.

- **calm-ops**: the home is the **Show tab's edit bar** (`✛ Capture` beside
  `✛ Step`, `show.js:512-525`). Five arguments, of which three are strong:
  the result is only *visible* there; the step needs naming immediately
  (every capture is aliased `"Captured presets"`, `show_model.py:859`, never
  overridden); and insertion position is a document decision (capture appends,
  `✛ Step` inserts after the selection).
- **live-operator**: a thin **Control tab strip**, right-aligned, with
  `+ column` at the far left. Rejects the Monitor dock explicitly — *never put
  a rarely-used commit next to the panic button* — and rejects the tab rail
  (muscle-memory trap, too much text).
- **show-authoring**: Control tab chrome, on the ground, never inside a column.

**Ruling: both entry points, one unparameterised command.**

calm-ops's own §0 rule decides it: *"duplication that forces a choice is noise;
duplication that forces no choice is reach."* Once capture takes no arguments,
two entry points are not two decisions — they are the same command reachable
from the surface you happen to be on. calm-ops in fact conceded this shape in
§1.4 ("the same command with the same words"), and it is the right resolution
rather than a split-the-difference: the live path keeps the flow argument, the
Show path keeps naming, insertion and visibility.

Concretely: `✛ Capture` in the Show edit bar, and one `capture` control in a new
thin Control-tab strip that also carries `+ column`. Same words, same behaviour,
no scope on either.

I decline calm-ops's implication that Control's entry is merely a concession. The
live-operator's flow argument is real, and the reason the Control path currently
feels wrong is not its location — it is that it gives no feedback (§3.2), which
this design fixes.

---

## 3. What all three lenses found that nobody asked for

These arrived independently from three directions, which is why I rank them
above the questions actually posed.

### 3.1 The guarding is inverted (live-operator §7.1) — VERIFIED

| action | guard | audible | reversible |
|---|---|---|---|
| capture as step | 2 `alert`s + `confirm` (`facilitator.js:247-265`) | no | yes (`undo_show`) |
| **apply a preset** | **none** — bare `<select>` `onchange` (`control-surface.js:413-418`) | **instantly, across the whole target** | **no** — provenance overwritten |
| delete a preset | `confirm` (`:424`) | no | no |
| device reboot / shutdown | 1200 ms hold (`facilitator.js:414-419`) | yes | no |

I verified the apply path: `select.onchange` calls `context.applyPreset` with no
confirmation of any kind. **The app guards the safe, silent, reversible action
with three dialogs and leaves the loud, irreversible one bare** — and N columns
multiply the bare one, not the guarded one.

I do **not** rule for a confirm on apply; live-operator is right that a modal in
the audio path is worse than the mistake. But this asymmetry is the strongest
argument in the whole consult for deleting the capture dialogs, and it belongs
in the record.

### 3.2 Capture succeeds silently — VERIFIED, all three lenses

`capture_show_preset_step` → `apply_show_mutation` persists and broadcasts
`show` (`server.py:1428-1453`). `facilitator.js` registers **no `show`
handler** — I checked the complete handler list at lines 212-270. So a
successful capture produces no observable result on the surface that initiated
it. Only failure speaks, via `alert`.

An authoring loop with no completion signal is not a loop.

### 3.3 Undo is unreachable from Control (live-operator) — VERIFIED

`show.js:1162-1170` short-circuits on `showPanel?.hidden`, so ⌘Z is bound only
while the Show panel is visible. An accidental capture on the Control tab today
cannot be undone without switching tabs — and since §3.2 means the operator does
not know it happened, they will not.

### 3.4 `prune()` silently widens a column to All — VERIFIED, all three lenses

`target-picker.js:271-287`: when no selector survives pruning and `allowAll` is
true, it returns `["all"]`, and `resolve()` persists it (lines 300-309). A
column targeting Seat 7 becomes a column targeting **every seat** the moment
Seat 7 is deleted, with no confirmation and no announcement. The fader that
drove one seat now drives the venue.

This is a **live safety defect today at N = 1**, not a column problem. It is the
one direction a live control surface must never fail in. All three lenses found
it independently and all three ruled the same way.

I rule it in scope for this design — not because columns cause it, but because
columns multiply the exposure and this is the stitch that noticed.

---

## 4. Rulings on the five open questions

### Q1 — column widths and the 1400px cap

**Fixed 342px. Never elastic, never resizable. Cap dropped on this tab. Row
left-aligned.**

- Width: `320px` drawer + `2 × --pad-panel` (10px) + `2 × 1px` border = **342px**.
  The lenses said 340 (they omitted the border); the mockup measures 342 and
  renders correctly at it.
- **Not resizable.** All three agree. calm-ops's argument is decisive and is a
  safety one, not an aesthetic one: a resize handle is *a horizontal drag target
  sitting adjacent to a column full of horizontal drag targets*, and a grab that
  misses by 4px moves a parameter on live speakers.
- **Not elastic either — and here I overrule live-operator.** That lens wanted
  columns to share leftover space equally between a 340 floor and a ~440 ceiling,
  computed by the tab, so the same parameter sits at the same relative x in every
  column. The goal is right; the mechanism defeats itself. Elastic widths mean
  **adding a fourth column resizes the first three**, which violates the same
  lens's own §7.3 requirement that adding a column never move existing controls.
  Fixed width satisfies both properties at once. Equal-relative-x is preserved
  trivially because all columns are identical.
- **Drop `.tab-panel{max-width:1400px}` on this tab.** Unanimous. It is a
  reading-measure constraint on a surface with no measure; it costs a whole
  column at 1680 for no benefit. Measured, uncapped, at 342px + 12px gutter:
  **1280 → 3 columns, 1680 → 4, 2560 → 7.** The mockups render exactly this.
- **Left-align, do not centre.** calm-ops holds this strongly and is right:
  `margin:0 auto` means adding a fourth column slides columns one through three
  sideways. Positional stability across add/remove is an operating requirement;
  centring is an aesthetic.
- **Overflow scrolls horizontally, intact.** This is `06`'s ratified rule applied
  one level up — scroll the intact face, never rearrange it. Never auto-collapse
  overflow columns into rails.
- **Each column scrolls its own body; its header is sticky.** Two lenses
  independently required this. With full manifest visibility a page-level scroll
  to reach column 4 drags column 1 off screen, and a column whose target label
  has scrolled out of view is a mis-target waiting to happen.

### Q2 — a column that resolves to no seats

**Two different situations. The code currently conflates them in the dangerous
direction.**

- **Emptied group** (group exists, membership is zero) — benign. Keep the column,
  keep its target, render the existing `empty-group` state
  (`facilitator.js:206`), rows disabled, meta reading `g3 · 0 Seats`. Do not
  collapse to a bare `No Seats` (`facilitator.js:343`): that discards the
  operator's target, which is their work. Add `aria-disabled` so the state is
  announced rather than inferred from a count in a `<small>` (calm-ops).
- **Deleted seat or group** — the §3.4 defect. **The Control host's prune
  fallback is empty, never `all`.** The column keeps its slot and its dead
  selector and renders an explicit unresolved state with a re-target action and
  **no controls at all** — not disabled controls; there is nothing they could act
  on.
- This needs a component change: `prune` reaches `[]` today only via
  `allowAll === false`, which would also remove the All chip. The component must
  separate *All is offerable* from *All is the fallback* — a `pruneFallback:
  "empty"` option. The Assets tab's advance-to-next-eligible behaviour is
  deliberate (`target-picker.js:266-270`) and must be preserved.

### Q3 — overlapping columns and the applied-preset marker

**Do nothing structural. Overlap is legal, useful, and needs no new signalling.**

Ground-truth §4 holds: provenance is per seat and dirtiness is derived at render
(`preset_application.py:264`), so two columns cannot disagree — they render the
same fact twice. All three lenses ruled the same way, and live-operator gave the
best reason: overlap is the **console idiom** (a channel on its own strip and
under its VCA), and it is the only place the system ever shows its own
aggregation rule working. It also makes design-language §6's "editing unifies"
visible for the first time — you pull the All column's fader and watch the seat
column follow, which is hard takeover made legible.

Rejected: dedupe, a "primary column", cross-column highlighting, overlap
warnings. All are machinery for a problem that does not exist.

Adopted from show-authoring, one small win: **make `mixed` carry its content.**
An All column showing the word `mixed` beside a group column showing `dusk *`
reads as a contradiction when it is merely uninformative. `dusk +2` or
`3 presets` dissolves it — and it is the same underlying fix as the capture
preview, because the panel currently discards exactly the arrangement that
capture reconstructs.

Rejected from live-operator: the ~120ms "travel" transition on externally-caused
value changes. That lens offered it as droppable polish, it is unmeasured, and
it risks the generator animation machinery for a cosmetic gain.

Kept, per calm-ops: the apply report's **exact member-set match** predicate
(`facilitator.js:73-79`). Do not loosen it to "overlaps", or an apply in one
column prints its report inside another.

### Q4 — `followFocusSeat` with N columns

**No column follows ambiently. Replace it with an explicit verb.**

Two of three lenses ruled this; I follow them and overrule live-operator's
selected-channel latch.

- **Every column** is out, unanimously: `adoptFocusSeat` *replaces and persists*
  a selection (`target-picker.js:289-299`), so one click on the Seats tab would
  destroy a four-column arrangement, durably, with no undo.
- **live-operator's `⌖` latch** (at most one column follows, radio across the
  tab) is the most sophisticated answer and I still reject it: it adds a
  per-column control (N affordances for one behaviour), plus persistent invisible
  state, to save one click.
- **The workflow it protects is real and must survive.** `37/10` kept
  Seats → Control deliberately. The better expression, on which show-authoring
  and calm-ops independently converged, is an explicit **"Open in Control"**
  action in the Seats inspector: focus an existing column already targeting that
  seat if one exists, else append one, then switch tabs. Explicit, additive,
  non-destructive — and it performs the tab switch, which the ambient version
  never did.
- **Compatibility rule:** ambient follow applies **only when exactly one column
  exists**. A single-column operator gets today's behaviour byte for byte, and
  the ambiguity cannot arise because there is nothing to be ambiguous between.
  This is the one ruling here I would most readily see Bob overrule to "none at
  all"; it is a compatibility kindness, not a principle.
- No plumbing is preserved by keeping ambient follow: the `storage`-event
  delivery does not fire same-document and `3-iframe-retirement` must rewrite it
  regardless (ground-truth §2).

### Q5 — capture-as-step ownership

Ruled in §1.4 and §2.

---

## 5. The capture interaction, resolved from three partial answers

Each lens proposed a different replacement for the two `alert`s and the
`confirm`. They are complementary, not competing, and compose into one flow:

| lens | contribution |
|---|---|
| live-operator | the count is **ambient on the control** (`capture step · 12/16`), computed client-side with no round trip; inline undo after commit |
| calm-ops | **arm-then-fire, never a modal** — the ratified `41/07` rule for the apply report (`control-surface.js:289-290`) applies here too |
| show-authoring | the commit step shows **the messages the server would mint**, not counts — this is the whole WYSIWYG fix |

**Ruling — the composed flow:**

```
capture step · 12/16                     ← ambient, always visible
   ↓ click (arms; no dialog, nothing committed)
┌ Capture arrangement — 3 messages, 4 seats omitted ──────────┐
│  PRE  dusk   → group “Left”        portable                 │
│  PRE  bloom  → group “Right”       portable                 │
│  PRE  solo   → seats 7, 9          site-bound *             │
│  —    (none) → 4 seats             not captured             │
│                                  [ Cancel ]  [ Capture ]    │
└─────────────────────────────────────────────────────────────┘
   ↓ commit
captured “dusk + bloom + solo” · undo     ← ~8s, same slot
```

Notes on why each piece is there:

- **The ambient count needs no round trip.** The client already holds
  `applied_preset` on every seat — it is what `presetProvenance()` reads
  (`control-surface.js:277-286`) — and after `3-iframe-retirement` the Control
  tab is the same document that receives the `shows`/`show` messages
  (`server.py:289-292`), so "is a show loaded" is local too. I verified both.
  **The entire `preview_show_preset_capture` round trip exists because the
  iframe could see neither fact.** Retiring the iframe retires the reason for
  the handshake.
- **No `alert`, no `confirm`, ever.** They block the whole document — the
  Monitor dock stops updating, the heartbeat re-render stops — which on a
  surface whose job is telling you what the room is doing is a blackout. They
  also offer Chrome's "prevent this page from creating additional dialogs",
  after which every future capture silently does nothing. Both no-show and
  nothing-applied become **disabled states with the reason in place**, visible
  before reaching rather than after clicking.
- **Naming.** Derive the alias from content (`dusk + bloom + solo`, truncated)
  instead of `"Captured presets"` for every step, and hand the new step to the
  Show tab's existing click-to-edit rename (`show.js:95-111`). Naming a cue when
  you record it is table stakes in every cue stack. This is a defect regardless
  of how the ownership question is ruled.
- **Undo** sends the existing `undo_show` verb. It is scoped to the ~8s window
  and to the step just appended. *Caveat I add and neither lens raised:*
  `undo_show` undoes the last show mutation, whatever it was — if the operator
  edits the Show tab within that window, the inline undo now means something
  else. Implementation must either clear the affordance on any intervening show
  mutation, or verify the top of the undo stack before firing.
- **Dirty and site-bound rows are marked in the preview.** Both are ratified
  behaviour nobody currently says out loud (§6.2).

---

## 6. Findings I rank above the questions asked

### 6.1 Chrome multiplies; content does not (calm-ops §7.1)

Counted per Seat card, before a single parameter row: `Send all`, the preset
`<select>`, `new`, `save`, `del`, the `Device setup` disclosure — and inside it
Update bopOS / Reboot / Shutdown. **Six chrome controls per card.** A column
holding a three-seat mixture renders three cards; three such columns render
**fifty-four chrome controls before the operator reaches what they came for.**

The mockup was costed against one panel. Nothing in the shipped card was costed
against three. I rule this the risk that decides whether the design succeeds,
and I adopt calm-ops's three cuts with one qualification:

1. **Device commands leave the Control column.** Update bopOS / Reboot /
   Shutdown behind a hold-to-confirm, inside a live parameter panel, is a
   category error at N=1; at N=3 it is three copies of a destructive fleet
   action one disclosure from the faders. The Devices tab owns device lifecycle
   and `07` established the hand-off pattern. **They stay on Remote** — an iPad
   away from the rack is exactly where a per-device reboot earns its place.
   *This is a Bob-visible behaviour change; it is flagged as such in the
   proposal, not smuggled in.*
2. **`new`/`save`/`del` demote behind one disclosure; the `<select>` stays in
   the row.** Applying is the live act; the other three are authoring. This also
   corrects a real IA lie calm-ops caught: **`del` is patch-scoped, not
   target-scoped** — it removes the preset from the store for the whole
   installation (`control-surface.js:425`) while sitting in a row whose every
   other control acts on this column's target.
3. **`Send all` moves to an overflow.** It is a rescue action for a returning
   node, not a live gesture.

### 6.2 Two ratified-but-unbuilt obligations the capture preview should discharge

- **Site-bound targets are minted silently.** `capture_target` falls through to
  explicit seat ids whenever the seat set is neither the whole venue nor an
  exact group match (`preset_application.py:261`). Ratified R3 says the Show tab
  should treat seat-id targets as site-bound and say so; nothing in `dashboard/`
  does. Capture is the main *producer* of them, so the preview is the honest
  place to say it first.
- **Dirty capture is lossy in the sonic dimension.** Capture takes the marker,
  not the values; `preset_dirty` never enters `_captured_show_preset_messages`.
  So an hour spent dialling the room past a preset captures the *preset*, not
  the hour — and the confirm dialog does not mention dirtiness at all. The
  preview marks it and offers the obvious next action (*save these values as a
  preset first*) inline.

### 6.3 Restart amnesia (show-authoring §4.5) — VERIFIED

`applied_preset` and `preset_dirty` are stripped before persistence
(`state.py:420-427`); seat *params* are not. So after a dashboard restart the
venue sounds identical, every fader is where it was, and capture reports
"0 of 12 targets have a preset applied; there is nothing to capture." Nothing on
screen explains why. This is ratified behaviour (F4) and I am not reopening it —
but the empty path must say *why* it is empty: a different sentence for a
different cause.

### 6.4 Blockers that belong to `2-control-column-component`, not `4`

calm-ops found the one that would otherwise be discovered late, and I verified
it:

- **One `ControlSurface` instance per column is required** — `openDrawers`,
  `drafts`, `openSaveDrawers`, `saveExclusions` are keyed by `scope:id`, not by
  column, so a shared instance would open the same drawer in two columns.
- **But per-column instances break the fade animator**, which is document-wide:
  `animateFades` queries `document.querySelectorAll('[data-fade-anchor]…')` at
  `control-surface.js:763`, and again at `:788` and `:792`. N instances start N
  rAF loops, each walking *every* column's anchors and writing their readouts —
  N× the work, racing each other's `input.value` writes. Either scope those
  three queries to the bound root or hoist the animator to a module singleton.

`bind(root = document)` is already parameterised (`control-surface.js:404, 828,
965, 971`), so scoping the binders is cheap; `facilitator.js:356`'s
`surface.bind(document)` becomes `surface.bind(columnEl)`. The animator is the
only genuinely document-wide piece. **This must be settled in `2`, not
discovered in `4`.**

### 6.5 Identity collisions (calm-ops §6)

Adopted wholesale; the shape is `05d`'s. No `id` attribute anywhere inside a
column; every selector scoped to the column root; one `bopos.control.columns`
layout key holding **minted ids, never indices** (indices renumber on remove and
silently re-point both storage and `aria-labelledby`); one live region per
column rather than per card, **prefixed with the column's target** (without
attribution, a takeover announcement heard twice from two regions is unusable);
columns as labelled `<section>`s; no positive `tabindex`.

One correction I contribute: calm-ops lists `data-preset-key` as a live
collision via `root.querySelector` at `control-surface.js:443`. It is real, but
it is *latent* rather than live today — `bind(document)` is called once per
render over a single card list. It becomes live the moment two columns carry the
same target, which §7.3 of that file correctly says should be **allowed**. So
the fix is required, not optional.

Also useful for the sweep: `facilitator.css:71`'s
`main[data-live-view=aggregate] .all-card{grid-column:1/-1}` is **dead** —
`selectionMode` only ever returns `all`/`groups`/`seats`/`mixed`
(`facilitator.js:324-329`). The codebase's only existing multi-column rule has
an inert exception in it. Do not port it forward as prior art.

### 6.6 A finding from building the mockup, which no lens could have seen

The mockup composes the **real** rendered surface (see `mockup.py`), and it
surfaced something none of the file-reading lenses caught: `.live-card`,
`.live-card-head`, `.name`, `.dot`, `.send-all`, `.promoted-controls` and
`.empty` are all declared in **`css/facilitator.css`** (lines 26-52) — a
stylesheet `index.html` does not load. Today that is invisible because the
Control tab is an iframe of `facilitator.html`.

**The moment the iframe goes, the parent document has no card chrome at all.**
This is `05e`'s pattern for the fourth time (component rules living on a host
stylesheet), and it is a concrete, load-bearing task for
`3-iframe-retirement` — at desktop metrics, not the tablet-first 44px/19px
facilitator values it would be tempting to port.

---

## 7. What I reject

- **Per-column capture**, in every form — §1.1. Not a preference; it is
  mislabelled by construction in three of five column shapes.
- **"The whole tab's arrangement" as a distinct concept** — no code holds it,
  and adopting it would encode the operator's window layout into the show
  document.
- **live-operator's elastic equal-width columns** — self-defeating against that
  lens's own positional-stability requirement (§Q1).
- **live-operator's per-column `⌖` follow latch** — N affordances plus invisible
  persistent state to save one click (§Q4).
- **live-operator's 120ms travel transition** — unmeasured polish that risks the
  generator animation (§Q3).
- **Any modal on this surface** — `alert`/`confirm` block the entire document,
  including the Monitor dock and the heartbeat re-render.
- **Centring the column row** — adding a column would move every existing one.
- **Cross-column dedupe, overlap warnings, or a "primary column"** — machinery
  for a problem that does not exist.
- **Preventing duplicate-target columns** — allow them; the collisions they
  expose (§6.5) must be fixed on their own merits anyway.
- **A column cap** — Bob operates this himself; a cap is a nuisance. Screen
  space allows seven at 2560; attention allows about three. Make `+ column`
  quieter than `capture` and let the operator decide.

---

## 8. One-line ruling

**Capture is a venue-wide command that takes no scope argument — the arrangement
lives in per-seat provenance, not in the columns, and per-column capture is
mislabelled by construction in three of five column shapes; it is reachable as
one unparameterised action from both the Show edit bar and a single Control-tab
strip, arms into a non-modal preview of the messages it would mint, commits with
inline undo, and never opens a dialog. Columns are fixed 342px cards, left
aligned, uncapped, each scrolling under a sticky header that is its own closed
target picker; no column follows the Seats tab ambiently; a column that loses its
target goes inert rather than silently widening to All.**
