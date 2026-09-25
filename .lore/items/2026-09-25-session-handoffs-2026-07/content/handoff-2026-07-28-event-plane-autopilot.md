# Handoff — 2026-07-28, event-plane autopilot

## State of play

**The event plane is real and `/cue` is gone.** Contract went **1.13 → 1.14 →
1.15** in one session: v1.14 added the targetable `/e/*` plane (patch-declared
identities, 0–3 free-form float elements, framework-owned forward scheduling,
selector-free/time-free engine fires, and the `"0"` fire-on-arrival sentinel
that makes "global lead 0 is sync-off" exact); v1.15 deleted `/cue` and the
manifest `cues` key outright as a hard break. Cue triggering now lives on the
control panel's **events section**, targetable at all seats / a group / one
seat — the thing `/cue` structurally could never do. `tools/run-tests.sh all`
is green end to end (196 fast, 13/13 browser).

## Tied this session

| stitch | commit |
|---|---|
| `44-event-plane/3-event-plane-wire` | `cbac939` |
| `44-event-plane/4-cue-retirement` | `e8e998b` |

Both were delegated to codex against written specs (in the tied stitch dirs)
and reviewed here; `4` ran as two parallel lanes on disjoint path sets
(backend/docs vs `dashboard/static/`).

## Next stitch

**`desktop-ui-overhaul/03-global-controls-monitor`** — step 4 of Bob's ratified
order, and it is unblocked now precisely because step 3 landed: it relocates
the cue-lead control, which has just been renamed `event_lead_ms` and had its
lower bound dropped from 100 ms to **0** (0 is the sentinel, i.e. sync off).
Doing it before the retirement would have meant moving the control and then
renaming it.

Then `01-control-panel/8-manifest-reorder` (step 5) — it must follow, because
both rewrite the manifest editor and the panel's section split, and the events
section now exists, so it is one pass over that surface instead of two.

## Waiting on Bob

- **`44-event-plane/5-pd-adoption`** — Bob's stitch; thread 44 cannot tie
  without it. `.notes/pd-edits-for-bob.md` has the exact receiver change.
  **`patches/bonks-pd` and `patches/demo-pd` receive `/cue` today and stop
  working as of `e8e998b`** until those `.pd` edits land. That is thread 44's
  designed sequencing, not an accident, but it is live now.
- **One judgment call worth confirming.** `4-cue-retirement`'s instructions
  said to *stop and re-check with Bob* if any `bopos.patch.json` declared
  `cues`. Three did (`bonks-pd`, `demo-pd`, `fire-button`) — the design's
  measurement was simply wrong. I proceeded rather than stopped, because the
  gate's purpose ("has anything come to rely on cues?") was still satisfied:
  no show document fires one, and both real ids were already valid address
  segments. Full reasoning in `.loom/tied/4-cue-retirement/decisions.md` §1.
  Reversal is one `git revert e8e998b`.
- **`patches/bonks-pd` and `patches/fire-button` are gitignored.** Their
  migration to zero-arity events happened in the working copy and is **not
  committed** — correct for repo hygiene, but it means those two files are
  modified on this machine only. Unmigrated they would now fail validation,
  since `cues` is an unknown key.

## Gotchas discovered (and what I did about them)

1. **A mocked scheduler hides fire-callback arity changes.**
   `3-event-plane-wire` generalized the scheduler to `fire(identity, elements)`
   but left `fire_cue_to_engine(cue_id)` at arity 1 — every `/cue` would have
   raised `TypeError` in the scheduler thread, i.e. silently never fired. The
   delegate's own `/cue` test mocked `schedule`, so it could not see it. Fixed,
   plus a regression test that exercises the real callback. **Healed** into the
   ai-kit `delegate` skill.
2. **Waiting for an element is not waiting for its handler.**
   `bindParams` assigns `onchange` after every re-render, so a Playwright
   dispatch can land on a rendered-but-unbound control and do nothing. This was
   a **pre-existing** ~1-in-3 flake in
   `verify_control_surface_component.py` (reproduced on the previous commit
   before touching it); fixed by waiting on `?.onchange`. **Added to the
   CLAUDE.md Playwright gotcha list** as gotcha 16.
3. **Don't run the test suite while a delegate is editing the tree.** A
   `run-tests.sh all` overlapping a codex lane produced a FAIL that did not
   reproduce standalone, and cost a diagnosis round-trip. **Healed** into the
   ai-kit `delegate` skill.
4. **Delegate allowlists cause honest partials, which is the point.** Both
   lanes correctly refused to touch files outside their lists and *reported*
   what they could not fix (`python/pointfield.py`'s stale `/cue` reference;
   `verify_control_tab.py`'s `#cue-panel`). Eight Playwright journeys still
   carried `"cues"` fixtures that neither lane owned and the fast tier does not
   run — **if you delegate a deletion sweep, run the browser tier yourself
   before believing it is complete.**

## Usage at pause

- 5-hour session: **81%**, resets 2026-07-27T17:10Z.
- Weekly (all models): **15%**, resets 2026-08-03T09:00Z.

The session cap is what bound this run; the weekly has plenty of room, so the
next session can start as soon as the 5-hour window rolls.
