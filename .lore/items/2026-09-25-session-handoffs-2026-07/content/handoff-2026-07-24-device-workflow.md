# Handoff — device-scoped patch workflow intake (2026-07-24)

## Autopilot session results (2026-07-24) — items 1 & 2 done

Bounded autopilot run (usage meter was blind — OAuth token expired/HTTP 401 —
so this was scoped to the two named items, not an open-ended "until cap" loop).

**Tied this session:**
- `36-engine-startup-delivery-race` — commit `bf85372`. Root cause: the
  bopos→engine port (6661) is closed until PD opens it; `send_to_engine` raised
  `ConnectionRefusedError`, and because that is an `OSError`, an unwrapped send
  inside a LAN handler propagated to `lan_listener_loop`'s `except OSError`,
  which tore the LAN socket down mid-startup (node dark in Dashboard, SSH fine).
  Fix: `send_to_engine` swallows connection errors (returns False, no leak);
  `deliver_engine_context` redelivers id/groups/latest-static-params on the
  engine-alive 0→1 transition in `heartbeat_loop`; transient cues/points not
  buffered, automation not replayed. `tests/test_engine_ready_replay.py` (6
  browser-free node-protocol tests); full `tests/` suite 50 OK.
  **Remaining: cold-boot confirmation on a real Pi — do it on Finn Jet.**
- `38-patch-edit-chrome` (both children + parent) — commit `eecded1`. Menu-bar
  Patch Edit launches/closes the editor; removed "Hear it in the sim"/"Restart"/
  "Launch selected patch"; `#editor-launch` toggles Launch editor ⇄ Stop Editor;
  both affordances kept in sync. `verify_editor_toggle.py` (in tied 38/1) — 15
  Playwright checks, edit mode reached headlessly via `--sim-no-engine`. Diff
  delegated to a Sonnet subagent; orchestrator judged it and re-ran the verify.

**Docs healed this session:** CLAUDE.md now records the `--sim-no-engine`
headless-edit-mode verify trick (thread 37 will need it); the ai-kit
`loom-autopilot` skill gained a tie-before-commit learning (that edit is
uncommitted — it's in the separate `~/repos/ai-kit` repo).

**Recommended next stitch:** per the order below, item 3 —
`37-device-scoped-patch-control/1` design — but it is Bob-gated and wants the
fleet-patch definition settled jointly with `feature-backlog/34`. Item 5
(`39-remove-installed-pack-from-device`) is the next *unblocked, workable* loose
end if a non-design session is wanted. Item 1 (`36`) is code-complete; its only
open thread is the Finn Jet cold-boot check.

## State of play

Bob brought a workflow intake: two real devices on one network — **Finn Jet**
(kite spool, bopOS-as-a-fleet-node case) and **Ciro Toast** (standalone) — and
wants to target/interact with a patch on a single device without pushing to the
whole fleet, plus editor-chrome cleanup and a device-side asset-pack removal.
Parsed into four loom threads (37/38/39 new, plus the pre-existing 35 logging (since renumbered 42 and activated, 2026-07-24)
seed and 36 startup-race bug). Several design calls were ratified in-session;
the meaty per-device design stays Bob-gated.

## Ratified in-session (Bob, 2026-07-24)

- **Fleet patch = a bulk-set / default over per-node desired patch**, not a
  first-class rival target. Per-node desired patch is the primitive.
- **Per-device control is NOT gated on seat-assignment.**
- **Switch/deploy authority on the Patch tab** (patch-first: pick patch → target
  = whole fleet *or* one device), with a Device-tab **"Set patch…"** shortcut +
  the Device-tab **current-patch display and live-control panel**.
- **Engine stop/start on the Device tab is SHELVED** (Bob's own earlier ask,
  withdrawn 2026-07-24); `restart-engine` stays. Revisit only if it recurs.
- **38 keeps both enter/exit affordances** (menu-bar Patch Edit toggle + in-tab
  Launch editor/Stop Editor button), kept in sync.
- **39 = device-side uninstall**, terminology "**Remove**" (matches existing
  extra-row button), extended to installed catalog rows; NOT host-catalog delete
  (Bob deletes host folders directly).

## Ordered program of work (this is the order to follow)

1. **`36-engine-startup-delivery-race`** — the fresh Finn Jet startup-race bug
   (engine localhost port opens after the LAN listener; three provided-term
   sends refused). Foundation; hits the device we're about to use. Software
   diagnosis + readiness/replay boundary is workable now; final proof needs the
   Pi/Finn rig.
2. **`38-patch-edit-chrome/1` then `/2`** — editor chrome fixes. `1`: menu-bar
   Patch Edit launches/closes the editor. `2`: remove "Hear it in the sim",
   "Restart", "Launch selected patch"; rename Stop→"Stop Editor"; that button
   toggles in place with "Launch editor". Small, no design gate, Playwright-
   verifiable via simfleet.
3. **`37-device-scoped-patch-control/1` (design, `.waiting`, Bob-gated)** —
   write the proposal; settle **drift semantics jointly with
   `feature-backlog/34-fleet-patch-global-state`** (define "the fleet patch"
   once). Best done as a sit-down with Finn & Ciro on the bench.
4. **`35-node-logging/1` (design, `.waiting`, Bob-gated)** *(2026-07-24: renumbered `42-node-logging`, un-waited — Bob set medium priority)* — grow the logging +
   USB-auto-mount seed. Note: `31-install-oneliner` is already tied, so the
   automount install step is net-new install work spawned as a child here.
   Pairs with step 3 (both design sit-downs; USB wants a stick in a real
   device).
5. **`39-remove-installed-pack-from-device`** — device-side pack uninstall +
   active-slot guard. Independent; slot in whenever.

Coupling to remember: **37 and 34 share the fleet-patch definition** — open them
together.

## Test rig

Finn Jet + Ciro Toast, both on one network, visible together in the Dashboard.
See auto-memory `finn-ciro-test-rig`. Use both for every per-device behavior.

## Next session

Continue from this handoff. If this is a fresh autopilot resume, the current
target is wherever the loom left off in the order above (check `loom.sh status`
for `.stitching`/`.waiting` state and the newest `handoff-*.md`).
