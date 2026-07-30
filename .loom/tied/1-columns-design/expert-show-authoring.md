# Expert consult — the show-authoring / document-semantics lens

**Lens:** what a captured artifact *means* when it is replayed later, possibly
in another venue, possibly months later, possibly by someone else. Reference
points: DAW scene capture, lighting cue stacks, version-controlled documents.

**Method note.** Everything asserted about behaviour below was read off `main`
at 2026-07-31 and is cited file:line. Where I am giving professional judgment
rather than reporting code, I say so in the sentence. I verified ground-truth
§4 and §5 independently; both hold, including the correction in §6 — an
all-column capture needs *no* widened server vocabulary. The stitch
instructions are wrong on that point and the design should not be shaped around
it.

---

## 1. The primary question: per column, whole tab, or neither

**My answer is "neither — capture is venue-wide", and I want the `scope`
argument deleted rather than re-pointed at a column.**

Not as a compromise. The venue reading is the only one of the three that
corresponds to something the document can actually say.

### 1.1 Provenance is a total, single-valued function over seats

`applied_preset` is stored on the seat (`server.py:2176-2178`) and is
single-valued: applying a preset to a seat overwrites whatever marker it had,
and choosing none clears it (`server.py:2051-2053`). Every seat in the venue
therefore has exactly zero or one preset marker at any instant, and the set of
markers over all seats *is* the arrangement. `_captured_show_preset_messages`
(`server.py:1838-1878`) reads exactly that: it groups seats by marker, and for
each distinct marker asks `preset_application.capture_target`
(`preset_application.py:246-261`) for the most portable selector shape covering
that seat set — `all`, else an exactly-matching `group:<name>`, else explicit
seat ids.

A column is a viewport onto that function. It is not an owner of any part of
it, and it cannot be, because two columns may cover the same seat (ground-truth
§4, `control-surface.js:276-286`). So:

- **Per-column capture** = the venue arrangement, restricted to the seats one
  viewport happened to be pointed at. A lossy filter over a total function.
- **All-column capture** = the venue arrangement, restricted to the union of
  the viewports, with the overlaps collapsing back to the same per-seat facts.
  A *less* lossy filter over the same total function, with one extra vice: the
  filter changes when you add a column to look at something. Opening a viewport
  is not supposed to change what gets saved.
- **Venue capture** = the function itself.

The two column-derived readings differ from the venue reading only by
*subtraction*, and they subtract on a criterion — "what I had on screen" — that
the resulting document does not record and cannot recover. That is the
disqualifying property. Whatever a step means, it should not mean "the parts of
the room the author had open in a panel on the afternoon they pressed the
button."

### 1.2 "But then how do I capture only part of the room?" — F3 already does that

This is the real objection to venue-wide capture and it is already answered.
F3 (ratified, `1-preset-architecture-design/decisions.md`) omits targets with
no preset applied. A venue where four of twelve seats are in play for this piece
has provenance on four seats and nothing on the other eight, so a venue-wide
capture emits messages for the four. **F3 is the scoping mechanism.** The
`scope` argument is a second, worse one layered on top of it.

Worse how: `scope:"groups"` drops every seat that belongs to no group
(`server.py:1809-1811`), including seats that *do* have a preset applied. That
is a filter that removes real content on a criterion the operator never stated
— they picked a group chip in a picker, they did not ask for un-grouped seats
holding presets to be excluded from the document. Ground-truth §5(b) is right
that the scope filter is nearly inert; I would go further and call
`scope:"groups"` an active defect in the authoring loop, independent of columns.

### 1.3 The WYSIWYG question, answered honestly

The brief asks the sharpest version: if the step is reconstructed from venue
state rather than from what the operator selected, is the document what they
believed they were capturing? My answer: **no, it is not — but narrowing the
capture to a column makes that worse, not better, because the panel's own
display is lossy in both directions.**

Concretely, the card projection is agree-or-mixed
(`preset_application.py:235-244`, mirrored client-side at
`control-surface.js:276-286`): if a card's member seats do not all carry the
identical marker, the card reports `mixed` and shows **no preset name at all**.
So an All column over a venue holding `dusk` on the left and `bloom` on the
right displays one word — "mixed" — while a capture of that same target mints
two named, portable messages. What is on screen is strictly *less* than what is
captured.

In the other direction, `total` in the confirm dialog counts seats
(`server.py:1815-1821`), including seats the operator has never looked at and
seats with no bound device, and the dialog calls them "targets"
(`facilitator.js:260-264`) — a word the UI otherwise uses for picker chips and
cards. An operator looking at one All card is told "3 of 12 targets have a
preset applied." Twelve of what? Nothing on screen is twelve.

