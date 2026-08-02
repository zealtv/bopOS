# Consult brief — Control columns, capture, and state legibility

You are advising **Bob**, who designs and operates bopOS: a Raspberry Pi + Pure
Data framework for networked multi-device sound installations. He has asked for
a UX/UI consultant who can work at **multiple altitudes** — interaction detail,
operator workflow, and system architecture — because the questions below are
coupled and he wants to rule on them once.

This is a **design consult, not an implementation task**. Do not write
production code. Your deliverable is a written recommendation Bob can ratify.

---

## The system, in one paragraph

A **venue** has **seats** (a seat is a logical position, bound to a physical Pi).
Seats can belong to **groups**. All the seats run the same **patch** (a Pure Data
program) which declares **params** (float/int/enum/string) and **events** in a
manifest. The **Control tab** in the dashboard holds N **columns**; each column
has a **target picker** (select `all`, groups, and/or individual seats) and
renders a control panel of every declared param. A **preset** is a named, sparse
set of param values stored per-patch (`patches/<patch>/presets/<slug>.json`);
applying one fans out ordinary `/p/<identity>` OSC messages. A **show** is a
document of ordered **steps**; each step holds **messages** that fire when the
step runs.

**Design values, stated by Bob and non-negotiable:**

* **Minimal traffic is the point of the system.** bopOS exists to send
  complicated states to many devices with little network traffic, so it scales.
  A design that emits hundreds of messages where tens would do defeats it.
* **Clarity beats flexibility.** Bob: *"The interface needs to work how you'd
  expect it to work, but it also might need to hem you in where that keeps the
  workflows clean and the systems architecture clean."* You are explicitly
  invited to **remove** affordances and forbid things.
* **0-indexing** on the wire and in the data model.
* The system works today and must keep working; prefer small ordered changes.

---

## Ground truth (verified in the code, 2026-08-02 — do not re-derive, but do
## challenge if you think it's wrong)

**Columns.** `control-column.js:368-376` does `selection.map(selectedCard)` — a
multi-entry selection renders **one card per selected entry**, stacked in a
342px-wide column. The exception is `all`, which collapses to a single
`All Seats` card. This was an explicit ruling in `07-target-selector-component`
(2026-07-30).

**Aggregation already exists.** `liveCard(scope, item, members, …)` takes a
member list, and `aggregateValue` (`control-surface.js:80`) already reduces N
seats to one control with a `mixed` state, a mixed hatch, and mixed automation.
An `All` card and a group card have always been "one panel, N seats". So "one
panel over an arbitrary selection" is not new machinery.

**A step holds two message kinds** — `MESSAGE_KINDS = frozenset(("osc",
"reference"))` (`show_model.py:34`). An `osc` message is address + args +
target. A `reference` is a preset pointer: `{"kind":"reference", "address":
"/preset/<patch>/<slug>", "args": [], "target":[...], "reference":{"content":
{"name","fingerprint"}, "schema"}}`. **Both shapes already work.** Nothing under
discussion requires an OSC contract change.

**What "Capture as step" does today** (`server.py:1830`,
`_captured_show_preset_messages`): walks every seat venue-wide, reads its
`applied_preset` marker, clusters seats by (patch, preset name), and emits ONE
`reference` message per cluster with `args: []`. Consequences, none visible on
screen:

1. It captures a **pointer, not a state**. Values are resolved at playback from
   whatever the preset file holds then.
2. **Hand-tweaks are silently dropped.** The panel shows a dirty marker; capture
   emits the unmodified reference.
3. **A seat with no preset applied captures as nothing at all** — it is `continue`d
   over. A state you dialled in by hand produces an EMPTY step.

Capture is deliberately **venue-wide and argument-free** — `4-n-columns/2-venue-wide-capture`
removed `scope`/`id` from the wire on the grounds that a per-column scope
captured the wrong thing for three of five column shapes, and the arrangement is
rebuilt from per-seat provenance anyway. `capture_target` derives the most
portable selector (all / `group:<name>` / seat ids) for any concrete seat set.
**Do not casually re-widen this; that argument was had and settled.**

**Two different sparsity mechanisms — this distinction is load-bearing:**

* *Mixed* sparsity (`capture_params`, `preset_application.py:206`): when target
  seats **disagree** on a param, store nothing for it and report it as omitted.
  This is how presets are sparse today. Note it gives **no** saving when a
  column drives one group whose seats agree — which is the common case.
* *Deviation* sparsity: only params that differ **from the applied preset**.
  This is the one that buys traffic. `preset_dirty` (`preset_application.py:264`)
  already walks param-by-param comparing seat state against the preset document,
  early-returning `True`; returning the differing identities instead yields the
  sparse payload for free.

**There is no way to choose which params a preset stores.** Preset save captures
everything the targets agree on. The "N omitted as mixed" note in the save drawer
is mixedness, not choice.

**Shows cannot switch patches.** A show's only patch awareness is the
`name + fingerprint` recorded inside a `reference`, used for non-blocking drift
warnings (`show_model.py:315`). There is no patch-loading step or message.

**Drift/dirtiness surfaces today** as an appended `*` (dirty) and `⚠` (drift) on
the preset dropdown — and `53-ui-niggles/3-preset-dropdown-menu` already exists
because appending them to a native `<select>` ellipsises exactly the marks that
matter.

