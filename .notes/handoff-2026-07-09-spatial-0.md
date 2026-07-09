# Handoff — 2026-07-09 (autopilot: spatial-0 Stage-A engine)

## State of play

The **spatial-audio Stage-A engine is software-complete**. The dashboard now
spatialises sound: a moving point (x,y) + radius + falloff curve resolves to a
per-device gain that rides the volume param already on the wire, composed as
**stored mix × master × spatial**, runtime-only (never persisted). This is the
ratified Stage-A transport — dashboard-computed per-device `/p/gain` (contract
§4); node-side `/pt` falloff (Stage B, big fleets) stays gated in the parent for
Bob co-design. The engine accepts `static` / `path` / `orbit` motion; **spatial-1
(the map authoring UI) is the next stitch** and mostly just sends `static`
drag points to the `set_spatial` ws command that already exists.

One stitch tied this session (`spatial-0`); the loom is honest (nothing claimed).

## Tied this session (commit hash)

- **`spatial-0-engine`** — `0ce8821`. New `dashboard/spatial.py` (pure math:
  falloff `linear`/`smooth`/`gauss`, motion `static`/`path`/`orbit`,
  `device_factor`, `sanitize`; built **mask → per-device value** so a
  video/node-side mask slots into `device_factor` later). `osc_bridge.py` folds
  the spatial factor into `send_device_param` + a change-gated ~25 Hz tick loop
  (`spatial_loop`, only ticks while the point moves). `server.py` `set_spatial`
  ws command (full-state/idempotent). `state.py` seeds runtime-only
  `data["spatial"]`. `simfleet.py` logs applied `p/<name>` values.
  `verify_spatial_engine.py` (in the tied stitch) = **18/18 PASS**; `dashboard/
  README.md` gained a "Spatial automation (Stage A)" section.
- Heal (same commit set, see `d…` below): CLAUDE.md testing note now points at
  the `~/.venvs/bopos` venv + PEP-668 workaround (this session lost time to a
  missing venv / system-pip block).

### Key design decision (recorded in the stitch's `results.md`)

**Shared gain-resolution helper: yes, and it already existed.**
`send_device_param` was already the single point resolving a device's wire
volume (stored × master). Spatial multiplies **there**, not in a new helper or a
parallel `/sgain` path — so manual set, preset load, master move, and the
spatial tick all compose the three factors in one place and can't drift.
Unpositioned devices / devices with no volume param resolve to factor 1.0
(untouched), never silenced.

## Recommended next stitch

**`spatial-1-authoring-ui`** — the spatial map drag/path UI on the facilitator
surface, driving `set_spatial`. Note: it's a **Playwright/browser** stitch and
**chromium is not installed here** — `~/.venvs/bopos/bin/playwright install
chromium --only-shell` first (see the healed CLAUDE.md testing note). If a cold
session wants browser-free work instead, `audition-1-stage0-launcher` (Linux-
first, interleavable, backend/bash) or `samples-0-backend-manifest` are good
heads; `spatial-2-synced-start` (cue a named sample fleet-wide via `/cue`) is
also available and builds on the tied sync work.

## Waiting / blocked (nothing blocks agent work)

Unchanged from the prior handoff: `sync-4` (hardware run), `audition-0` (macOS
spike), `audio-input` (deferred), pi-zero hardware children, scene-sequencing
(paused), `dashboard` (real-rig adoption). All agent-workable loose ends are
listed above.

## Decisions awaiting Bob

Carried forward from `handoff-2026-07-09.md` (none new this session):
1. **PD `/cue` receiver** — helper.py fires a bare `/cue <cueId>` to PD on 6661;
   the default patch needs a `[/cue]` receiver (PD is Bob's domain — pending
   pd-edit, alongside the `level`-meter item).
2. **Not pushed** — the branch is well ahead of origin/main (this session's
   spatial commit + everything prior). Bob still needs to `git push`.

No new decision gate: spatial-0 lives entirely within ratified contract §4
(Stage-A `/p/gain`); the `set_spatial` shape is additive/backend-only.

## Gotchas (healed where noted)

- **Verify deps need the `~/.venvs/bopos` venv**; system `pip` is PEP-668
  externally-managed and refuses installs. This session used a scratchpad venv
  to run the verifies; the *project* convention is `~/.venvs/bopos` (per
  `dashboard/README.md`) and it was missing on this machine. **Healed** in
  CLAUDE.md's "Dashboard browser tests" bullet (create-if-missing recipe +
  browser-free vs Playwright dep split).
- **`.loom/loom`** is the script name (README calls it `loom.sh`); `./loom
  <cmd>` works. Not healed (cosmetic).
- **simfleet now logs `p/<name>=<v>`** on every applied patch value — a few
  hundred lines during a sweep. Fine for verify; if it ever gets noisy for a
  human watching a long run, that's where to gate it.

## Usage at stop

- **weekly (Fable): 96%** — another model's cap, ignored for this Opus run
  (only forbids spawning Fable sub-agents). Resets 2026-07-13T09:00Z.
- **weekly (all models): 66%** — resets 2026-07-13T09:00Z.
- **5-hour session: 69%** — resets 2026-07-09T17:20Z.

Stopped at a clean thread boundary with headroom (session 69% < 85% threshold),
not at a cap — deliberately, because the one remaining fit-in-budget path
(`spatial-1`) is a browser stitch needing a chromium install, too big for the
~16 session points left once heal + handoff are reserved. A follow-on Opus
session can continue immediately. Tell the next session: **continue from this
handoff, next stitch `spatial-1-authoring-ui`** (install chromium first) — or
pick a browser-free head if chromium is unwanted.