Both mismatches exist **today, with one column**. They are not caused by N
columns and they are not fixed by choosing a column-shaped scope. The fix is to
raise the fidelity of the moment of capture, not to lower the reach of the
capture. That is §2.1.

### 1.4 The document cannot tell you which reading was used

`capture_preset_step` hardcodes the step's alias to `"Captured presets"`, a
5.0 s duration, one play, then stop (`show_model.py:873-881`), and appends it at
the end of `items`. Nothing in the persisted step records the scope that
produced it, which columns existed, or what was omitted.

So the per-column/whole-tab choice is **invisible in the artifact**. Three
captures in an afternoon produce three steps identically named "Captured
presets", distinguishable only by their pills (`show.js:372-375`,
`messageLabel` at `:81-88` — the pill shows the preset name, which is at least
something). Six months later the difference between a step captured from the
"Left rig" column and one captured venue-wide is unrecoverable.

My judgment: a distinction that the document cannot express should not be a
per-invocation operator choice. Either it is a property of the tool (one
behaviour, always) or it must be written into the step. I recommend the former,
and separately recommend fixing the naming (§2.2), which is a defect regardless
of how the primary question is ruled.

### 1.5 The recommendation, precisely

1. **One capture action per Control tab**, not per column. It lives in the
   tab's own chrome — above or beside the column strip, on the ground — never
   inside a column's card. A capture button inside a column asserts, by
   placement, that the column is its subject; it is not.
2. **`scope` and `id` leave the wire.** `preview_show_preset_capture {}` and
   `capture_show_preset_step {}`. `_capture_show_seats` (`server.py:1804-1812`)
   collapses to `list(self.state.seats.values())` and can be inlined;
   `presetScope()` (`facilitator.js:381-397`) is deleted outright. Per
   ground-truth §6 this is a **removal**, not a widening — the arrangement was
   never carried by the scope.
3. **Label it for what it does.** `Capture arrangement…` — the ellipsis is the
   standard "this opens something, it does not commit" signal, which today's
   button badly needs given that it fires two possible `alert`s and a
   `confirm` (`facilitator.js:247-265`).
4. **Narrowing happens after capture, in the document.** A captured step's
   messages are individually selectable and deletable in the Show tab; deleting
   `PRE bloom` from a captured step is one focus and one delete, performed
   where the author can see the pills they are keeping. This is the DAW/lighting
   model: capture the whole stage, prune in the arrangement view. Selective
   record exists on lighting desks, but it is an explicit expert path with its
   own modifier — never an implicit inheritance from whatever the operator had
   selected.

**What it costs.** You lose the ability to pre-narrow to one seat
(`scope:"seat"` is the only genuinely narrowing case today). In exchange the
narrowing moves to a surface with evidence on it. I regard this as a net gain
for authoring and a small, real loss for a specific live habit — the
live-operator lens may weigh that differently and should say so.

If Bob wants pre-narrowing back later, the right shape is **checkboxes in the
capture preview** (§2.1), one per message the server would mint, defaulting to
all checked. That is selective record with the selection visible, and it needs
no scope vocabulary either — the client sends back the subset of markers it
wants, or the server keeps minting everything and the client deletes. Do not
reintroduce it as a view-derived scope.

---

## 2. Three fixes the capture loop needs regardless of how §1 is ruled

These are all cheap, all inside the capture path, and all matter more to the
authoring loop than the column question does. I would ratify them alongside it.

### 2.1 Replace the confirm with a preview of the messages

Today: `show_preset_capture_preview` returns `{applied, total, omitted,
show_loaded}` (`server.py:1814-1822`) and the client renders that as up to two
`alert`s and one `confirm` sentence (`facilitator.js:247-265`). Counts only.
The operator confirms a document they have not seen.

The server already computes the messages. Have the preview return them (or a
projection: preset name, resolved target label, portable/site-bound, dirty) and
render a small non-modal panel:

```
Capture arrangement — 3 messages, 4 seats omitted
  PRE  dusk    → group “Left”          portable
  PRE  bloom   → group “Right”         portable
  PRE  solo    → seats 7, 9            site-bound *
  —    (none)  → 4 seats               not captured
                                   [ Cancel ]  [ Capture ]
```

This is the whole WYSIWYG fix. It does not narrow the capture; it makes the
reconstruct-from-state result visible at the one moment that decides whether
the artifact is what the author believed. It also satisfies F3's ratified
requirement ("the button states the count before committing") strictly better
than a count sentence does, and it is where the portability and dirtiness
warnings below have a place to live.

