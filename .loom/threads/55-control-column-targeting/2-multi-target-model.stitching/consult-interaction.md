# Consult — interaction / legibility altitude

Read against the running app (simfleet, 6 seats, 3 groups, 1440×900; shots
`A-multi-target.png` / `B-two-columns.png` in the parent stitch) and against
`control-column.js`, `control-surface.js`, `control-panel.css` §16/§18,
`control-column.css`, `preset_application.py`, `server.py:1830-2240`.

---

## 1. Recommendation

### Q1 — a column is one aggregate panel. Yes to (a), with one restriction and one refinement.

**Ruling asked for:** a column renders **one card** whose members are the union
of the selected entries' seats. `all` keeps its current collapse. Per-entry
cards go.

**Restriction (the hemming-in):** the picker forbids **heterogeneous**
selections — a column targets `all`, *or* one-or-more groups, *or* one-or-more
seats. Never a group and a seat together. That case is the only one where the
aggregate is actually incoherent: pick `Front` + `Seat 1` where Seat 1 is in
Front and the seat is in the union twice, its state is simultaneously "part of
the aggregate" and "the thing overriding it", and no readout can be honest.
`selectionMode()` (`control-column.js:331`) already computes this exact
discriminator and writes it to `data-live-view` — **which nothing anywhere
reads.** The predicate is written; give it a job.

**Refinement the brief and the stitch both miss — and the reason this costs no
wire change.** Aggregate the *display*; fan out the *send* per selected entry.
`apply_preset` and `set_live_param` stay `{scope, id}` and the column issues one
per entry. This matters beyond tidiness: `server.py:2130` coalesces an `all` or
`gN` apply into **one datagram per param**, and falls back to one per seat
otherwise. A genuine union-target verb would have to resolve to seats, so
targeting two 8-seat groups would go from 2 datagrams per param to 16. Sending
per entry keeps traffic proportional to *entries*, not seats, keeps D1's ruling
against widening the server vocabulary intact, and leaves `capture_target`'s
portable-selector derivation untouched.

One integration cost, named because it will bite: `presetReport`
(`control-column.js:142`) matches a report whose target set is **exactly** the
card's members. Two applies produce two reports, neither matching. The column
must merge the reports for the applies it issued — it already knows what it
sent.

### Q2 — a step is a preset reference plus deviation messages, produced by one algorithm with no special case.

Capture stays **venue-wide and argument-free**. For each cluster of seats
agreeing on (patch, preset), emit the `reference` as today **plus** `osc`
messages for the identities that differ from the stored document — which
`preset_dirty` (`preset_application.py:264`) already walks; return the differing
identities instead of early-returning `True`.

Then delete the special case: a seat with **no** preset is a cluster whose
reference is absent, so its deviation set is measured against nothing and comes
out as the full agreed state. Same code path, and consequence 3 in the brief —
*a state you dialled in by hand captures as an empty step* — stops being
possible. Traffic stays sane because `capture_target` still clusters those seats
into `all` / `group:<name>` before targeting them.

**Sub-question: no, capture does not let you pick values.** Capture records what
is. The filter already exists one level up, in the save drawer's include list.
If you want a step to carry less, save a preset that stores less. Two filters
would diverge within a month.

### Q3 — the state space, and how to show it

**Bob's four categories are one axis of three.** The real space is two
independent axes plus a fault axis, and the fault axis is currently invisible.

| axis | values | where it lives today |
|---|---|---|
| **anchoring** | unanchored · anchored · deviated | `applied_preset` + `preset_dirty` |
| **agreement** | agreed · mixed provenance · mixed values | `presetProvenance` / `aggregateValue` |
| **fault** | ok · schema drift · **preset missing from store** · **member on a foreign patch** | drift shows as `⚠`; the other two **do not exist as states** |

The fault row is a shipped defect, not a design gap. `refresh_preset_dirtiness`
(`server.py:1981`) sets `preset_dirty = True` when the preset file cannot be
read at all, and `preset_dirty` returns `True` when `marker["patch"] !=
effective_patch` (`:269`). So **three unrelated causes render as one appended
asterisk**: you moved a fader; the preset was deleted underneath you; this seat
is running a different patch and the apply was `skipped`. The first is normal
and desirable, the second means the thing you are about to capture cannot be
read, the third means the panel is describing a target it does not control.
`preset_dirty` should become a *reason* — `{deviated: N}` / `missing` /
`foreign-patch` — which is host state only, nothing on the wire.

**The glanceable question is not "is it dirty".** It is *would capture record
what I am hearing?* That is the workflow Bob described, and it orders the
anchoring axis into a scale an operator can read without thinking:

| state | glance | inspection |
|---|---|---|
| unanchored | **yes** — empty bar, dim name | — |
| anchored, clean | **yes** — solid bar, full ink | — |
| deviated, N params | **yes** — hatched bar, `dusk +3` | which params, in the menu |
| deviated *by automation* | **yes** — cyan hatch | — |
| mixed provenance | **yes** — hatched bar, `dusk & 2 more` | split the column |
| schema drift | glance-lite — existing amber `⚠` | what gets dropped/clamped |
| preset missing / foreign patch | **must be promoted out of `*`** — amber bar | reason in the menu |
| restart amnesia | **not on the column** — the capture control already owns it | — |
| offline members | already the dot | — |

