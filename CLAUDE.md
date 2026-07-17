# Working notes for agents

bopOS is a Raspberry Pi + Pure Data framework for networked multi-device sound
installations. This file is the orientation for any agent working here.

## Start here

1. `README.md` — system overview, OSC port map, patch system.
2. `docs/OSC-CONTRACT.md` — the **ratified** OSC contract (v1.7: 2026-07-07 base +
   the 2026-07-11 seam amendment, 2026-07-12 engine-boundary revision,
   2026-07-13 patch/asset distribution amendment, and the 2026-07-14
   fleet-patch fingerprint/cues amendments, the 2026-07-15 UID-admin and
   unassignment revision, the device asset-inventory amendment, plus the
   2026-07-17 patch-admin-surface amendment (engine-sent `/admin` requests,
   version/patch-fingerprint in the run context)):
   grammar, planes, provided terms (§4.1), the engine surface (§4.2),
   identity/persistence, ports, constraints. Don't re-litigate it; the reasoning
   lives in lore items `2026-07-07-osc-schema-council`,
   `2026-07-10-patch-seam-council`, and tied `engine-boundary-ratification`.
3. `.notes/architecture-review-2026-07-05.md` — the current architectural review and
   forward plan; the shared context every loom thread points back to.
4. `./.loom/loom.sh status` — live task state. The loom (`.loom/`) is the task tracker;
   read `.loom/README.md` for the protocol (claim → work → tie; split when too big).
5. `.notes/dashboard-development-context.md` — full dashboard design (stack, protocol,
   UI) if working on dashboard threads.

Verification levels and representative commands are collected in
`docs/VERIFICATION.md`. Stitch-local instructions and verification artifacts
remain the authority for a particular piece of work.

## House rules

- **NEVER edit Pure Data patches (`.pd` files).** PD programming is Bob's domain.
  Agents work on Python, Bash, JS/HTML, architecture, and docs.
- **PD float precision:** PD's OSC floats are 32-bit. Never send a value needing >6
  significant figures (epoch timestamps, fine clocks) through PD as a float — encode
  64-bit values as strings or int pairs, and keep absolute time out of PD entirely.
- **0-indexing is the default** for elements, points, and any new index on the wire
  or in code (Bob, 2026-07-11). Human-facing labels may render however the UI likes,
  but the wire and the data model count from 0.
- **Decision gates:** some choices are Bob's to ratify — the OSC port/namespace
  redesign, scene-language syntax, engine strategy calls, anything user-facing in the
  facilitator view. Produce a written proposal (see Lore below), mark the stitch
  `.waiting`, and surface it to Bob. Don't implement past an unratified design.
- Commit style: plain prose subject line (match `git log`), body explaining why.

## Thread ordering (reconciled 2026-07-16)

**Foundation status (all complete, software-side):** the OSC contract is at
**v1.7** (2026-07-07 base + seam amendment + engine-boundary revision +
distribution amendment + fleet-patch fingerprint/cues amendments + UID-admin
and unassignment revision + additive unattended-update outcome receipts +
2026-07-17 patch-admin-surface amendment);
`engine-boundary-design`, `patch-seam`, `clock-sync`
(sync-0..3), spatial software (spatial-1/2), the dashboard's four phases + UI
review, the audition preview stack (Stage 0 + preview-0..3), and
`patch-asset-sync` (dist-0..4), fleet-patch (fp-0..4), and patch-editor
(pe-0..4 plus the PE-4b delivery/element-target follow-up), and the nested
parameter-address foundation are **all tied**. `bopos.py`
(ex-helper.py) alone owns LAN 6660/5550; engines consume the localhost 6661
surface; run context is launch-delivered; `role`/meter are dead;
facilitator controls come only from `facilitator: true`.

