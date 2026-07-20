# Handoff — 2026-07-20 autopilot session

Orchestrated session (Fable orchestrating Sonnet implementation agents).
Everything queued for the session landed; the tree is clean and all work is
committed on `main`.

## Tied and committed

- `f059962` — **show-layout-polish/01-layout-review**: design session with
  Bob. Ratified: edit bar above the step list (structural-only;
  Duplicate/Delete disabled on message focus; divider duplicate allowed; no
  delete confirmation — undo covers); single click/tap inline step-name
  editing (Enter/blur commit, Esc cancel, blank→untitled, Enter/F2 keyboard);
  OSC terminals at 900px breakpoint / 320px fixed expanded height. Bob's
  review added hard retention constraints (coloured message pills, pill
  ⌘C/⌘X/⌘V/Delete copy/paste, message inspector, "Add message") — recorded in
  the tied stitch's `decisions.md`, honoured by 02.
- `84f829f` — **engine-group-context**: engines receive `groups` as sorted
  OSC ints (sentinel `-1`) at launch (runcontext/start-engine) and live over
  `bopos-context` after every durable membership change; audition parity;
  additive contract entry. Browser-free verifier: 0 failures.
  **Bob TODO:** the `bopos~.pd` receiver wiring described in
  `.notes/pd-edits-for-bob.md` (agents must not edit `.pd`).
- `cb43ff5` — **02-edit-bar-and-inline-step-name**: edit bar, real
  `duplicate_item` model/server op with fresh UIDs, inline step name (stored
  field still `alias`, UI label "name"), bottom add bar + Arrange grid
  removed after parity. 52-check Playwright suite at 1280/768px.
- `d314fbf` — **03-responsive-osc-terminals** + the `show-layout-polish`
  parent tie: CSS-only twin-column/stacked consoles with fixed 320px expanded
  height. Two non-obvious CSS facts recorded in the tied `verification.md`:
  Chromium wraps `<details>` children in a `::details-content` box (needs
  `display:contents` while `[open]` for flex layouts), and grid
  `align-items:stretch` will stretch a closed panel to its open sibling.
  29-check suite plus unmodified re-runs of the tied console, compact-row,
  and edit-bar suites.

## Loom state

No loose ends, no claims. Everything remaining is `.waiting` (Bob- or
hardware-gated): asset-fleet-distribution, sync-4, dashboard-terminology
review, framework-version-management, pi-zero-performance, scene-sequencing,
spatial-3-rig-sweep. Next software work is the host-loom patch-workflow
documentation/starter-kit close-out
(`~/repos/.loom/threads/patch-workflow-friction/`).

## Known minor pre-existing issues (not from this session)

- `.loom/tied/1-protocol-node/verify_group_protocol_node.py` fails on a
  pre-existing `AttributeError` (bare `AuditionRig` missing
  `param_declarations`) — confirmed by stash bisection to predate
  engine-group-context.
- `.loom/tied/boundary-5-launch-context-and-topology/verify_launch_context.py`
  is stale (missing `start-laptop.sh`, outdated assumptions).
- Older tied Show verifiers that poke the retired `.show-add-bar` /
  `#show-step-alias` selectors fail at that point by design; superseding
  coverage lives in the 02/03 tied suites.
- `dashboard/shows/` is untracked runtime data (left alone deliberately).
