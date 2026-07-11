# Working notes for agents

bopOS is a Raspberry Pi + Pure Data framework for networked multi-device sound
installations. This file is the orientation for any agent working here.

## Start here

1. `README.md` — system overview, OSC port map, patch system.
2. `docs/OSC-CONTRACT.md` — the **ratified** OSC contract (v1.1: 2026-07-07 base +
   the 2026-07-11 seam amendment): grammar, planes, provided terms (§4.1),
   identity/persistence, ports, constraints. Don't re-litigate it; the reasoning
   lives in lore items `2026-07-07-osc-schema-council` and
   `2026-07-10-patch-seam-council`.
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

The OSC contract is **ratified** (v1.1 — the seam amendment landed 2026-07-11;
§4.1 provided terms are **implemented**: master via `seam-2`, `/pt` via
`seam-3`, both tied 2026-07-11); the **dashboard's four phases are all tied** (2026-07-08, incl. `/facilitator` and the meters surface —
the manifest `role` field is ratified in contract §8/§11). The `dashboard` goal
now waits via its blocker child `dashboard-6-rig-adoption.waiting` (Bob adopting
it on a real rig).

Every active thread is decomposed into numbered children (2026-07-08 loom audit);
in-thread order is the numeric prefix. Cross-thread order for autonomous sessions:

1. **`clock-sync`** — **software complete (2026-07-09, `sync-0`→`sync-3` tied):**
   wire shape in contract §3.1; dashboard is the leader (offset estimate + push);
   helper.py pongs, slews, fires cues; `tools/sync_measure.py` is the jitter
   harness. Only `sync-4` (hardware run) remains, `.waiting` on Bob/a rig. The
   `/cue` PD receiver is a pending pd-edit (see handoff).
2. **`patch-seam`** — **the active head.** The 2026-07-10 seam council (tied
   `seam-0-council`) re-drew the bopOS↔patch boundary: bopOS provides terms,
   never composes them into patch params; no backwards compat (patches
   rewrite in lockstep); one engine instance clones N positioned elements.
   Bob ratified the amendment 2026-07-11 (`seam-1` tied — v1.1 live).
   **`seam-2` (master term) and `seam-3` (node-side `/pt`) tied 2026-07-11**:
   `python/pointfield.py` is the shared decomposition module, helper/simfleet
   both consume it, ws surface is `set_points`/`set_point`/`clear_point`.
   Remaining: `seam-4` then `seam-5`, in numeric order. `spatial-1`
   (authoring UI, gate now open) and `spatial-2` (synced start) are claimable
   after them. Bob's element-dot UI direction (colour = element index,
   number = device) is recorded in `seam-3`'s instructions (tied). PD edits
   live in the top-level `pd-edits-for-bob.waiting` stitch
   (`.notes/pd-edits-for-bob.md` — A5/A6 now carry the live spellings).
3. **`audition-rig`** (`audition-1`, then `audition-2`) — Linux-first; the
   port-sharing spike passed on Linux (broadcast+selector addressing only),
   `.waiting` on the macOS run. Can interleave with 1–2 (independent).
4. Free-floating fill: `samples-0..2`, `zero-0-measure-kit`, `friction-0/1`
   (`hw-onboarding-doc` tied 2026-07-11 → `docs/HARDWARE.md`),
   `dashboard-5-position-precision` (numeric position entry + space origin,
   Bob 2026-07-11 — deliberately last).

Bob's rulings (2026-07-08): order above confirmed; **`audio-input` deferred**
(both children `.waiting`); `/sync/*` wire shaping is delegated (record
additively, flag in handoff); starter-kit template lives in `templates/` in
this repo; a dev Pi is ssh-reachable during development for hardware stitches
(confirm the host in-session — don't bake "ask via gremlin" steps into loom
instructions); audition rig is Linux-first now, but **macOS is the likely
installation/performance platform** — the macOS spike/relay question stays
strategically live.

**Paused by Bob (2026-07-08): `scene-sequencing`** — the whole thread (language,
clip grid, video-mask) waits until the foundation above lands; the language is
co-design with Bob, never solo (brief in the stitch). Also gated: the SC
proof-of-concept (`zero-2`) and all hardware `.waiting` children (`sync-4`,
`zero-1`, `input-1`). (Spatial "Stage B" no longer exists — node-side is the
ratified primary model, implemented via `patch-seam/seam-3`.)
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
