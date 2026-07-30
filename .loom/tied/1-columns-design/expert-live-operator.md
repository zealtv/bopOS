# Expert consult — the live-operator / performance-instrument lens

Reference points: a lighting desk, an SSL centre section, Ableton's session
view. Not a web admin panel. The operator is standing, in the dark, with two
hands, and the room is listening.

Everything load-bearing below is cited to source. Where I am giving a
professional opinion rather than reporting the code, I say so.

---

## 0. The answer in one paragraph

**Capture is neither per column nor "across all columns" — it is
venue-wide, and there is exactly one capture control on the tab.** Per-column
capture is not merely harder; as the code stands it is *a lie* — a button
beside a column targeting group `Left` captures every seat in every group
(`facilitator.js:396` → `server.py:1809-1811`). Making it truthful costs a
server change, and having made it truthful you would have built four buttons
that mostly do the same thing, on the one surface in the app where the number
of committing affordances should be as close to one as the task allows. The
arrangement a step records lives in per-seat provenance (`server.py:1838-1880`),
not in the columns; the columns are a lens, not a container. So: one control,
in the tab's own strip, capturing what the venue currently asserts — and while
we are there, **delete the two `alert()`s and the `confirm()`** (`facilitator.js:247-265`),
which are the worst thing in the current design and get four times worse with
four buttons.

---

## 1. The spine: a column is a lens, not a container

Every position I take below falls out of one observation about this system.

Nothing in bopOS is owned by a view. Parameter values live on seats
(`facilitator.js:347-353`). Applied-preset provenance lives on seats
(`41-preset-primitive` F4, `.loom/tied/1-preset-architecture-design/decisions.md:23-34`);
dirtiness is *derived at render* (`preset_application.py:264`) and never
stored. A card's verdict is a projection of its members
(`control-surface.js:275-287`). The Device tab and the patch editor apply
presets through the same `ControlSurface`, so a seat can be carrying a preset
applied from a panel that no longer exists on screen.

Columns will nonetheless *read* as containers. They are vertical, they have a
name at the top, they sit side by side — that is a mixer, and a mixer's strips
own their channel. Operators will call the third column "my Left mix" within a
day. The design's whole job is to keep that misreading from becoming
load-bearing, because the first time two columns overlap, "this column owns
Left" is false and the operator has to unlearn it under time pressure.

Concretely, that means: no per-column preset ownership, no per-column capture,
no per-column mute/solo, no per-column undo. A column contributes exactly two
things — *which seats am I looking at* and *where are my hands* — and nothing
it does is attributable to it afterwards. Everything else belongs to the seat
or to the tab.

The other two lenses will, I suspect, arrive at per-column capture from
different directions (authoring wants narrow steps; calm-ops wants the button
next to the thing it acts on). I think both are wrong here, and §2 argues it.

---

## 2. The primary question: who owns capture-as-step

### 2.1 What per-column capture would capture today

`presetScope()` (`facilitator.js:381-397`) reduces a picker selection to one of
three coarse scopes, and `_capture_show_seats()` (`server.py:1804-1812`) turns
that scope into a set of seats. Trace every selection shape a column can hold:

| column target | scope sent | seats actually captured |
|---|---|---|
| All | `all` | every seat |
| one seat | `seat` | that seat ✔ |
| two seats | `all` (`facilitator.js:395`) | **every seat** |
| one group `Left` | `groups` (`:396`) | **every seat in any group** |
| `Left` + seat 7 | `groups` | **every seat in any group** |

Only two of five shapes are faithful. A capture button sitting inside the
`Left` column, labelled with `Left`, would append a step containing `Right` and
`Centre` as well. That is not a rough edge; on a performance surface it is the
category of bug that destroys trust in a control permanently — the operator
hits it once, gets a step full of targets they did not ask for, and from then
on stops using capture and hand-authors steps instead.

So "per column is easiest" is false at the outset. Per column is *either*
wrong *or* a server change.

### 2.2 The server change is cheap — and still not worth making