**A new column defaults to `["all"]`** (`control-host.js:210`).

---

## The questions

### Q1 — What is a column?

One target, or an aggregate over a multi-entry selection? Bob's own reading:

> shouldn't it remain as a single control panel, that is targeting all seats
> from its target picker?

and later, appraising the interface in use:

> I can see a world where it is perfectly fine that the target picker only picks
> one thing, be it a group or all or an individual seat. It certainly would be
> convenient to be able to pick multiple things, but I think there may be a
> world in which the simplicity of targeting a specific target may improve
> clarity.

Shapes on the table: **(a)** pure aggregate over the union; **(b)** aggregate
with per-entry disclosure; **(c)** keep card-per-entry; **(d)** restrict the
picker to a single target entirely (Bob's newest option — note that the
aggregate case subsumes it, so this is a *hemming-in* choice, not a capability
choice). Costs of aggregation: per-seat state with nowhere to go (online/offline
dot, `empty-group`, per-card overflow), and two groups at different values read
as `mixed` rather than as two legible values.

### Q2 — What is a step?

Bob's stated intuition: *"you would create a state using the control tab and then
click capture to step and everything in that state would get captured to a step,
and that would include deviations from the preset."* He also ruled that the
preset-with-modifications affordance **should exist**: *"this affordance probably
should be there. It's what feels natural when using the interface."*

Candidate shapes: preset reference (today); flattened values; **preset reference
+ deviation messages** (currently the recommended shape, because it is sparse by
construction); auto-generated presets written at capture time (Bob raised this —
note the objections: it pollutes the preset dropdown on every Control card, and
`presets/` travels with the *patch*, not the show, so a show becomes
non-self-contained).

There are **no existing shows**, so migration is not a constraint and late-binding
behaviour can be chosen freely.

Sub-question Bob raised directly: should capture let you **pick which values are
sent**? If so, does that same affordance belong on preset save, so the two don't
diverge?

### Q3 — The state taxonomy, and how to show it

Bob, verbatim:

> I think part of this comes back to it being clear when a preset is dirty. I
> think we might need a clearer visual representation of that — that is much
> clearer. So we might need a border around the column indicating that column's
> current state. Is it a preset? Is it a preset with changed values? Is it not a
> preset at all? Is it mixed? What different categories are here? And how do we
> most clearly show that on the interface?

**Enumerate the actual state space** (do not assume Bob's four are complete —
consider at least: no preset ever applied; clean preset; preset with deviations;
targets disagree on which preset; preset missing from the store; patch/schema
drift; automation running on top of a preset), decide which distinctions an
operator must see **at a glance versus on inspection**, and design the treatment.
The border-on-the-column idea is Bob's suggestion, not a constraint.

Existing design language you must work within: the app is a compact grayscale
scale with **cyan = modulation**, widened by ratified decision to "something is
driving this, continuously or discretely". Read
`.loom/legacy-v1/tied/1-columns-design/decisions.md` and the design-language
sections referenced in `CLAUDE.md` before proposing new colour meaning.

### Q4 — Patch switching, as future load

Bob:

> down the line I can see it's going to be important for us to be able to change
> patches… I could see us running with a particular patch for say thirty minutes,
> and then after a divider, loading another patch and running through a new set
> of presets with new changes.

This is **not yours to design**. The foundational question — is "the fleet patch"
a first-class concept or a projection of per-device desired/reported state? —
belongs to `feature-backlog/34-fleet-patch-global-state`. Your job is to make
sure your answers to Q1–Q3 **do not foreclose** it, and to state plainly what
they need from it. A step that switches patches implies every param, preset and
target reference in later steps resolves against a different manifest; say what
that does to your model.

---

## How to work

* Read the code you are reasoning about. Key files: `dashboard/server.py`,
  `dashboard/preset_application.py`, `dashboard/preset_store.py`,
  `dashboard/show_model.py`, `dashboard/static/js/control-column.js`,
  `control-host.js`, `control-surface.js`, `show.js`, `show-capture.js`.
* Read the prior rulings before reversing one:
  `.loom/legacy-v1/tied/1-columns-design/decisions.md` (nine ratified decisions,
  D1 and D5 especially), the `07-target-selector-component` record, and
  `4-n-columns/2-venue-wide-capture`. If you reverse one, say so explicitly and
  say why the original reasoning no longer holds.
* You may run the dashboard against the simulated fleet to look at the real
  thing: `tools/simfleet.py` + `dashboard/server.py` on non-default ports; the
  worked harness is
  `.loom/threads/55-control-column-targeting/repro-columns.py`, and
  `tests/verify_control_tab.py` is a living example. Venv is `~/.venvs/bopos`.
  **Do not modify any `.pd` file — Pure Data is Bob's domain.**

## Deliverable

A single markdown document, max ~1200 words of prose plus whatever tables or
ASCII sketches earn their place. Structure:

1. **Recommendation** per question, stated as a decision Bob can say yes/no to.
2. **What it forbids.** Bob asked to be hemmed in; name what your design makes
   impossible and why that is worth it.
3. **The weak point.** The single strongest argument against your own
   recommendation.
4. **What it needs from `34-fleet-patch-global-state`**, in one short section.

Prefer one clear recommendation over a survey of options. Where you disagree
with the framing in this brief, say so — the brief is an input, not a spec.
