# Patch editor — design proposal (pe-0)

Drafted and **ratified by Bob 2026-07-14** (his verbatim rulings on the four
open questions are recorded at the end). Decisions ratified earlier the same
day and not re-opened here: the editor launches PD itself with the GUI via
the managed-audition path; cues become a declarable manifest field (additive
v1.3→v1.4); shared infrastructure under an independent UI; sim and edit
modes are mutually exclusive.

## 1. Summary

The patch editor is a third state of the dashboard's engine supervisor. The
dashboard already knows how to run host patches audibly through
`tools/audition.py`; the editor is that same rig at N=1 with the PD GUI
visible, plus three authoring affordances: a live parameter panel, a manifest
editor (params and cues — no more hand-editing `bopos.patch.json`), and a
mini spatial setup for points. Editor traffic is private loopback, like the
listener puck: outside the fleet OSC contract.

## 2. Mode model: `off | simulate | edit` — mutually exclusive

Bob asked whether sim and edit should be exclusive. Yes, and the current
architecture effectively decides it for us:

- `audition.py` **binds** the loopback command port (`--cmd-port` = the
  dashboard's send port). Two rigs cannot both bind it.
- `start_simulation()` retargets the dashboard's single OSC sender to
  `127.0.0.1` and `stop_simulation()` restores the performance target and
  re-asserts seat assignments. The OSC plumbing is single-target by design.

So the supervisor holds one mode enum: `off`, `simulate`, `edit`. Entering
either running mode stops the other first (confirmation-gated when leaving a
*running* sim, matching the existing active-patch send gate). Switching is
cheap because both modes share the launcher — the editor gets a **"Hear it in
the sim"** button that tears down the edit session and starts the simulated
fleet on the same patch, and the sim panel gets the inverse ("Edit this
patch"). Exclusivity also sidesteps audio-device contention (N sim engines +
one GUI PD fighting over CoreAudio/JACK).

Real-fleet interaction: `edit` mode retargets OSC to loopback exactly as
`simulate` does, so a LAN fleet is untouched while editing — devices keep
heartbeating and reappear when the mode returns to `off`.

## 3. Editor session lifecycle

- `audition.py` grows an `--edit` flag: forces `--devices 1`, drops `-nogui`
  from the PD command, and reports `mode: edit` in its ready message.
  Everything else — run context, `BOPOS_ENGINE_PORT`, the relay surface,
  heartbeats — is unchanged. No parallel launch stack.
- Selecting a patch in the editor tab spawns the rig on that patch's
  manifest, exactly like the sim's Switch. Switching patches restarts the
  single engine (same `restart_simulation` shape).
- The existing `/hb` engine-alive flag is the health signal. If Bob quits the
  PD window, the tab shows "engine closed" with a **Relaunch** button rather
  than silently respawning — respawn would discard unsaved PD edits' state
  and steal focus.
- PD is live-editable, so there is no edit→restart loop: the running instance
  *is* the editing surface. Restart exists only as an explicit button (to
  test a patch's cold-start behaviour, seed/run-id regeneration).

## 4. Parameter panel

Reuse the tech view's manifest-driven param controls, pointed at the edit
instance: sends go `/0/p/<name>` through the normal selector path and the
shared `relay.shape_provided_term` strips them to `/p/<name>` on the engine
port. The panel shows **all** declared params (not just facilitator-promoted
ones), grouped by `group`, with the facilitator flag visible as a badge.
Master is included (the rig already relays `/os/master`); framework mute is
not (it deliberately isn't relayed to engines).

## 5. Manifest editing — params and cues

A form-based editor over `bopos.patch.json`:

- **Params:** add/edit/remove rows — name, type (`f`/`i`), min/max, default,
  group, facilitator flag. Writes are atomic (temp file + rename) and
  validated through `python/manifest.py` before landing; an invalid edit
  never reaches disk. Name changes and removals warn that the PD patch's
  receives must follow.
- **Liveness — no dev-mode carve-out needed.** The relay forwards any
  `/p/<name>` without checking the manifest, and `/os/params` re-reads the
  file per request. So: save the manifest → the panel re-renders with the new
  control → move it → the value arrives at the live PD instance → add the
  receive object in the open GUI. Zero restarts, zero contract exceptions.
  (Node-side launch validation is untouched; it still gates production
  starts.)
- **Cues:** same CRUD treatment for the new `cues` list (§6).
- **Scope guard:** `engine`, `entrypoint`, `caps`, `slots` render read-only
  in v1. They change rarely, and hand-editing them is not the friction Bob
  named.
- **New patch:** a "New patch" action creates `patches/<name>/` with a valid
  minimal manifest **and a stub `main.pd` copied from a Bob-provided template
  file** (ratified Q2: "i'll provide the file to copy — that will give us a
  template ready to go for free"). The editor never generates or edits `.pd`
  content itself; it only copies Bob's file verbatim. Implementation note for
  pe-3: the template's home must not surface in the patch catalog (it is not
  a patch) — pick a location outside catalog listing and document it; if the
  template file is absent, New patch still succeeds with manifest only and
  says so.

## 6. Cues amendment — proposed v1.4 wording

Addition to contract §8 (additive; validation rejects malformed entries but
an absent key stays valid):

> **`cues` (optional; additive, v1.4):** a list of cue declarations the
> patch responds to: `{"id": <string>, "label": <string, optional>,
> "description": <string, optional>}`. `id` is the exact string delivered as
> the bare relative fire `/cue <id>` (§3.1 unchanged: engines never see
> absolute time). Declarations are documentation and UI surface only — the
> framework neither filters undeclared cue ids nor schedules anything from
> the manifest. Duplicate ids are invalid.

The editor renders one fire button per declared cue (fires immediately: the
dashboard's normal `/cue` broadcast with a now-deadline reaches the rig's
scheduler unchanged), plus a free-text fire box for trying ids before
declaring them. The tech view may later render declared cues fleet-wide;
that's ui-tabs/fleet territory, not this thread.

## 7. Points mini-setup

Reuse the spatial map component in a stripped configuration: one element
pinned at the origin (the edit instance), **with the origin at the centre of
the box, not the corner** (Bob, 2026-07-14 — the element sits mid-room so
points can approach from every side). Draggable points keep the existing
radius/falloff authoring controls. Point frames go out the normal `/pt` wire;
the rig already decomposes them into per-element proximity `/pt <id> <el>
<v>` — with one element that's exactly the preview a composer needs to hear
a point sweep past. Editor points are session-local scratch state, not
written into `installation.json` (open question 3). The listener puck is
omitted: one source needs no spatial mix, and stereo identity is the rig's
default.

## 8. Single-object seam assessment ([bopos] + [bopos.out~])

Walking the resulting composer workflow: New patch → manifest form → launch →
drop objects into an empty canvas → add receives as params are declared. The
editor makes patch *scaffolding* nearly free, which raises the relative cost
of the remaining boilerplate — two required objects whose split serves the
framework's history, not the composer. The clone-singleton argument from the
2026-07-13 assessment stands; nothing in this design depends on the split
(the editor talks to the surface, not the objects). **Ratified (Q1: "two is
good"):** the merge keeps its own contract revision, cut when the PD work
actually happens; v1.4 carries the cues amendment alone. The merge remains
recommended Bob-side PD work after the editor lands.

## 9. SuperCollider path

`--edit` on a non-PD engine launches the engine exactly as the sim does
(manifest `engine` + entrypoint) and everything except the GUI works: param
panel, manifest editor, points, cues. The "open in editor" affordance is
PD-only in v1; the tab says so plainly for SC patches rather than guessing at
`scide` invocation. Revisit if SC editing becomes real (zero-2 is the
gate for SC strategy anyway).

## 10. Implementation split (created on ratification)

- **pe-1-contract-v1.4** — the cues amendment only (Q1: single-object
  amendment stays out); manifest validation for `cues`; docs.
- **pe-2-edit-mode** — `audition.py --edit`, the supervisor mode enum with
  exclusive switching, tab UI with patch list + param panel + health/relaunch.
- **pe-3-manifest-editor** — param/cue CRUD forms, atomic validated writes,
  New patch (manifest + Bob's template `main.pd` copied verbatim).
- **pe-4-points-and-cues-ui** — mini spatial setup, cue fire buttons.

Each ships a Playwright `verify_*.py` per house testing rules; pe-2 onward
verify against a real launched PD only where the environment has one, with a
`--no-engine`-style fallback for CI-ish runs.

## Ratification record (Bob, 2026-07-14, verbatim)

The four open questions were put to Bob in-session; his answers, quoted:

> 1. two is good. 2. i want a stub written - but i'll provide the file to
> copy. that will give us a template ready to go for free. good ux. 3.
> session only is fine. 4. master only is good.

Applied as: (1) v1.4 = cues only; the single-object §4.2 amendment gets its
own later revision. (2) New patch copies a Bob-provided `main.pd` template
verbatim — the editor still never authors `.pd` content. (3) Editor points
are session-only scratch, never persisted. (4) The editor's only global
control is master.

Earlier the same day Bob also ratified, in-session: sim/edit mutual
exclusivity ("might be best for it to be either sim *or* edit") and the
shared-infrastructure approach ("the shared infrastructure point is totally
fine").
