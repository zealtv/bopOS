# Working notes for agents

bopOS is a Raspberry Pi + Pure Data framework for networked multi-device sound
installations. This file is the orientation for any agent working here.

## Start here

1. `README.md` — system overview, OSC port map, patch system.
2. `docs/OSC-CONTRACT.md` — the **ratified** OSC contract (v1.0, 2026-07-07): grammar,
   planes, identity/persistence, ports, constraints. Don't re-litigate it; the
   reasoning lives in lore item `2026-07-07-osc-schema-council`.
3. `.notes/architecture-review-2026-07-05.md` — the current architectural review and
   forward plan; the shared context every loom thread points back to.
4. `./.loom/loom status` — live task state. The loom (`.loom/`) is the task tracker;
   read `.loom/README.md` for the protocol (claim → work → tie; split when too big).
5. `.notes/dashboard-development-context.md` — full dashboard design (stack, protocol,
   UI) if working on dashboard threads.

## House rules

- **NEVER edit Pure Data patches (`.pd` files).** PD programming is Bob's domain.
  Agents work on Python, Bash, JS/HTML, architecture, and docs.
- **PD float precision:** PD's OSC floats are 32-bit. Never send a value needing >6
  significant figures (epoch timestamps, fine clocks) through PD as a float — encode
  64-bit values as strings or int pairs, and keep absolute time out of PD entirely.
- **Decision gates:** some choices are Bob's to ratify — the OSC port/namespace
  redesign, scene-language syntax, engine strategy calls, anything user-facing in the
  facilitator view. Produce a written proposal (see Lore below), mark the stitch
  `.waiting`, and surface it to Bob. Don't implement past an unratified design.
- Commit style: plain prose subject line (match `git log`), body explaining why.

## Thread ordering (critical path)

The OSC contract is **ratified** and fully implemented; the **dashboard's four phases
are all tied** (2026-07-08, incl. `/facilitator` and the meters surface — the manifest
`role` field is ratified in contract §8/§11). The `dashboard` goal stitch waits only on
Bob adopting it on a real rig.

Every active thread is decomposed into numbered children (2026-07-08 loom audit);
in-thread order is the numeric prefix. Cross-thread order for autonomous sessions:

1. **`clock-sync`** (`sync-0` → `sync-3`; `sync-4` is the hardware run, waiting) —
   head of the critical path.
2. **`spatial-audio`** (`spatial-0` → `spatial-2`; `spatial-2` needs sync-2 tied).
3. **`audition-rig`** (`audition-1`, then `audition-2`) — Linux-first; the
   port-sharing spike passed on Linux (broadcast+selector addressing only),
   `.waiting` on the macOS run. Can interleave with 1–2 (independent).
4. Free-floating fill: `samples-0..2`, `zero-0-measure-kit`, `friction-0/1`,
   `input-0-config-plumbing`.

**Paused by Bob (2026-07-08): `scene-sequencing`** — the whole thread (language,
clip grid, video-mask) waits until the foundation above lands; the language is
co-design with Bob, never solo (brief in the stitch). Also gated: the SC
proof-of-concept (`zero-2`), spatial-audio Stage B, and all hardware `.waiting`
children (`sync-4`, `zero-1`, `input-1`).
Cross-repo: spool-scoped siblings live in `kite-choir-brains/.loom` (`bopos-uptodate`) —
coordinate, don't duplicate.

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
  teardown. Deps: `pip install pyOSC3 python-osc websockets playwright
  -r dashboard/requirements.txt && playwright install chromium --only-shell`.
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