**The treatment. Do not put a border on the column.** Three reasons: §18 states
"the column *is* the card" and deleted the old `.all-card`/`.group-card` border
tints precisely because a card that draws no border has none to tint — a tinted
column border re-creates what D1 removed; the state is per-target, so at N
entries a column border must average down to the least informative reading; and
a 1px perimeter is a peripheral channel that cannot carry three values plus a
fault.

Put it on the **preset row**, which is where the state is already claimed and
where `53-ui-niggles/3-preset-dropdown-menu` is about to rebuild the control
anyway. That stitch is the moment: it replaces a `<select>` (which cannot carry
a glyph, and ellipsises the marks — measured, it is `max-width:110px`) with a
disclosure whose **closed face is the state readout**.

```
   ┌──────────────────────────────────────────┐
   │ Front  ▪▪ g0+g1 · 4 Seats            ⋯   │   swatches = which groups
   ├──────────────────────────────────────────┤
   │ alpha        ▌ dusk                  ▾   │   anchored — solid bar
   │ alpha        ▞ dusk +3               ▾   │   deviated — 45° hatch, neutral
   │ alpha        ▞ dusk +3               ▾   │   deviated by generator — cyan hatch
   │ alpha        ░ no preset             ▾   │   unanchored — empty bar, dim
   │ alpha        ▌ dusk  ⚠               ▾   │   fault — amber bar + existing ⚠
   └──────────────────────────────────────────┘
```

**Every ink here already exists and already means this.** The 45° slash in
`--hatch` is the app's ratified "this readout does not fully describe what is
here" (a mixed param row); `--mod-hatch` is the same pattern in cyan when a
generator is involved (`mixed-mod`, `control-panel.css:520`) — which is exactly
the deviated-by-automation case, and is the ratified widened cyan, "something is
driving this". `--amber` is already the preset row's warn ink
(`.live-preset-drift:1175`). The `inset 3px 0 0 <ink>` left bar is already the
app's state-of-this-row idiom (`.show-step-row.active`,
`.device-row.patch-exception`). **No new colour meaning is proposed.**

Two rulings that fall out and must be taken explicitly:

* **`+N` collides.** D6 already uses `dusk +2` for *mixed provenance*. Ruling:
  `+N` always means *N deviated params*; a mixture reads `dusk & 2 more`. Under
  Q1's aggregate the mixture is much rarer, which is what makes the scarcer
  phrasing affordable.
* **The deviation count is the whole design.** `dusk +3` is self-explaining
  where `dusk *` is not, it is free from the Q2 change, and it is literally the
  payload the step will carry. Ship the count or the treatment is just a
  prettier asterisk.

### Q4 — patch switching

Not designed here. See §4.

---

## 2. What it forbids

* **A column targeting a group and a seat at once.** The only genuinely
  incoherent aggregate; the predicate for refusing it is already written.
* **Seeing two groups' values side by side inside one column.** Two groups at
  different values read `mixed` (hatched), not `0.3` and `0.7`. That is what
  two columns are for, and they are one click away.
* **A union-targeted verb on the wire.** No `apply_preset` over a seat list, no
  scope on capture. Both were argued and settled; nothing here reopens them.
* **Choosing which values a capture sends.** Curate the preset, not the step.
* **A step that silently records nothing.** Impossible after Q2.
* **A `*` that means three things.** After Q3 the operator's own edits and a
  broken reference cannot look the same.

## 3. The weak point

**The aggregate hides a real failure mode that per-entry cards made obvious.**
Target `Front` + `Back` where the two carry *different* presets: the panel reads
`dusk & 1 more`, hatched, and every parameter row hatches too. The operator now
has a column full of "it differs" and no way to see *what* it differs to without
changing the target. Today's three stacked cards, for all their height, answer
that at a glance.

I accept it because the honest resolution of a mixture is to **split it**, not
to paint it — and N columns is precisely that facility, shipped. But it is a
genuine regression for one workflow (compare two groups quickly), and if Bob
weights that workflow highly, shape (b) — aggregate with per-entry disclosure —
is the hedge, and the `+N`/`& N more` grammar above survives it unchanged.

The second weak point is smaller: **fan-out-on-send means N applies, and they
are not atomic.** One can succeed and one fail. Today's per-card applies have
the same property, so this is not a regression, but an aggregate *looks* like
one act and will be read as one.

## 4. What it needs from `34-fleet-patch-global-state`

Only one thing, and Q3 already builds the socket for it: **`effective_patch`
must stay per-seat and must stay visible through the aggregate.** The column
resolves its whole panel — declarations, preset catalog, drift — from a single
`state.live_controls.patch`, and today's silent handling of a member on another
patch (`apply_preset` counts it `skipped`, `preset_dirty` returns `True`) is
only survivable because it is rare.

If a step can switch patches, that stops being rare during the transition. So:
`34` must answer whether a seat's effective patch is per-device desired/reported
state or a fleet-wide fact, and until it does, **the fault axis keeps
`foreign-patch` as a first-class value** — an amber bar meaning "this panel is
describing targets it does not control", not an asterisk meaning "you moved a
fader". That is the whole ask. Nothing in Q1–Q3 assumes one patch per venue;
the aggregate assumes only that members it *drives* share the manifest it is
rendering, and the fault state is how it says when they do not.
