# Ground truth — bopOS OSC schema council, 2026-07-07

Verified facts about the current system, established by reading the code in
`/home/bob/repos/bopOS` on 2026-07-07. Where a claim comes from a review doc rather
than code, it is marked. Experts: where the seed and this file disagree, this file wins.

## What bopOS is today (verified in code)

A Raspberry Pi + Pure Data framework for networked multi-device sound. Each Pi runs:
jackd + PD (the engine, running the active patch), `python/helper.py` (admin), and
`python/io/main.py` (I2C↔OSC bridge). A laptop (dashboard/controller) speaks OSC over
UDP **broadcast** to the fleet. Scale today: 2–12 devices; design intent ~50–100
(review §1).

## Port map (verified: helper.py:13-15, io/main.py:19-20, bopos.osc.pd netreceive/netsend)

| Port | Listener | Sender | Scope |
|---|---|---|---|
| 5550 | Dashboard | PD via `netsend -u -b` → 255.255.255.255 | LAN broadcast |
| 6660 | PD (`bopos.osc.pd` netreceive) | Dashboard broadcast | LAN broadcast |
| 6661 | PD | helper.py | localhost |
| 6662 | PD | io/main.py | localhost |
| 7770 | helper.py | PD (`route helper` forwards) | localhost |
| 8880 | io/main.py | PD | localhost |

All Pi→laptop traffic is **broadcast from inside PD** — Python never talks to the
laptop directly. All laptop→fleet traffic is broadcast; per-device routing happens
inside each Pi's PD (`route-by-id` on `/<id>/...` and `/all/...`; id −1 = unset).

## Message surface (verified: helper.py handlers, io/main.py handle_command, dashboard-development-context.md §3)

- **Pi → dashboard (5550):** `/hb` (every 10s, **no payload — no MAC/ID/version**;
  generated *inside PD*, so engine death looks like device death), `/aloha 1`
  (announce on boot/request), `/version <f>`, `/id <f>` (after /config), `/echo <0|1>`
  (echo-back hack), `/rpt ...`. Dashboard must correlate devices by source IP.
- **Dashboard → Pi (6660), routed by id:** patch-param legacies `gain`, `gain2`,
  `backing`, `echo` (these are **patch-specific**, not framework — Bob, round 2);
  admin verbs forwarded to helper.py on 7770: `reboot shutdown update getsamples
  addpatch patch pullpatch config checkout` (PD `route` list at bopos.osc.pd:129);
  io verbs forwarded to io/main.py on 8880.
- **helper.py (7770):** `/config` (reads `bopos.devices` CSV keyed by MAC from argv,
  sets hostname via hostnamectl, sends `/id <float>` to PD), `/update` (git pull +
  reboot), `/getsamples`, `/shutdown`, `/reboot`, `/checkout <branch>`, `/patch <name>`
  (**validates `main.pd` exists** — hardcoded PD assumption; `pkill pd; pkill jackd`;
  reboots), `/addpatch <user> <repo>` (**GitHub-only** URL construction), `/pullpatch`.
  helper.py has **no heartbeat, no clock, no liveness reply**.
- **io/main.py (8880):** `/io/create <name> <type> <hexaddr>`, `/io/poll <hz>`,
  `/io/report`, `/io/scan` (replies `/io/scan <addrs...>`); `/system/rssi|id|ip|uptime|
  rev|patch|info` (each replies on its own address to PD on 6662); `/<peripheral>/<cmd>`
  writes to a named peripheral. Sensor polling sends a bundle of `/<name> <values...>`
  at poll_rate Hz. Peripheral registry: ads1015, ads1115, lis3dh (accel), mpr121
  (captouch), ssd1306 (OLED), switch.

## Identity & positions (verified: helper.py config_callback, README)

`bopos.devices` CSV maps **MAC → hostname, ID, POSL, POSR**. Pre-registration is
required; unknown MAC = "not found", no fallback. ID travels as an OSC **float**.
Positions are already first-class data (also dashboard `installation.json` pos1/pos2 —
review §4). Bob had provisional OSC-driven ID change and endorses remote assignment
of id/position to cut install friction (ruling, 2026-07-07).

## Patch system (verified: patches/, bash/start.sh, bash/getsamples.sh)

Patches are git repos under `patches/`; `active_patch.txt` names the active one.
**Partial generalization already exists:** each patch carries a `bopos.config`
(today: just `SAMPLEPACKSURL`), `patches/default/` also has its own `start.sh`, and
`bash/start.sh` launches `pd -nogui -jack -open "$PATCH_ENTRYPOINT" -send "; RANDOM …;
STARTTIME …; ACTIVEPATCH …"`. But helper.py `/patch` still hard-requires `main.pd`,
and the engine launch is PD-only. `getsamples.sh` = **gdown from a Google Drive URL**
in the patch's `bopos.config`, unzipped into `patches/<active>/bop/samplepacks` —
internet-dependent, not local-network, sample-specific.