The dashboard review sweep is complete through Devices and Patches (01, 02,
03, 05, 06, 08, 07, 09, and 10). Bob expanded the accepted implementation
sweep to the following **nine-stage program of work**. This order takes precedence
over `./.loom/loom.sh next`'s alphabetical listing; still claim, work, verify,
and tie one concrete stitch at a time:

1. **Complete — parameter-address foundation.** Contract/model/relay and
   dashboard state/editor are tied. True nested OSC, flat compatibility,
   canonical persistence/presets, and editor path CRUD are verified; promoted
   live controls remain reserved for stage 7.
2. **Complete — Seat-group spatial UX gate.** Bob ratified focus plus bounded
   four-group rail comparison, view-local styles, checklist authoring,
   eye/eye-off visibility, and the subordinate collapsible Groups placement
   after Seat detail and before Simulation/Venue.
3. **Complete — Seat-group core.** Canonical selectors, node persistence and
   matching, simulator/audition parity, dashboard group state, safe assignment
   transitions, and acknowledged membership synchronization are tied.
4. **Complete — Seat-group delivery.** Group catalog/membership authoring,
   eye/eye-off comparison controls, stable four-slot spatial rails, responsive
   touch layout, and dense-layout verification are tied.
5. **Complete — Single-device Assets workflow.** Device asset inventory
   (`11a`) and the operational one-assigned-physical-device Assets workspace
   (`11b`) are tied. The first real `bop000` transfer gate also repaired
   canonical cache ordering across restart and retired the temporary
   `samplepacks` compatibility path. Durable observations drive
   absent/current/stale/unknown/extra state; fleet-wide bulk rollout remains
   deferred to `asset-fleet-distribution`.
6. **Complete — unattended Update bopOS.** Runtime convergence is split
   from privileged provisioning, fails without prompting, reports outcome
   phases and reboots only after success. Niko Cloud passed the real
   receipt-before-reboot/return gate at `7d8a671` with `bonks-pd` preserved.
7. **Complete — Dashboard live controls.** The staged host manifest now drives
   Seat-owned All/Group/Seat promoted controls with nested identity intact,
   mixed aggregates, durable offline/unbound values, and per-Seat/All replay.
   Exact-UID persistent physical-device mute, fleet-overlay OR semantics,
   selected-detail action, roster indication, simulator/audition parity, and
   focused touch verification are tied. Seat/Group mute and solo remain
   deferred.
8. **Complete — Diagnostic density and polish.** The host Git shorthand,
   copyable identity tails, adjacent desired/reported identities, terse copy,
   divided Seat inspector, two-element UI guard, Seat-bound IP, empty-preset
   cleanup, UX-reviewed All & Groups / Seats live tabs, and manifest-declared
   synchronized Dashboard cue triggers, bounded Seat/Device rosters, live Seat
   name filtering, independently staged device mute beneath fleet safety, and
   exact-device alias-derived hostname action are tied. Existing Pis need one
   manual provisioning run before the hostname action is available.
9. **Next — Close the sweep.** Resume
   `patch-workflow-friction/friction-0..1` so documentation and starter-kit
   copy describe the finished system.

The latest sequencer brainstorm is input to the separately Bob-gated
`scene-sequencing` co-design. It is not part of this nine-stage sweep and does
not authorize implementation.

Everything else is `.waiting` for a reason stated in its stitch:

- **Bob + hardware gates:** `sync-4` (rig jitter measurement),
  `spatial-3-rig-sweep`, and `zero-1` (claimable in any session that confirms
  bop000 reachable).
- **Bob-gated decisions/pauses:** `scene-sequencing` (whole thread paused
  2026-07-08; language is co-design, never solo), `zero-2-engine-verdict`
  (SC strategy is co-design), and `framework-version-management` (device
  framework-currentness/update design, parked on the UI-tabs-runway basis).
  `parameter-addresses`, `seat-groups`, the single-device Assets workflow, and
  Dashboard live controls and diagnostic density are complete. The next
  software stitches in the accepted sweep are patch-workflow friction
  documentation and starter-kit copy.