Ground-truth §5 is right that the instructions' warning is backwards: the
arrangement was never carried by the scope. `_captured_show_preset_messages`
(`server.py:1838-1880`) groups the candidate seats by their applied preset,
then asks `capture_target()` (`preset_application.py:246-261`) for the most
portable selector shape per group — `all`, else `group:<name>`, else an
explicit seat list. Making capture faithful to a column is therefore a
two-line change: `_capture_show_seats` takes the picker's selector list and
resolves it the way the panel already resolves it, and `presetScope()` is
deleted. Nothing about `41`'s ratified model resists it.

I still argue against it, for reasons that have nothing to do with cost:

**(a) The artifact is a venue state, not a viewport state.** A step that
replays says "the room sounds like this". Capturing the union of whichever
panels happened to be open encodes the operator's *window layout* into the
show document. Two operators with the same venue in the same state, one with
three columns open and one with five, produce different steps. That is the
"print what's on screen" mistake, and shows outlive layouts.

**(b) Presets arrive from outside the columns.** A seat preset applied from the
Device tab, or from a column removed ten minutes ago, is part of what the room
is doing. Column-scoped capture silently omits it — and silent omission is
exactly what `41` F3 went out of its way to prevent by making the button state
its count (`decisions.md:18-21`).

**(c) N buttons that mostly agree is worse than one.** With four columns whose
targets overlap — the normal case — four capture buttons produce nearly
identical steps. The operator now has a choice to make that has no right
answer, at the moment they least want a choice. Every desk I would compare
this to has *one* RECORD; what it records is decided by the state of the room,
not by which window has focus.

**(d) Pressing three of them makes a mess.** `capture_preset_step()` appends
with a fixed alias (`show_model.py:859`, `alias="Captured presets"`), fixed
5.0s duration, `then_actions:[stop]`. Three presses give three steps all named
`Captured presets` at the end of the show, and the operator cleans that up
later, on the Show tab, blind to which was which.

### 2.3 The recommendation

**One capture control, tab-scoped, venue-wide.** Send no scope at all; delete
`presetScope()` and `_capture_show_seats()`. Per ground-truth §5 this is
removing an argument, not adding one — the whole reduction machinery is
inert except as a way to lose targets (`scope:"groups"` drops any seat with no
group membership, `server.py:1810-1811`, which is precisely the seat an
operator would be astonished to lose).

Label it for what it does, with its own count in it:

```
capture step · 12/16
```

12 seats carry a preset, 16 exist, so 4 will be omitted (F3). That readout is
the whole preview, permanently on screen, computed **client-side with no round
trip**: the client already holds `applied_preset` on every seat — it is what
`presetProvenance()` reads (`control-surface.js:277-286`) — and after
`3-iframe-retirement` the Control tab is the same document as `show.js`, which
already knows whether a show is loaded (`show.js:1668`). The entire
`preview_show_preset_capture` round trip exists because the iframe could not
see either fact. Retiring the iframe retires the reason for the handshake.

### 2.4 What the handshake costs mid-show, and what replaces it

Today: click → wait for a server round trip → possibly `alert("Load or create a
Show…")` → dismiss → possibly `alert("0 of 16 targets…")` → dismiss → else
`confirm("… Add this arrangement as a Show step?")` → dismiss
(`facilitator.js:247-265`).

Costs, from the operator's side:

- `alert`/`confirm` block the *entire document*. Not the tab — the document.
  The Monitor dock stops updating, the heartbeat re-render stops, meters
  freeze. On a surface whose job is telling you what the room is doing, a
  modal is a blackout.
- They steal keyboard focus, and Chrome offers "prevent this page from
  creating additional dialogs" — one stray tick and every future capture
  silently does nothing.
- The response is handled by an unkeyed global listener (`facilitator.js:247`;
  contrast the preset-capture preview, which at least guards on
  `pendingPreview`, `:233-238`). Two presses in quick succession can pop a
  dialog over an unrelated part of the screen after the operator has moved on.
  With one button that is tolerable. With N it is a jump scare.
