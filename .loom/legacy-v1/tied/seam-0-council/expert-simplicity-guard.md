# Seam council — the simplicity guard's response

## 1. Lens & altitude

I am the seat that asks *how much of this is real*. My altitude is one level
above the wire sketches: I judge which of the three sub-problems is a genuine
seam fix, which is a small additive feature, and which is speculative
generality wearing an architecture costume. I chose this altitude because the
instigating event was tiny — spatial-0 was **one function composing a multiply
in the wrong place** — and the risk in this room is that five experts answer a
scoping error with five redesign programs. My job is to keep the total diff
small enough that Bob can still hold bopOS in his head.

## 2. Problem reframing — and the honest size

The candidate principle ("bopOS provides a subscribable OSC surface; the patch
enacts it; nothing enforced but mute") is **not a new principle**. It is the
already-ratified constitution: contract §3 says `/p/*` is "the only place output
semantics live," framework planes are a closed set, and §6/§14 already carve
mute out as the single framework-owned output verb. So the council must not
"ratify the principle" as if it were new — that re-litigates 2026-07-07. The
principle is settled; the task is to find the **places where code violates it**
and apply the smallest correction.

There are exactly two such places, and they are the same shape:

- **Spatial (spatial-0):** bopOS streamed a computed scalar *into the patch's
  volume param*. Already agreed wrong; S1 fixes it.
- **Master gain:** the dashboard composes `mix × master` and sends the *product*
  as the volume param (`osc_bridge.py:139-143`, re-sent by `resend_volumes`
  146-153, catch-up at 237-241). The patch never sees master.

Count the master "type case": about **a dozen lines** across two methods. That
is the measure of the actual mistake. It is not an architecture; it is a
misplaced multiply, exactly like spatial-0. The right response is therefore a
small *contract sentence* that names the seam so both violations — and the next
one — are caught, plus one real code fix (S1) and one deferred design (master).

**Total redesign size: less than the other seats will propose.** One
already-agreed backend fix, one additive manifest field, one contract
paragraph, and two explicit deferrals with named un-defer triggers.

## 3. Proposed design — the smallest coherent fix

### The one load-bearing idea: *provided scalars*

Unify spatial-proximity and master into a single primitive the contract already
almost describes: **a named, full-state scalar bopOS provides, the patch
subscribes to by name and maps wherever it likes, upstream of its own output.
bopOS never composes it into a patch param.** Spatial S1 is already forcing this
exact convention into PD patches ("helper delivers a 0→1 value, the patch maps
it upstream of volume"). Master is the *same shape*. Naming them as one concept
is the whole payload — it deletes the special-case and it is the sentence that
would have caught spatial-0.

### (1) Master — designed now, **shipped never as a standalone migration**

Move `mix × master` off the wire *only when it can ride the S1 PD-edit event*.
Rationale, in guard terms: three of the four reasons spatial-0 was wrong do
**not** apply to master — it is low-rate (only on master move), single-cardinality
(one master is correct), and a master gain genuinely *is* a level scalar, not an
alien value forced onto volume. The one reason that does apply (the patch can't
see master) is needed by **zero current projects** — Kite Choir and Playable
Streets are stereo gain-only. Moving it costs a PD-receiver edit on every
deployed patch (Bob's domain, §23) and buys nothing today.

So: dashboard-side composition **stays as-is now**. Design the target — master
becomes a provided scalar (`/all/...`, spelling deferred to Bob) the patch
multiplies internally — and let it land the day a patch needs it, folded into
the spatial receiver work so patches take *one* PD-edit event, not two. Refuse
the tempting middle path of broadcasting master raw *and* keeping the composed
product: that is two sources of truth for one value — a second surface, exactly
what I guard against.

- **Un-defer evidence:** a project that needs the patch to *react* to master
  (master-driven ducking, LED brightness following overall level) rather than
  merely scale gain — or a non-PD engine where dashboard-side composition is
  awkward.

### (2) Facilitator promotion — one manifest field, and a hard refusal

Promoting **patch params** to the facilitator surface is a real, cheap want.
The minimal delta reuses the existing render-from-manifest path: **one optional
boolean, `facilitator: true`, on a param declaration** in `bopos.patch.json`.
The value still flows as `/<id>/p/<name>` — no new wire, no new plane, no new
verb, no second config file. `facilitator.html` already renders volume cards;
it renders promoted params the same way. Consumers that don't know the field
ignore it (§8's "consumers ignore roles they don't recognise"). That is the
entire mechanism.

Promoting **bopOS admin commands** (shutdown/reboot/update) to the facilitator:
**hold the ratified scope guard** (facilitator proposal Q6). A non-technical
operator at a live show must not be one stray tap from rebooting the rig
mid-performance; that guard is load-bearing safety, not fussiness. I refuse a
general command-promotion mechanism outright — it is manifest bloat plus a
safety regression. If end-of-night "shut the rig down" is genuinely needed, the
answer is **one hardcoded, confirm-gated button** at the SILENCE-ALL tier
(`/all/os/shutdown`), which Bob ratifies as a specific affordance — not a
framework for arbitrary verbs. Default position: defer even that until a real
show asks.

### (3) Multi-element devices — build **nothing**, preclude nothing

This is the speculative-generality trap in its purest form: wanted someday,
needed by no current project. Do not design an element model in detail, and
above all **do not make it a "mode"** of the dashboard or of bopOS — a second
mental model is the tax that breaks a solo-artist framework.

The good news is that the additive path already exists and costs nothing to
preserve: the assign wire and node persistence **already carry a second
position** (`pos2x pos2y`, parsed at `helper.py:503-508`, a Belief-era remnant).
So *identity does not preclude split-channel today*. The real blocker is not the
contract or the dashboard — it is engine launch: `start-engine.sh` runs one PD
instance and the four localhost ports (6661/6662/7770/8880) are singletons that
a second instance would collide on. That means multi-element, when it comes, is
overwhelmingly a **node-launch change** (N engines with per-element port
offsets) plus per-element addressing on the wire — not a system redesign.

- **What to do now:** in S1, compute proximity from position 1 only. Keep the
  `pos2` slots. Keep the device/element terminology. That is the whole cost.
- **Un-defer evidence:** a *booked* installation that needs independently
  positioned channels (a Belief revival, or Playable Streets committing to
  split L/R). Then, and only then, run S2 as a node-launch stitch.

## 4. How it fits — the contract amendment (small) and code touch points

**Amendment diff (three edits, all already partly agreed):**

1. **§1** — strike the framework's claim to "the sync/cue/**spatial** control
   plane" and the dashboard's "spatial math"; spatial *geometry* is
   framework/dashboard-provided, spatial *mapping* is the patch's (node computes
   proximity, patch maps). (This is the overturn the redesign plan already
   agreed.)
2. **§4** — strike "dashboard-computed per-device `/p/gain` is the correct first
   implementation"; node-side `/pt` decomposition is **primary**.
3. **Add one short paragraph** (§8 or a new §4 note) — *Provided scalars:* bopOS
   may broadcast named full-state scalars a patch subscribes to by name and maps
   upstream of its own output; **bopOS never composes a provided scalar into a
   patch param.** Note master as the deferred instance (currently
   dashboard-composed) and add `facilitator: true` as an optional param field.

That paragraph is the anti-spatial-0 guardrail in one testable sentence: *if
bopOS is multiplying a value into a patch param, the seam is drawn wrong.*

**Code touch points (S1 only, now):** `helper.py` (node-side proximity + the
salvaged falloff curves), `simfleet.py` (same decomposition, per the house
rule), the `/pt` receive path. **Untouched now:** `osc_bridge.py`'s master
multiply (deferred), `facilitator.html` (one small render addition when the
field lands), everything about multi-element.

## 5. Why this is right — and why "minimal" doesn't re-invite spatial-0

The deletions *are* the design: I delete a master migration (zero projects need
it), delete a command-promotion mechanism (safety + bloat), and delete the
entire multi-element workstream (nobody has booked it). What remains is one
backend fix already scoped as S1 and one contract sentence.

The obvious objection to my seat: *minimal leaves the seam fuzzy and the next
spatial-0 walks right in.* It does not, because the one paragraph I add is a
**bright-line, mechanically checkable rule** — "bopOS delivers named scalars;
if it is composing a multiply into a patch param, it is wrong." Spatial-0 and
the master multiply are *both* instances of that violation. A rule that catches
both past mistakes with one sentence is a sharper seam than any amount of new
machinery, and it is cheaper to remember. Fuzziness comes from *more* surface,
not less.

## 6. Tradeoffs, risks, what I'm NOT solving

- **I am not moving master now.** Risk: the wire keeps carrying a product, not a
  raw value, so a future engine-agnostic patch that wants master must wait for
  the deferred work. Accepted — no current engine or project needs it, and the
  shape is designed so the wait is cheap.
- **I hold the facilitator admin-verb guard.** Risk: Bob's real installs *did*
  put shutdown on an operator tablet, so I may be overruling lived practice.
  That is explicitly Bob's to arbitrate; my recommendation is one confirm-gated
  button if anything, never a mechanism.
- **I build nothing for multi-element.** Risk: if a split-channel show books
  sooner than expected, S2 becomes urgent. Mitigated by preserving `pos2` and
  naming the real blocker (node-launch ports) so S2 is scoped, not surprising.
- **Not solving:** point authoring UI, sequencer integration, raw-distance
  exposure — all correctly parked in the S1 draft.

## 7. Smallest first step

Run **S1 exactly as drafted** (node-side proximity into a named scalar, patch
maps upstream of volume) and, in the *same* stitch, land the three-edit contract
amendment above — the crucial line being the *provided-scalars* paragraph.
Ship the `facilitator: true` field opportunistically when the facilitator view
is next touched. Do **not** open a master stitch or a multi-element stitch;
record both as deferred with the un-defer triggers named here. That is the whole
redesign.