Standing rulings still in force: `/sync/*` wire shaping delegated (record
additively, flag it); a dev Pi is ssh-reachable for hardware stitches
(confirm in-session; don't bake gremlin-ask steps into instructions);
the audition software stack is retained, but the combined Mac/Linux audible
gate—particularly Linux auditioning—is no longer actively tracked; the
2026-07-08 "template lives in `templates/`" ruling is
**superseded** (Q6, 2026-07-13 — demos live in `patches/`).
Cross-repo: spool-scoped siblings live in `kite-choir-brains/.loom`
(`bopos-uptodate`) — coordinate, don't duplicate.

## Testing without hardware

- **Simulated fleet:** `dashboard-0-sim-fleet` builds `tools/simfleet.py` — N fake Pis
  speaking the real OSC protocol (heartbeats on 5550, commands on 6660). Once it
  exists, use it for all dashboard/clock-sync/scene development; treat it as part of
  the deliverable (new protocol features land in the simulator in the same stitch).
- **Laptop rig:** `bash/start-laptop.sh` runs PD + the io bridge on a laptop
  (MCP2221A USB-I2C adapter) for peripheral work.
- **Audible fleet:** `audition-rig` builds the composition monitor — N real engine
  instances on the laptop, spatially mixed. Protocol-only (`simfleet`) and audible
  instances should stay config-compatible so they can mix in one session.
- **Real Pi loop:** the edit→push→pull-on-Pi dance and the stop-stack/restart test
  sequence are documented in `kite-choir-brains/.claude/skills/bopos-dev/SKILL.md`.
  Hardware verification ultimately needs Bob or a live rig — say so in the stitch
  rather than claiming it verified.
- **Dashboard browser tests:** every dashboard stitch ships a `verify_*.py` that
  launches the real `dashboard/server.py` + `tools/simfleet.py` on non-default
  ports and drives headless Chromium (Playwright). Copy the newest tied one
  (`.loom/tied/*/verify_*.py`) as the template — repo-by-marker root, sim ports,
  teardown. **Verifies run from the `~/.venvs/bopos` venv** (the path
  `dashboard/README.md` uses); system `pip` is PEP-668 externally-managed, so if
  that venv is missing, create it: `python3 -m venv ~/.venvs/bopos && ~/.venvs/
  bopos/bin/pip install -r dashboard/requirements.txt pyOSC3`. Browser-free
  verifies (sync/spatial planes — LAN/engine only) need just those deps; the
  Playwright dashboard suites add: `~/.venvs/bopos/bin/pip install playwright &&
  ~/.venvs/bopos/bin/playwright install chromium --only-shell`.
  Three Playwright gotchas these scripts learned the hard way: (1) `inner_text`
  applies CSS `text-transform`, so lowercase before matching a `capitalize`d
  row; (2) clicking a button auto-scrolls the page — `window.scrollTo(0,0)` and
  re-read bounding boxes before a spatial drag, and clamp drag targets on-screen
  (the room can extend above the viewport); (3) one type-aware `page.on("dialog")`
  handler (prompt→text, else accept) — two handlers race and one eats the other's
  prompt.

## Records

- `.lore/` holds complete dated artifacts — design proposals, decision records,
  session transcripts. `./lore.sh keep <prepared-dir> <slug>`; read `.lore/INDEX.md`
  deliberately, don't auto-load it. Design drafts awaiting ratification live here.
- `.notes/` holds current working reference (revisable); `docs/` (once created) holds
  durable specs like `OSC-CONTRACT.md`.
- Put working artifacts (measurements, logs, decision notes) inside the stitch
  directory — they travel with it into `tied/`. Because tie **moves** the
  directory (different depth), stitch test scripts must locate the repo by
  marker (walk up until `tools/simfleet.py` exists) or via an imported
  module's path — never by a fixed number of `..` hops.