Blocking `alert()`/`confirm()` on a surface an operator drives mid-show is
independently poor; I expect the live-operator lens to want them gone too.

### 2.2 A captured step must be nameable at capture time

`"Captured presets"` for every step (`show_model.py:876`) is the single worst
thing about the current artifact from my lens. Minimum: derive an alias from
the content — `dusk + bloom + solo`, truncated — so two captures are
distinguishable in the step list without opening them. Better: mint the derived
name, append, and put the new step's name into the Show tab's existing
click-to-edit rename state (`show.js:95-111`) so the author names it while they
still remember what it was. Naming a cue when you record it is table stakes in
every cue stack I know.

### 2.3 Capture currently succeeds silently

`capture_show_preset_step` → `apply_show_mutation` persists and broadcasts
`show` (`server.py:1428-1453`). The Control surface registers no `show` handler
at all (`facilitator.js:212-267`) — only `error`, which alerts. So the operator
confirms, and *nothing observable happens on the tab they are on*. There is no
way to tell a successful capture from a swallowed one, or one capture from
three, without switching to the Show tab.

Once the iframe is retired (`3`) the Control tab is in the same document as the
Show tab, so this is trivially fixable: a transient confirmation naming the step
that was appended, ideally clickable through to it. An authoring loop with no
completion signal is not a loop.

---

## 3. What the captured step means when it is replayed elsewhere

Three portability hazards, all present today, none of them addressed by the
column question but all of them worsened by capturing more often (which N
columns will encourage).

**(a) Site-bound targets are minted silently.** `capture_target`
(`preset_application.py:246-261`) falls through to explicit seat ids whenever a
preset's seat set is neither the whole venue nor an exact group match. Ratified
R3 (`2-workflows-and-simplification/proposal.md:126-129`) says seat-id targets
stay legal but "the Show tab should treat them as site-bound and say so." Today
nothing says so — there is no such marking anywhere in `dashboard/`. Capture is
the main *producer* of seat-id targets, so the honest place to say it first is
the capture preview (§2.1), with the Show tab's message row echoing it. This is
a small, ratified-but-unbuilt obligation and this stitch is the natural moment.

**(b) Group promotion is exact-match, and ties break arbitrarily.**
`capture_target` matches a group only when its membership *equals* the captured
seat set, and on multiple matches takes `min(matches)`
(`preset_application.py:255-260`). Two coextensive groups ("Left" and
"Downstage") capture as whichever has the lower id — a decision the author never
made and cannot see afterwards, since only the chosen name is stored. The
preview panel makes it at least visible; I would not add a disambiguation UI for
it now.

**(c) Replayed overlap is order-dependent, and the order is alphabetical.**
Within the capturing venue the emitted messages cover disjoint seat sets (each
seat has one marker). That disjointness is a *venue-time* property, not a
document property. Replayed in a venue where `group:Left` and `group:Right`
share a seat, both preset messages hit that seat, and the winner is whichever
is emitted last — that is, the later of the two in `sorted(grouped.items())`
(`server.py:1853`), i.e. alphabetical by `(patch, preset name)`. `show_engine`
emits step messages in list order with hard takeover
(`show_engine.py:146-165`), so nothing downstream re-derives it. Alphabetical
preset-name precedence is not a semantics anyone would choose. I am not asking
this stitch to fix it; I am asking that it be written down as a known property
of captured steps, because it is exactly the class of thing that surfaces as
"the show sounds wrong at the new venue and nobody can see why." A
`namedTargetWarnings`-style overlap warning at load time (`show.js:259-269` is
the obvious host) is the eventual fix.

---

## 4. Positions on the other five

### 4.1 Column widths, and the 1400px cap

**Fixed at the measured floor. Not resizable. Drop the cap on this tab.**

The panel's content is a 320px instrument face that never reflows
(`control-panel.css:145-149`, the `06`/`06b` rulings). Widening a column adds
whitespace inside a card; narrowing is not an option. So a resize handle offers
the operator a control over a variable with no consequence — and worse, it
invites them to encode meaning in geometry ("the wide one is the important
one") that no persisted artifact records. Per-column geometry also inflates the
localStorage layout from an ordered list of targets into a list of
target+width, which cuts against Bob's own argument for localStorage ("it
should be easy to spin up whatever control panel targets one needs" — cheap
re-creation, so keep the state cheap).

