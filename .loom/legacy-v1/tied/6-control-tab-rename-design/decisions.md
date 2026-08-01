# Ratified — Dashboard → Control tab (Bob, 2026-07-25)

Bob ratified `proposal.md` with all three open questions settled, **and issued a
correction that narrows this proposal's scope**. Authority for implementation
stitch `10-control-tab`.

## Correction to the proposal — read this first

**Bob:** "important: the dashboard is what is being renamed to control, not
patches. patch deployment to the fleet or to a pinned device happens on the
patch tab."

The proposal (and the artifact mockup) implied the Control tab would also host
the patch **target picker**. It does not. The split is:

| Tab | Owns |
|---|---|
| **Patch** | patch deployment — fleet *and* per-device pin. The bite-2 target picker stays exactly where it is. |
| **Control** | live control only — the renamed Dashboard tab. No patch deployment. |

Nothing about the shipped bite-2 picker moves. This also rewrites the hand-off in
stitch `4` (see its `decisions.md`).

## Ratified design

### 1. Rename + shared seat filter

**Bob:** "Dash is renamed to Control. let's use a shared seat filter as a
reusable component."

- The live-controls tab is renamed **Dashboard → Control** (label, route/anchor,
  and any copy referring to it).
- The **target filter** (All / Groups / Seat) is built as a **reusable
  component**, not a one-off widget on this tab — the same seat-filter component
  is available to other surfaces that need to pick a scope. It reuses the global
  selected-seat state (proposal recommendation, unchallenged).
- The filter scopes the shared `ControlSurface` (stitch 5) rendered below it.

### 2. Cues at the top

**Bob:** "let's try cues up the top."

Cues (with the master strip) sit as a **compact strip above** the control
surface. The rejected alternative was a persistent left rail. "Let's try" is
noted as provisional — this is a placement Bob wants to live with, so keep the
cue strip a self-contained block that can be relocated without touching the
surface below it.

### 3. Presets follow the target filter

**Bob:** "yes, presets follow target filter."

A preset is saved and recalled **in the scope the filter is currently on** —
saving under "All" is a different preset from saving under "Seat 2". This stitch
reserves the Presets shelf and fixes that scoping rule; **what** a preset
captures, how it loads, and generator interpolation remain thread `41`'s design.