- And the guarding is upside down. Capture is *reversible* (undo stack,
  `server.py:1451`), *inaudible*, and touches a JSON file. Yet it gets two
  dialogs — while applying a preset to every seat in a group is a bare
  `<select>` `onchange` with no confirmation at all
  (`control-surface.js:413-418`), is instantly audible to the audience, and
  overwrites provenance irreversibly. The app currently guards the safe thing
  and leaves the loud thing bare. See §7.1.

Replace with: **live readout → single click commits → inline undo.**

```
capture step · 12/16          ← before
captured "Captured presets" · undo   ← for ~8s after, in the same slot
```

Undo needs saying out loud, because it is currently unreachable from this
surface: `show.js:1162-1170` binds ⌘Z only when the Show panel is *visible*
(`showPanel?.hidden` short-circuits). An operator who captures by accident on
the Control tab today has no way to undo it without changing tabs. The inline
undo link fixes that at the exact moment it matters, and it is the correct
reversal model for an action this cheap: commit immediately, offer the takeback
in place. (Judgment, not code: I would *not* extend the ⌘Z binding app-wide —
a global undo whose target is an invisible document is worse than no undo.)

The one case that still deserves a hard stop is "no show is loaded": there is
nothing to append to. Do not alert. Render the control disabled with its reason
in place — `capture step · no show loaded` — which is a state the operator can
see *before* reaching, not after.

### 2.5 Where the control lives

In a thin tab strip above the column row, right-aligned, with `+ column` at the
left end. Not in a column; not in the Monitor dock's Globals panel.

The dock is tempting (master, MUTE ALL and event lead moved there in
`03-global-controls-monitor`) and I reject it for one reason: adjacency to
MUTE ALL. Never put a rarely-used commit next to the panic button. Globals are
things that act continuously on the fleet; capture is a commit against an
offline document, and it should not share a neighbourhood with either the
faders or the kill switch.

I also considered the tab rail, where `03-chrome-reclamation` right-aligned the
`Remote` link — it would cost zero vertical space. I reject it too: a fixed rail
whose right end is `Remote` on four tabs and `capture` on one is a
muscle-memory trap, and `12/16` is too much text for that rail.

The strip costs ~34px of the height `03` reclaimed. I think that is the right
trade — it is the only chrome the tab gains, and it absorbs both tab-scoped
actions.

---

## 3. Column widths, and the 1400px cap (Q1)

**Fixed width, no resize handle, all columns equal.**

An instrument's controls do not move. If columns are individually resizable,
the fader you reach for lives at a different x after every drag, on every
machine, and a mis-grabbed handle mid-show shifts every control to its right.
The gain — a longer slider throw — is real but small, and §9 already answers
precision properly with click-to-type entry on every numeric display.

Not ragged, though: let columns share the leftover space equally between the
`340px` floor (`control-panel.css:148`, `320px + 2 × --pad-panel`) and a `~440px`
ceiling, computed by the tab, never by the operator. Equal widths mean the same
parameter sits at the same `y` and the same relative `x` in every column, which
is the entire reason to have columns side by side — you scan across a row of
faders, you do not read each strip.

**Lift the 1400px cap on this tab.** `.tab-panel{max-width:1400px}`
(`style.css:44`) is a measure-of-text cap on a surface with no text to measure,
and it costs a whole column:

| viewport | usable | columns capped at 1400 | columns uncapped |
|---|---|---|---|
| 1280 | 1248 | 3 | 3 |
| 1680 | 1368 | 3 | **4** (4×340 + 3×16 = 1408 ≤ 1648) |
| 2560 | 1368 | 3 | 7 fit; operator will not want 7 |

At 1680 — a common laptop-plus-projector width — the cap is the difference
between three columns and four for no benefit. Uncapped, the column strip is
centred and the ground shows as margin either side, which is exactly what §12
says ground is for. No count cap is needed: the operator adds and removes
columns themselves, minimum one.

Two structural calls that go with the width:

- **The column is the card, not a container of cards.** A column targeting
  `Left + seat 7` renders two cards today (`facilitator.js:341`). Nesting
  bordered cards inside a bordered column is the "swimming" look §12 forecloses
  in the other direction. Make the column one card whose picker is its header
  and whose multiple targets are `--subpanel` sections within it.
