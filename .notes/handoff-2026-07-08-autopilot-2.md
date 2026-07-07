# Handoff — 2026-07-08 autopilot session 2

## State of play

The OSC contract thread is **fully closed** and the dashboard is now through
phase 3 with phase 4's buildable half done. This session tied `os-admin-verbs`
(and with it the `osc-schema-contract` goal), then built the dashboard forward:
spatial map, discovery+assignment, and patch+installation management — each
browser-verified against simfleet. Two user-facing / contract-adjacent pieces
are parked on Bob's ratification (facilitator view, sensor-data view), each
with a written proposal. Same Codex-free split as before, but this session did
the builds itself (they were UI + Python glue over verbs already specified), and
leaned on the headless-browser verify pattern that every dashboard stitch now
shares.

**Not yet pushed** — the branch is ahead by this session's commits plus the 3
from the prior session. Bob still needs to `git push`.

## Tied this session (local commits)

- **os-admin-verbs** — `b7b0a4c`. helper.py's 6660 listener answers the §7
  lifecycle + provisioning verbs, delegating to the 7770 callbacks; every verb
  replies `/os/rev <sha> <model> <uid>` (lifecycle before executing,
  provisioning after the pull). Ephemeral no-ops provisioning but still sends
  the receipt. simfleet mirrors it; dashboard flipped its admin row off legacy,
  added a Converged line + restart-engine. Closed the `osc-schema-contract`
  goal (`a4e1f9f`). Proposals in the stitch's `design-decisions.md`: the
  trailing `uid` on `/os/rev`, and `/os/getsamples`→`/os/fetch` remap.
- **spatial-map** — `ca0a005`. SVG floor plan in the tech dashboard; drag to
  position, double-click for a speaker pair, UNPLACED tray, room bounds in
  metres in `installation.json` (the coordinate system spatial-audio will use).
- **dashboard-3-discovery-assign** — `8a9884a`. Unassigned pool keyed by uid,
  assign form (name + next-free id + uid-targeted Identify), `/os/assign`
  pushed + persisted node-side incl. positions, ID-collision refusal.
  `bopos.devices` is now an export (`GET /bopos.devices`), not the source.
- **patch-and-install-mgmt** (child of dashboard-4) — `4aa7145`. Patch panel
  (switch/pull/add-from-GitHub/get-samples over the `/os/*` verbs), framework
  update visibility via version + `/os/rev` convergence, and venue save/load
  of `installation.json` (`dashboard/installations/<name>.json`, gitignored).

## Waiting on Bob (proposals written; nothing blocks on them)

1. **facilitator-view** (`dashboard-2` child, `.waiting`) — lore item
   `2026-07-08-facilitator-view-proposal`. Six questions; the load-bearing one
   is how a volume card finds its param now params are manifest-declared
   (proposed `role: "volume"` marker + `gain` fallback).
2. **sensor-data-view** (`dashboard-4` child, `.waiting`) — proposal in the
   stitch (`proposal.md`). Option A (patches/helper republish read-only `/p/*`
   meters, recommended) vs Option B (new `/io/report` stream). Shares the
   `role` manifest-field question with #1 — decide them together.
3. Still open from session 1: `git push`; the PD edits in
   `.loom/tied/osc-schema-contract/pd-edits-for-bob.md` (§1–§4 + the §13
   revision); real-rig verification of every tied stitch.

## Recommended next

- **If Bob has ratified the `role` field:** build `facilitator-view` then
  `sensor-data-view` — both unblock together and finish the dashboard thread
  (only `dashboard-4`'s parent tie then remains, gated on sensor-data-view).
- **Otherwise, free-floating, no gate:** `sample-distribution` (now has
  `/os/fetch` + dashboard asset serving to build its fleet-sync UI on),
  `clock-sync` (next on the critical path after dashboard), or the
  measurement half of `pi-zero-performance`.
- **Do NOT start `scene-sequencing/scene-language-spec` solo** — Bob asked to
  design the scripting language / Ableton-clip-slot triggering *with* him.
  Surface it and wait for him.

## Gotchas (healed where noted)

- Every dashboard stitch ships a `verify_*.py` (real server + real simfleet +
  headless Chromium). Reuse the newest tied one as a template. Healed into
  CLAUDE.md "Testing without hardware" along with the three Playwright gotchas
  this session hit: `inner_text` applies `text-transform` (lowercase before
  matching); clicking auto-scrolls (scroll to 0,0 + re-read boxes before a
  drag, clamp targets on-screen); use one type-aware `dialog` handler.
- The dev venv (pyOSC3, python-osc, websockets, fastapi/uvicorn, playwright +
  chromium `--only-shell`) is in this session's scratchpad; rebuild via the
  CLAUDE.md command. This box has working pip 24.0.
- Loom CLI is `./.loom/loom …`, not `./loom.sh` (that path doesn't exist here).

## Usage at stop

5-hour **session cap at 77%** (threshold 85), resets 2026-07-08T03:20Z
(~an hour out). Weekly Fable 73% (resets 2026-07-13T09:00Z), weekly all-models
45%. A fresh session after the session reset has a full 5-hour window; the
weekly Fable cap is the one to watch for a long run.
