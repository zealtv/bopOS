# 54-remote-verb-promotion

> it would be good to have, in the patch manifest editor, the ability to set
> reboot, shutdown etc as remote parameters. — Bob, 2026-08-02

**`.waiting` on Bob.** Not because the outcome is unclear — it is perfectly
clear — but because the shortest route to it crosses a line the OSC contract
draws on purpose, and Bob is the one who drew it. The question below is one
ruling long.

## What exists today (measured 2026-08-02)

The wanted capability is **already built and already shipping**. What is
missing is any way to configure it from the app.

* `installation.json` carries `facilitator_commands: []` — an install-level
  allowlist of framework verbs. `dashboard/state.py:112`, cleaned at `:945`,
  published at `:417`.
* Remote renders them as a `Fleet setup` row, venue-wide
  (`facilitator.js:143`), and per-device inside each Seat card's
  `Device setup` disclosure (`control-column.js:275`).
* Destructive verbs (`updatebopos`, `reboot`, `shutdown`) are **hold-to-confirm**
  on both surfaces; the rest are `confirm()`-gated.
* The Control tab renders **none** of them — D8, `4-n-columns/3-chrome-demotions`:
  device commands left the Control column for a `Device setup…` hand-off to the
  Devices tab. Remote kept them because it has no tab to hand off to.
* **There is no UI anywhere that edits `facilitator_commands`.** The only way
  to set it is to hand-edit `installation.json`. Grep confirms: `state.py`,
  the two renderers, two test fixtures, `dashboard/README.md:208` and the
  contract. Nothing writes it.

That last point is almost certainly the real source of the request. The
manifest editor is where Bob sets what appears on Remote — it has a `Remote`
checkbox on every param (`dashboard.js:694`) and every event (`:708`) — so it
is the natural place to look for the other thing that appears on Remote, and
the only thing that isn't there is the verbs.

## The line this crosses

`docs/OSC-CONTRACT.md` §799-802 is explicit, and it is a ratified boundary, not
an implementation detail:

> Promotion of **framework verbs** is *never* a manifest concern: an
> install-level allowlist in `installation.json`
> (`"facilitator_commands": […]`, **default empty**) opts specific verbs onto
> the surface […] **The patch promotes its params; the venue promotes its
> verbs.**

The reasoning is sound and worth restating before anyone reopens it: a patch is
**portable content** and is distributed to the fleet, while `reboot` and
`shutdown` are **framework** verbs that exist whatever patch is loaded. Putting
them in the manifest means a patch copied from another venue silently arms
destructive fleet-wide buttons in this one, and it means the same verb's
availability changes when the fleet patch changes — which is the opposite of
what you want from a shutdown button.

There is also a mechanical consequence: `presets/` is excluded from the
distribution fingerprint (§9, v1.17) precisely so host-side edits do not
restage the fleet. Verbs in the manifest would have no such exclusion, so
toggling a Remote button would re-fingerprint the patch and restage every node.

## The question for Bob (this is the whole gate)

**Where should the verb allowlist be edited, given that it must stay venue-level?**

Three candidate answers, cheapest first. I recommend (a).

* **(a) A venue-level verb section, placed where Bob went looking.** The
  editing UI sits in or beside the Patches tab's manifest editor — visually
  adjacent, labelled as venue-scoped and clearly outside the manifest document,
  writing `facilitator_commands` through a new verb. Zero contract change; the
  request is satisfied; the boundary survives, and is made *visible* rather
  than merely documented. Cost: one panel that looks like it belongs to the
  manifest but does not, so the labelling has to earn its keep.
* **(b) Venue settings.** Same verb and same store, but the UI lives wherever
  venue-scoped configuration lives. More honest about scope, less discoverable —
  and discoverability is the actual complaint.
* **(c) Move promotion into the manifest.** A contract hard break, the
  portability and fingerprint costs above, and a migration for any
  `installation.json` already carrying the key. Only worth it if Bob's mental
  model really is "the patch decides", in which case the contract paragraph is
  the thing that is wrong.

## Second, smaller question, whichever way (a)/(b)/(c) goes

Bob wrote "as remote **parameters**". Two readings:

1. *the verbs appear on Remote alongside the promoted params* — which is what
   already happens, so the ask is purely the editing UI; or
2. *a verb can be placed in the parameter list, ordered among the params* —
   which is a real UI change, and interacts with
   `01-control-panel/8-manifest-reorder`'s drag-to-reorder.

Reading 1 is the safe assumption and matches the state of the code. Confirm
before building; the difference is one panel versus threading verbs through the
manifest editor's row model.

## Also worth putting to Bob while this is open

D8 removed device commands from the Control column and handed off to the
Devices tab. If verbs become configurable, is that still right? The Devices
tab's `Actions` section (`dashboard.js:1441`) renders `reboot`, `shutdown`,
`restart-engine`, `updatebopos` **unconditionally** — it does not consult
`facilitator_commands` at all. So an allowlist that gates Remote and gates
nothing on the desktop is a coherent design (the desk has physical access; the
iPad does not), but it should be a stated one rather than an accident.

## Do not start until Bob rules

An implementation child can be laid out from this stitch once the answer is in.
Record the ruling in `decisions.md`, and if it is (c), the contract revision is
part of the same stitch, not a follow-up.