- **Each column scrolls independently, with a sticky header.** With full
  manifest visibility the parameter list is long; a page-level scroll to reach
  a parameter in column 4 drags column 1's controls off screen. The sticky
  header keeps *which seats am I about to change* permanently visible, which is
  the single most important fact on this surface.

---

## 4. A column that resolves to no seats (Q2) — and a live safety defect

Two different situations get conflated here, and only one of them is benign.

**Benign: an empty group.** `liveCard` already has `empty-group`
(`facilitator.js:206`, `facilitator.css:30`). Keep the column, keep its header
and its target chips, render the parameter rows disabled, and state the reason
in one line: `Left · 0 seats`. Do not collapse to a bare `No Seats`
(`facilitator.js:343`) — that discards the target, which is the operator's
work, and leaves nothing to recover from. A column with nothing to drive is
still a column.

**Not benign: a pruned selector silently widens the column to All.**
`prune()` drops selectors the venue no longer has, and when nothing survives it
returns `["all"]` (`target-picker.js:280-283`). So if the seat or group a
column targets is deleted, that column **becomes an All column**. The fader at
that screen position, which drove one seat a second ago, now drives the whole
venue. There is no confirmation and no announcement.

Mitigations exist — the card header says `All Seats`, `.all-card` has a
stronger border (`facilitator.css:30`), the picker's terse readout changes — so
this is visible *if you look at the header*. Mid-show, with four columns, the
eye is on the fader. Probability is low (seats and groups are rarely deleted
during a show); cost is venue-wide and audible.

**Position: for the seat domain on the Control tab, prune-to-empty must not
fall back to `all`.** It should produce an inert column that names what it
lost — `seat 7 — no longer in this venue` with a `clear` action. Widening a
target is never a safe default; the safe default of a control that lost its
target is *doing nothing*. This is a small change in the column's picker
options (the component already supports `allowAll:false`,
`target-picker.js:281-287`), and I would ship it with `4` rather than let N
columns multiply the exposure.

---

## 5. Two columns showing the same seat (Q3)

**Do nothing. Do not dedupe, do not warn, do not badge.**

Ground-truth §4 is right that there is no state to diverge — both columns
project the same per-seat provenance through the same function
(`control-surface.js:275-287`). The remaining question was perceptual, and my
answer is that the perception is *the feature*.

Overlap is the console idiom: a channel appears on its own strip and under its
VCA, and when you pull the VCA you watch the strip fader move. That visible
coupling is how an operator learns what a group actually contains. Suppressing
it — hiding a seat from the All column because it is also shown alone, or
warning about overlap — would remove the only place the system ever shows its
own aggregation rule working.

It also makes §6's "editing unifies" legible for the first time. Moving a fader
in the All column is hard takeover of every member (contract §3.2,
design-language §6); today the consequence is invisible unless you go looking.
With two columns open you *see* the seat column's value snap to the group's.
That is the truth, shown at the moment it becomes true.

One piece of polish, offered as judgment and not as a requirement: make an
externally-originated value change *travel* rather than teleport — a ~120ms
transition on fill and marker when the change did not come from this control.
A jump reads as a glitch; a move reads as causation. It must not fight the
existing generator animation machinery (`facilitator.css:59-67`), so if it
cannot be done cleanly for automated rows, do it for manual rows only or skip
it entirely. It is not worth risking the modulation display for.

---

## 6. `followFocusSeat` with N columns (Q4)

**Not every column. Not none. Exactly one, opt-in, radio across the tab.**

If every column adopted the focus seat, one click on the Seats tab would
collapse a four-column arrangement — twenty seconds of chip-picking — into four
identical seat columns. That is destroying the operator's work with a click on
another tab, and it is not recoverable except by rebuilding.

If no column followed, the Seats → Control workflow that `37/10` deliberately
preserved dies quietly. That workflow is diagnostic: something sounds wrong,
find the seat on the map, go poke its parameters. It is worth keeping.

