# Working notes for agents

bopOS is a Raspberry Pi + Pure Data framework for networked multi-device sound
installations. This file is the orientation for any agent working here.

## Start here

1. `README.md` — system overview, OSC port map, patch system.
2. `docs/OSC-CONTRACT.md` — the **ratified** OSC contract (v1.5: 2026-07-07 base +
   the 2026-07-11 seam amendment, 2026-07-12 engine-boundary revision,
   2026-07-13 patch/asset distribution amendment, and the 2026-07-14
   fleet-patch fingerprint/cues amendments, plus the 2026-07-15 UID-admin and
   unassignment revision):
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

## Thread ordering (reconciled 2026-07-15 after patch-editor PE-4/PE-4b)

**Foundation status (all complete, software-side):** the OSC contract is at
**v1.5** (2026-07-07 base + seam amendment + engine-boundary revision +
distribution amendment + fleet-patch fingerprint/cues amendments + UID-admin
and unassignment revision); `engine-boundary-design`, `patch-seam`, `clock-sync`
(sync-0..3), spatial software (spatial-1/2), the dashboard's four phases + UI
review, the audition preview stack (Stage 0 + preview-0..3), and
`patch-asset-sync` (dist-0..4), fleet-patch (fp-0..4), and patch-editor
(pe-0..4 plus the PE-4b delivery/element-target follow-up) are **all tied**. `bopos.py`
(ex-helper.py) alone owns LAN 6660/5550; engines consume the localhost 6661
surface; run context is launch-delivered; `role`/meter are dead;
facilitator controls come only from `facilitator: true`.

**The workable queue for autonomous sessions.** Fleet-patch and patch-editor
are tied; fp-4 passed on bop000, the PE-3b launch-race regression passed an
audible simulator gate, and Bob confirmed PE-4/PE-4b point and cue delivery
from the live editor. This recommended order takes precedence over
`./.loom/loom.sh next`'s alphabetical listing:

1. **Complete:** `ui-tabs/tabs-0-ia-proposal` — Bob ratified the lore-kept
   Dashboard / Seats / Devices / Patches / Assets / Sequencer IA, amended so
   promoted Dashboard admin commands have explicit fleet and single-device
   action scopes.
2. **Complete:** `ui-tabs/tabs-1-skeleton` — the ratified six-tab structure,
   Dashboard compatibility entry, and dual-scope promoted admin commands are
   implemented and browser-verified.
3. **Complete:** `ui-tabs/tabs-2-review-session` — Bob's real-dashboard review
   plus an independent interactive-installation UX review are lore-kept. The
   resulting correctness-first next sweep is accepted. Bob explicitly dropped
   venue point persistence; runtime-only production points remain intentional.
4. **In progress:** `ui-tabs/tabs-3-next-sweep` — 01, 02, 03, 05, 06, 08, 07,
   09, and 10 are complete. Stitch 11 was narrowed with Bob on 2026-07-15 to
   **`11-assets-device-workflow`**: first establish device asset inventory,
   then manage assets on exactly one device at a time. Fleet-wide bulk asset
   rollout is deferred on the separate `asset-fleet-distribution` thread. Then
   continue with 12 Dashboard live controls, 13 diagnostic density, and 14 the
   device-alias design gate.
5. **`patch-workflow-friction/friction-0..1`** — resume after the full next sweep so the
   docs and starter-kit copy describe the finished editor and tab structure.

Everything else is `.waiting` for a reason stated in its stitch:

- **Bob + hardware gates:** `sync-4` (rig jitter measurement),
  `spatial-3-rig-sweep`, `preview-4-mac-linux-audible-gate` (ears, both
  platforms), `dashboard-6-rig-adoption` (the dashboard goal's tie gate),
  `zero-1` (claimable in any session that confirms bop000 reachable),
  `input-1`.
- **Bob-gated decisions/pauses:** `scene-sequencing` (whole thread paused
  2026-07-08; language is co-design, never solo), `zero-2-engine-verdict`
  (SC strategy is co-design), `audio-input` (deferred 2026-07-08),
  `pd-audition-host` (deferred until a concrete multichannel/DAW need),
  `parameter-addresses` (nested custom `/p/...` path design, parked until Bob
  resumes it after the UI-tabs runway), and `framework-version-management`
  (device framework-currentness/update design, parked on the same basis).

Standing rulings still in force: `/sync/*` wire shaping delegated (record
additively, flag it); a dev Pi is ssh-reachable for hardware stitches
(confirm in-session; don't bake gremlin-ask steps into instructions);
audition rig is Linux-first but **macOS is the likely performance
platform**; the 2026-07-08 "template lives in `templates/`" ruling is
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