`.tab-panel{max-width:1400px}` (`style.css:44`) is a reading-measure constraint
and it belongs on the form-shaped tabs. A column strip is an instrument rack;
capping it at three columns on a 2560px display is arbitrary. My call: the
Control tab overrides to `max-width:none`, columns keep their fixed width, and
the strip scrolls horizontally past the viewport. Horizontal scroll is the
right failure mode here for the same reason it is the right one inside the
panel (`control-panel.css:145-149`): scroll an intact face rather than rearrange
it.

I expect the calm-ops lens to defend the cap on scanability grounds. My counter:
the cap does not improve scanning of a rack, it just hides the fourth
instrument; and unlike prose, columns have no measure to respect.

### 4.2 A column whose target resolves to no seats

**Two different failures, and the code currently conflates them in the
dangerous direction.**

- *Emptied group* (group exists, membership is now zero): keep the column,
  render the `empty-group` card state that already exists
  (`facilitator.js:206`), say "0 seats — this column controls nothing", and
  disable the controls. Honest and stable.
- *Deleted group or deleted seat*: `prune` drops the unknown selector, and if
  nothing survives it **returns `["all"]`** (`target-picker.js:271-287`, the
  fallback at :283) — then `resolve` persists that
  (`target-picker.js:300-309`). So a column that targeted one deleted seat
  silently becomes a column targeting **the entire venue**, and the operator's
  original intent is gone from localStorage with it.

That is unacceptable on a live control surface, and from my lens it is also a
capture hazard: silent target widening is the mechanism by which "what I
thought I was operating" and "what the state actually says" diverge. My
position: the Control host's prune must not fall back to `all`. A column whose
selection prunes empty becomes an **untargeted column** — it keeps its slot and
its position, renders "target no longer exists · choose a target", and disables
its controls until retargeted. Parameterise the fallback per host; the Assets
tab's advance-to-next-eligible behaviour is deliberate and must be preserved
(`target-picker.js:266-270` explains why).

Note how much simpler this is once capture is venue-wide: nobody has to answer
"what does the capture button on an empty column do?"

### 4.3 Overlapping columns and the applied-preset marker

**Do nothing about the overlap. Fix the projection instead.**

Ground-truth §4 is correct: provenance is per seat, dirtiness is derived
(`preset_application.py:264-292`), so two columns cannot disagree about a fact
— they can only render the same fact twice. Two true statements are not a
contradiction, and I would not add dedup, a "primary column", or cross-column
highlighting. All three would be machinery invented to solve a problem that
does not exist.

The one thing that *reads* like a contradiction is agree-or-mixed: an All
column saying `mixed` beside a group column saying `dusk *`. The All column is
not wrong, it is uninformative. Make `mixed` carry its content — `dusk +2`, or
`3 presets` — and the apparent conflict evaporates. This shares its data with
the capture preview (§2.1) and is the same underlying fix: the panel currently
throws away the arrangement that capture reconstructs.

### 4.4 `followFocusSeat` with N columns

**None of them. Retire `followFocusSeat` on the Control host and replace the
workflow with an explicit affordance.**

Today the Control picker is the only consumer of the flag
(`facilitator.js:105`; no other caller sets it), and adoption is a destructive
write: `adoptFocusSeat` replaces the whole selection with `[seat]` and persists
it (`target-picker.js:289-299`). With one panel that was tolerable — there was
no view state to destroy. With N columns, a Seats-tab click that reaches in and
rewrites a column's target destroys authored state, immediately and durably,
and there is no undo. Rewriting *every* column is worse still: one click on
another tab silently retargets the whole instrument rack.

The Seats→Control workflow's actual intent is "get me to this Seat's controls."
With N columns there is a better expression of it: an explicit **"Control this
Seat"** action on the Seats tab that (a) focuses an existing column already
targeting exactly that seat if one exists, else (b) appends a column targeting
it, then switches to Control and scrolls it into view. Explicit, additive,
non-destructive, and it produces the arrangement the operator wanted rather than
mutating one they built.

Ground-truth §2 notes the `storage`-event delivery is being rewritten by `3`
anyway, so no plumbing is preserved by keeping the current rule. `07`'s ruling
that the focus seat is one shared key stands and is untouched — this changes
who *reacts* to it on Control, not where it lives.

### 4.5 The real risk, which the brief did not ask about

**Capture reads a volatile, invisible layer, so the step is a function of
session history rather than of what the room sounds like.** Two failure modes:

1. **Restart amnesia.** `applied_preset` and `preset_dirty` are explicitly
   stripped before persistence (`state.py:420-427`) — runtime-only, like
   automation. Seat *params* persist. So after a dashboard restart the venue
   sounds exactly as it did, every fader is where it was, and
   `Capture arrangement` reports "0 of 12 targets have a preset applied; there
   is nothing to capture." Nothing on screen explains why, because the thing
   that vanished was never visible as a thing — only as a name in a dropdown.
   This is the purest form of "what you saved is not what you thought", and it
   is invisible until the moment you need it.

2. **Dirty capture is lossy in the sonic dimension.** F4 stores provenance and
   derives dirtiness; capture takes markers "dirty or not — the asterisk is a UI
   truth, not a capture rule" (`1-preset-architecture-design/proposal.md:348-351`),
   and `preset_dirty` never enters `_captured_show_preset_messages`
   (`server.py:1838-1878`). So: you spend an hour past a preset dialling in the
   room, you capture, and the step reproduces the *preset* — not the hour. The
   `*` is on screen, but the confirm dialog does not mention dirtiness at all
   (`facilitator.js:256-265`). The workflow in which an operator most wants to
   save what they hear is precisely the one where capture silently saves
   something else.

Both are ratified behaviour and I am not asking to reopen F3 or F4. I am asking
that the capture surface stop being silent about them:

- The preview (§2.1) marks dirty rows explicitly — "captured as `dusk`; edits
  made since are not included" — and offers the obvious next action, *save
  these values as a preset first*, inline.
- The "nothing to capture" path says *why* it is empty when the venue plainly
  has values: "no preset provenance in this session (provenance is not kept
  across a dashboard restart)". A different sentence for a different cause.

I would rank both of these above every column question in this stitch. Columns
change where a button sits; this decides whether the artifact is true.

---

## 5. Where I expect to disagree with the parallel lenses

- **vs. live-operator, on per-column capture.** I expect that lens to prefer a
  capture button in each column: it is closer to the hand, it matches "I am
  working in this column right now", and it needs no reading. I would accept
  every one of those points as true about the *gesture* and still refuse it,
  because the gesture's convenience is paid for by the artifact, and the
  artifact outlives the gesture by months. If the live lens wins on ergonomics,
  the compromise I would accept is one capture button per column that all
  perform the *same venue-wide capture* — placement follows the hand, semantics
  stay singular. What I will not accept is N buttons with N different meanings.
- **vs. live-operator, on the confirm dialog.** I want a preview panel; that
  lens may want capture to be one keystroke with no dialog at all. I think we
  converge: a non-modal preview that can be committed with `Enter` is faster
  than today's `confirm()` and honest as well. Blind one-shot capture I would
  argue against, on the "restart amnesia" and "dirty capture" grounds in §4.5 —
  those are exactly the cases where a silent capture produces a wrong document
  and nobody finds out until the next venue.
- **vs. calm-ops, on the 1400px cap.** Stated in §4.1. I want it dropped on
  this tab; I expect that lens to keep it.
- **vs. calm-ops, on "how many capture buttons before none is obvious."** We
  agree on the conclusion (one), and I want the reasoning on record as *not*
  primarily about button count. Even if a single column somehow made N buttons
  legible, per-column capture would still be wrong, for §1.1.

---

## 6. Summary of positions

| # | question | position |
|---|---|---|
| — | capture ownership | **Neither column nor tab: venue-wide.** Delete `scope`/`id` from the wire; F3 is the scoping mechanism. One `Capture arrangement…` action in the tab's chrome, never inside a column |
| — | capture confirm | Replace the two alerts + confirm with a **preview of the messages to be minted**, marking omitted, dirty, and site-bound rows |
| — | captured step name | Derive from content and open the existing inline rename; never ship N steps named "Captured presets" |
| — | capture feedback | Confirm the appended step on the Control tab; today it succeeds silently |
| 1 | column width | Fixed at the ~340px floor, not resizable; **drop `max-width:1400px` on the Control tab**, strip scrolls horizontally |
| 2 | empty target | Emptied group → keep the column, `empty-group` state, controls disabled. Deleted group/seat → **untargeted column**; kill prune's `["all"]` fallback for this host — never silently widen a target |
| 3 | overlapping columns | Nothing. Render the same fact twice; make `mixed` informative (`dusk +2`) instead |
| 4 | `followFocusSeat` | **None.** Retire it on Control; replace with an explicit "Control this Seat" action that focuses or appends a column |
| 5 | real risk | Provenance is runtime-only (`state.py:420-427`) and dirty state is not captured — the capture surface must say both out loud |