The console has solved this exactly: a **selected-channel strip**. Most strips
are fixed; one section follows whatever you select. So: a small latch in each
column's header (`⌖`, `aria-pressed`, latching radius per §8) meaning *this
column follows the Seats tab*. At most one column may hold it; latching it on
column B clears it on A. It persists with the column layout in localStorage,
and a fresh single-column layout has it **on**, so today's behaviour is the
default and nothing regresses for an operator who never adds a second column.
`07`'s rule that a picker adopts the focus when it *moves*, not on load
(`target-picker.js:289-299`), stays exactly as is.

Per-column storage key follows directly: `bopos.target.control.<columnId>`,
with the column id minted into the persisted layout. Ground-truth §2 notes the
`storage`-event delivery has to be replaced with a direct call once the
documents merge (`target-picker.js:365-367`); that is `3`'s work and it does
not constrain this choice.

---

## 7. What the brief did not ask, ranked by how much it will hurt (Q5)

### 7.1 The guarding is inverted, and N columns multiply the unguarded thing

This is the real risk in the design, and it is not capture.

| action | guard | audible | reversible |
|---|---|---|---|
| capture as step | 2 alerts + confirm (`facilitator.js:247-265`) | no | yes (undo stack) |
| **apply a preset** | **none** (`control-surface.js:413-418`) | **instantly, everywhere in the target** | **no** — provenance is overwritten |
| delete a preset | confirm (`:424`) | no | no |
| fire an event | none | instantly | n/a |
| device reboot/shutdown | 1200ms hold (`facilitator.js:414-419`) | yes | no |

Four columns means four identical preset `<select>`s on screen, each one click
+ one choice away from re-asserting a whole preset across a whole group, with
no confirmation and no undo. That is the mis-hit that ruins a performance, and
it is the one the design currently does nothing about.

I am not asking for a confirm on apply — a confirmation dialog in the audio
path is worse than the mistake. I am asking for three cheap things, and I would
put them in `4`:

1. **Wheel must never change a preset select.** With independent per-column
   scrolling the operator's pointer is over these controls constantly. Chrome
   no longer changes an unfocused `<select>` on wheel; a *focused* one and other
   engines are another matter. Bind a `wheel` handler that
   `preventDefault()`s on `.live-preset-select`, and put it in a browser guard.
   (I have not measured this in the app — flagging it as a thing to test, not a
   reported fact.)
2. **The apply report already exists** (`control-surface.js:291-311`); make sure
   it lands in the *column that applied*, and stays long enough to read. Today
   it is matched by exact member-set equality (`facilitator.js:73-79`), which
   means with overlapping columns an All-column apply can attach to whichever
   card covers the same set. Worth a look in `4`.
3. **Never place `remove column` next to a preset select or a fader.** See 7.3.

### 7.2 Nothing may move while a hand is on a control

`interacting` is currently a module global that suppresses the whole
re-render mid-drag (`facilitator.js:272-282`, `renderCards`'s
`if (interacting) return` at `:332`). When `2-control-column-component`
extracts instance state, there will be a natural pull to make it per column.

**Keep it tab-wide.** Per-column suppression means dragging a fader in column A
lets column B re-render under the operator's other hand — and with overlapping
targets, B is showing the value A is dragging. Freezing all four columns for
the duration of a drag costs nothing (the values are re-read the instant the
pointer lifts) and buys the single most important property of a performance
surface: it does not move while you are working it.

### 7.3 Layout actions are more dangerous than parameter actions

`+ column` and `× remove` change *where every control is*. That is worse than
sending a wrong value, because a wrong value can be dragged back and a moved
control cannot be un-learned.

- Adding a column appends to the right and **never resizes existing columns**.
  If the new column does not fit at the floor width, the strip scrolls
  horizontally. Fixed equal widths (§3) make this cheap; a re-flowing layout
  makes every add a small earthquake.