## Process management (verified: bash/stop.sh)

`stop.sh` is literally `pkill pd; pkill jackd; pkill python` — kills any python
including helper/io/future processes; cause of `/patch`-restart fragility.

## Hard constraints

- **PD OSC floats are 32-bit** (~6–7 sig figs). Epoch-ms timestamps cannot round-trip
  through PD. Happy Brackets ships longs as **strings** over OSC. Consequence (ratified,
  review §7): synced clock lives in **Python**; PD only ever gets small relative values.
- **Pi Zero 2 W is the constrained target**; PD is single-threaded.
- **Deployed fleets exist** (Kite Choir spool v2, The Plants via plantsOS) — migration
  cost is real; the review asks for transition aliases (e.g. `/helper` kept one release).
- **Never edit .pd files** (agent house rule; PD is Bob's domain) — but this council is
  design-only anyway.
- jackd fixed at 44.1k/512/2, `SOUNDCARD="DigiAMP"` hardcoded in start.sh (config
  belongs in `bopos.config` — long-standing TODO).

## Already-settled decisions — ground truth, do NOT re-litigate (review §4/§7, stitch)

1. `/helper/*` → `/os/*` rename, `/helper` aliased for one transition release.
2. Heartbeat moves from PD into helper.py and carries identity:
   `/hb <mac> <id> <version> [rssi]` (RSSI switchable via bopos.config).
   Engine death ≠ device death.
3. `/echo` is replaced by a deliberate liveness/latency probe in helper.py
   (`/os/ping` → `/os/pong <t>`) plus real discoverability/debug design.
4. Synced clock + cue scheduling live in Python/dashboard, never absolute time into PD.
5. Patch declares its own entrypoint (its `start.sh`/manifest); PD stays the
   *reference* engine, not the *required* one.
6. Targeted process management replaces pkill-everything.
7. An OSC-driven key/value persistence store will exist (PD sends key+values, Python
   persists and returns on load).
8. Reserved namespace sketches exist for `/sync/*`, `/cue`, `/point` (clock-sync and
   spatial-audio threads).

## Bob's rulings from this session (2026-07-07) — treat as given

- **Framing:** bopOS is a **platform-agnostic framework for networked spatial
  audio-visual systems**; Raspberry Pi is the *primary use case*, not an assumption.
  Motivating scenario: an office floor of computers taken over via live-booted Linux
  images as a spatial AV system.
- **Outputs are patch-side.** A patch may be PD, openFrameworks, SuperCollider, or
  anything else, driving monitors, LEDs, thermal printers, robotics, scent diffusion.
  The patch defines its own **patch-local OSC schema**. The framework provides
  transport/orchestration, never output semantics.
- **I2C stays first-class** — it's the convenient offboard layer for sensors, lights,
  actuators; engines do I2C badly or not at all (that's *why* it's offboarded). MIDI/
  keyboard/mouse/general IO usually arrive via the engine. **The exact framework-IO vs
  engine-IO boundary is an open question for this council.**
- **Distribution generalizes:** the sample-loading mechanism should be agnostic to the
  kind of media/data it moves; the **landing location** (where patches of any kind —
  PD, SC, OF — find delivered assets) is an important design decision.
- **Capability broadcast:** unimplemented due to perceived complexity; Bob is open to
  it but wants **concrete use cases** — he hasn't needed it in his own workflow yet.
  Justify it with uses or reject it.
- Deliverable: **judgment only** — Bob ratifies before anything is implemented.

## The open questions (the council's mandate)

A. **Responsibility statement** — a crisp definition of what bopOS the framework owns,
   vs the patch, vs the engine, vs the dashboard.
B. **First-class OSC vocabulary** — the complete set of framework message families
   (identity/assignment, discovery, capability, distribution, sync, cue/scene, spatial,
   telemetry/log, persistence, …): what's missing from Bob's current thinking, and what
   should deliberately NOT be first-class.
C. **Platform agnosticism** — what the contract must (and must not) assume so a
   live-image x86 box is a first-class citizen (identity without pre-registered MACs?
   no I2C? no WiFi/RSSI? different audio stack?).
D. **Patch parameter declaration/discovery** — how a patch declares names/ranges/
   defaults so the dashboard stops hardcoding gain/gain2/backing.
E. **Port architecture** — keep-and-document vs consolidate; migration cost per option.
F. **Framework-IO vs engine-IO** boundary (I2C first-class is given).
G. **Capability broadcast** — worth it? Concrete use cases, or a cheaper substitute.
H. **Distribution** — media/data-agnostic movement + the landing-location contract.

## Constraints any design is graded against

Solo maintainer (Bob). Artist-first workflows, increasingly agent-assisted. Performance
stability above features (the Belief System lesson: Ableton + Max for Live sequencing
was unstable and complicated — bopOS needs its own simple, reliable story). Simplicity
ethos: smallest vocabulary that works, no speculative machinery, fail loud. Deployed
fleets must have a migration path.
