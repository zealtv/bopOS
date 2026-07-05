# bopOS Architectural Review & Forward Plan — 2026-07-05

Structured from Bob's two brain dumps (evening 2026-07-04 + morning 2026-07-05), a code
review of bopOS/plantsOS, the Kite Choir usage docs, and the Happy Brackets source as a
sync reference. Plans live as threads in `.loom/` — this doc is the shared context they
point back to.

## 1. What's working (keep, don't disturb)

- **Remote update over git**: press a button → `/helper/update` → git pull + reboot. Effective.
- **Patches as git repos** (`patches/`, `active_patch.txt`, `/addpatch` `/patch` `/pullpatch`).
- The plantsOS → bopOS reconvergence (2026-06) — bopOS is canonical, I2C-direct architecture.
- Scales 2–12 devices today; design intent is ~50–100 (Kite Choir performance system).

## 2. Current deployments / use cases

| Deployment | Repo / context | Notes |
|---|---|---|
| **Kite Choir spool v2** | `kite-choir-brains` (docs/bopos.md, loom `bopos-uptodate`) | Pi Zero 2 W + DigiAmp+ + LIS3DH/button/OLED; the current driver of bopOS work; RSSI first-class decision made there |
| **The Plants** | `plantsos` (fork, migrating back) | Garden installation lineage; source of the patch system + io bridge |
| **belief** (reference) | Happy Brackets + Pi Zeros, not bopOS | Prior art for synced start + moving-point/radius spatial gain |