- Removing a column should not have a `×` sitting in the header where fingers
  live. Put it inside the column's own target picker disclosure — `remove this
  column` at the foot of the panel you already opened to re-target. Two
  deliberate acts, zero screen real estate, and it is exactly where the operator
  is when they are re-arranging. (A 1200ms hold, as
  `destructiveCommands` uses, is the alternative; I think it is heavier than
  this deserves — Bob's own argument for localStorage is that columns are cheap
  to recreate.)

### 7.4 Capture writes to disk during the show, and says nothing

`apply_show_mutation` persists and broadcasts on every mutation
(`server.py:1436-1456`). The Control page registers no `show` handler at all
(`facilitator.js:212-270` lists every handler), so a successful capture
produces **no feedback whatsoever** — success is silent, only failure alerts.
The inline `captured … · undo` confirmation in §2.4 is not a nicety; it is the
only signal the operator will ever get that the thing happened.

### 7.5 Column count is an attention budget, not a screen-space budget

Screen space allows seven columns at 2560 (§3). Attention allows about three.
I would not cap it — Bob operates this himself and a cap is a nuisance — but I
would make `+ column` slightly less prominent than `capture`, so the tab does
not read as an invitation to fill the screen. This is judgment, not evidence.

---

## 8. Layout sketch

At 1680, cap lifted, four columns, one following focus:

```
┌ tab rail ───────────────────────────────────────────────── Remote ─┐
├ tab strip ─────────────────────────────────────────────────────────┤
│  + column                                       capture step · 12/16│
└────────────────────────────────────────────────────────────────────┘
   ┌ column ────────┐ ┌────────────────┐ ┌───────────────┐ ┌─────────┐
   │ ▸ Left      ⌖ │ │ ▸ Right      ⌖│ │ ▸ 7         ⌖│ │ ▸ all  ⌖│
   │ ── sticky ─────│ │────────────────│ │───────────────│ │─────────│
   │ bonks   dusk ▾ │ │ bonks bloom ▾ │ │ bonks solo ▾ │ │ bonks ·· │
   │ [ 0.42 ][gain  │ │ [ 0.60 ][gain │ │ [ 0.42][gain │ │ [····][g │
   │ [ 220. ][pitch │ │ [ 180. ][pitch│ │ [ 220.][pitch│ │ [····][p │
   │ ▾ reverb       │ │ ▸ reverb      │ │ ▸ reverb     │ │ ▸ reverb │
   │   [ 0.30][mix ∿│ │               │ │              │ │          │
   │   ┌ drawer 320 ┐│ │               │ │              │ │          │
   │   │ LFO|loop|fd││ │               │ │              │ │          │
   │   └────────────┘│ │               │ │              │ │          │
   └────────────────┘ └────────────────┘ └───────────────┘ └─────────┘
        ↑ scrolls          ↑ scrolls        ↑ ⌖ latched      ↑ ground
          independently                       (follows Seats)   between
```

- One `capture step`, top right, with its live count. One `+ column`, top left,
  the two furthest-apart points on the strip.
- No `×` visible; removal lives inside the `▸ Left` picker disclosure.
- The `all` column overlaps all three others: its `gain` shows mixed dots
  (`·····`, §6) because Left and Right disagree. Pulling it unifies them, and
  the operator watches the other three columns move. That is correct.
- At 1280 the same layout carries three columns and the fourth scrolls into
  view; at 2560 the strip is centred with ground either side. Column widths are
  equal at every viewport.

---

## 9. Calibration — where I am least sure

- **Lifting the 1400px cap** is a tab-scoped exception to an app-wide rule, and
  `11-ground-and-card-audit` may reasonably want it back. I hold the position
  (an instrument is not a document) but it is a preference, not a finding.
- **The ~120ms travel transition** in §5 is polish I would drop at the first
  sign it destabilises the generator animation.
- **Wheel-over-select** (§7.1) I have not reproduced in this app. Test it before
  writing code for it.
- **The one thing I would not compromise on**: not the capture location, not
  the widths — the modal dialogs. Two `alert()`s and a `confirm()` on a live
  performance surface are indefensible whatever the answer to the ownership
  question turns out to be, and they should come out even if this consult is
  overruled in every other particular.