Note: the bopOS planning items were **not in the HQ loom** (searched — nothing there). The
live ones are in **kite-choir-brains' loom** (`bopos-uptodate` → `osc-contract-pd-agnostic`,
`pi-zero-bringup`, `pi-zero-optimisation`, `default-patch-converge`). Those stay where they
are (they're spool-scoped and cross-linked from kite-choir docs); the bopOS-generic side of
each is now covered by local threads here, cross-referenced both ways.

## 3. The friction list (from the brain dumps)

1. **CPU overhead** — PD is single-threaded; Pi Zero 2 W is the constrained target.
2. **Engine agnosticism** — keep bopOS working whether or not the sound engine is PD.
3. **OSC schema tidy-up** — `/helper` → `/os`, consistent namespaces, written contract.
4. **Forward-synchronised clock** — WiFi latency breaks tight cue triggering today.
5. **Spatialised sound** — synced simultaneous start + moving point/radius controlling per-device gain (the belief technique).
6. **Non-technical musicians** — PD → GitHub → headless-Pi-over-OSC is a steep path.
7. **Audio input** — DigiAmp+ is out-only, and jackd is launched playback-only (`-P`); input is part hardware choice, part config.
8. **Dashboard as keystone** — primary interface for patches, devices, framework updates, spatial X/Y arrangement. Design already drafted in `.notes/dashboard-development-context.md`.

## 4. Review findings (code-level)

- **Already ~90% PD-agnostic.** All laptop↔Pi and Pi-internal traffic is OSC on fixed
  ports. The PD-bound residue: (a) `start.sh` assumes `pd -nogui -jack main.pd`;
  (b) the **heartbeat is generated inside PD** (`bopos.osc.pd` → netsend 5550) — kill PD
  and the device looks dead even though helper.py and the io bridge are fine.
- **Heartbeat carries no identity.** `/hb` has no MAC/ID payload; the dashboard must
  correlate by source IP. This is the single cheapest Pi-side change with the biggest
  dashboard payoff: move the heartbeat into Python (helper.py) and include
  MAC/ID/version/RSSI. That also fixes the engine-agnosticism residue (a Pi without PD
  still heartbeats) and lands the kite-choir RSSI decision in the right place.
- **PD float precision is a hard constraint for sync.** PD's OSC floats are 32-bit
  (~6–7 sig figs). Epoch-millisecond timestamps **cannot** round-trip through a PD patch.
  Happy Brackets hit the same wall (they send longs as *strings* over OSC — see below).
  Consequence: the synchronised clock must live in **Python (helper.py)**, and PD should
  only ever receive **small relative values** ("fire in 843 ms"), never absolute times.
- **`stop.sh` is `pkill pd; pkill jackd; pkill python`** — indiscriminate; kills any
  Python including future dashboard-adjacent processes; already caused the
  `/patch`-restart fragility (helper must `setsid` itself around its own death).
- **jackd fixed at 44.1k/512/2, playback-only, DigiAMP hardcoded in start.sh** — soundcard
  and capture config belong in `bopos.config` (long-standing TODO).
- **Positions are already first-class** (`bopos.devices` POSL/POSR, dashboard
  `installation.json` pos1/pos2) — the spatial-audio feature has its data model waiting.

## 5. Sync reference: how Happy Brackets does it

Read from source (`net.happybrackets.core.Synchronizer`, plus the newer
`core.scheduling.HBScheduler`/`DeviceSchedules`). Two generations:

**Gen 1 — `Synchronizer` (the one used for belief-era triggering):**
- Every device broadcasts every ~1s: `s <myMAC> <sendTimeMs>`.
- Every *other* device replies by broadcast: `r <srcMAC> <origSendTime> <myMAC> <myTimeNow>`.
- The original sender, on receiving a reply, computes:
  `roundTrip = now - origSendTime`; `oneWay = roundTrip / 2`;
  `offset = (replierTime + oneWay) - now`.
- **Leader election is trivial**: highest MAC string wins; everyone slews toward the
  leader's clock. Corrections split into a fast `timeCorrection` and a slow
  `stableTimeCorrection` (folded in every 20 rounds) so the clock is stable long-term but
  responsive short-term.
- Scheduled events: `doAtTime(runnable, t)` — wait `t - correctedTimeNow()` locally, then fire.
- **The mysterious appended long integer:** timestamps are appended to trigger messages
  as the *synchronised time at which to act*; each device converts that shared time to a
  local delay against its corrected clock. They're encoded as **strings** because OSC
  (and PD) mangles 64-bit longs.

**Gen 2 — `HBScheduler`:** same idea, but the clock is a monotonic uptime-based scheduler
(immune to NTP/wall-clock jumps) adjusted by `adjustScheduleTime(amount, slew_duration)` —
corrections are *slewed* over e.g. 500 ms rather than stepped, so running audio doesn't
glitch. Stratum values pick the leader.

**Recommendation for bopOS** (detailed in the `clock-sync` thread):
- Clock lives in **helper.py** (or its successor), NOT in PD; monotonic
  (`time.monotonic()`), never wall clock.
- The **dashboard backend is the natural leader** (it already exists as the single
  laptop-side process) with HB-style ping/reply offset estimation per device;
  fall back to leaderless MAC-election only if dashboard-less operation demands it.
- Cue API: dashboard sends `/cue <cueId> <sharedTimeAsString-or-two-ints>`; helper.py
  converts to a local deadline and, at the deadline, fires a plain localhost OSC message
  (`/cue <cueId>`) at whatever engine is listening. Engine stays fully agnostic; PD never
  sees a timestamp. Slew corrections, never step, while audio runs.

## 6. Spatial audio (the belief technique, bopOS-shaped)

Mechanism from belief: start the same sound on all devices simultaneously (needs the
synced clock), then move a point (or path) through the room; each device's gain =
falloff(distance(point, device)). Two candidate homes:

- **A. Dashboard-computed (recommended first):** backend knows every position
  (`installation.json`) and already sends `/gain`; add a "spatial automation" layer that
  moves a point and broadcasts per-device gains at ~20–30 Hz. **Zero Pi-side changes**;
  works with today's patches; the dashboard spatial map doubles as the authoring UI.
- **B. Pi-computed (later, for scale/autonomy):** broadcast `/point <x> <y> <radius>`
  once per frame; each Pi computes its own gain from its own position (delivered via
  `bopos.devices`/OSC). One message instead of N; works at 50–100 devices; survives
  dashboard hiccups. Requires a small engine-side or helper-side falloff computation.

A→B is a clean evolution; the OSC shape of B should be sketched in the contract now.

## 7. Where things live (the agnosticism ruling)

| Concern | Home | Why |
|---|---|---|
| Synced clock, offsets, cue scheduling | Python (helper) + dashboard backend | PD float limits; engine-agnostic; survives engine swap |
| Heartbeat + identity + RSSI | Python (helper) | device liveness ≠ engine liveness |
| Audio generation, falloff DSP, sample playback | patch (engine) | that's what patches are for |
| Spatial automation (moving point), presets, cue authoring | dashboard backend | it's control data, positions live there |
| jack/soundcard/capture config | `bopos.config` | per-deployment hardware fact |

## 8. Thread map (see `.loom/threads/`)

- `dashboard` — the keystone; 4 phased children (core → spatial/facilitator → discovery → patch mgmt). Design: `.notes/dashboard-development-context.md`.
- `clock-sync` — forward-synchronised clock + cue scheduling (HB reference above).
- `spatial-audio` — moving-point gain automation; depends on clock-sync + dashboard phase 2.
- `osc-schema-contract` — `/helper`→`/os`, heartbeat-with-identity in Python, written OSC contract; generalised patch entrypoint. (Overlaps kite-choir `osc-contract-pd-agnostic` — coordinate, don't duplicate.)
- `patch-workflow-friction` — musician-friendly patch path (dashboard-first: add/switch/update patches without git/terminal).
- `audio-input` — capture support: jackd flags + soundcard/capture in `bopos.config`; hardware guidance (which HATs have line/mic in).
- `pi-zero-performance` — CPU headroom on Zero 2 W: measure first (xruns, top), then tune jackd/-p/-r, patch cost, poll rates; survey alternative engines (SuperCollider et al.) only if PD can't hold.

## 9. Open questions for Bob

- zil.co appears to be a parked/for-sale domain now — where does belief's documentation
  actually live? (Not blocking; the technique is captured above.)
- Dashboard-as-leader for the clock: acceptable that tight-sync features require the
  dashboard backend running? (Pis stay autonomous for everything else.)
- Musicians' path: is "musician uses only the dashboard, Bob handles patch authoring in
  PD" the target, or do we also want a patch-template/starter-kit story?
