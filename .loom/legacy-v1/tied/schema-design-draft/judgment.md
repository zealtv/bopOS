# Judgment — bopOS OSC schema council

> **Ratified 2026-07-07 with amendments — see `ratification.md` (authoritative
> delta) and `docs/OSC-CONTRACT.md` (merged spec).** Notably: Crux 1 amended —
> node-side persistence is required, standalone operation is first-class.

Judge: fable (orchestrator, inline), 2026-07-07. Inputs: `ground-truth.md`, five
expert designs, and direct re-verification against the code. Deliverable per Bob's
framing ruling: **judgment only — Bob ratifies before `docs/OSC-CONTRACT.md` is
written.** `DECISION:` markers flag what is specifically Bob's to ratify.

## 1. Fact adjudication

Every load-bearing claim I re-checked against the repo held:

- Identity gates on `bopos.devices` with **silence** as the failure mode — unknown MAC
  prints "not found" and does nothing (`helper.py:47-48`). CONFIRMED.
- `/patch` hard-requires `main.pd` (`helper.py:111`) and reboots via
  `pkill pd; pkill jackd` + `systemctl reboot` (`helper.py:127,141`). `/addpatch` is
  GitHub-URL-only (`helper.py:160`). CONFIRMED.
- `start.sh` hardcodes `wlan0` (line 12), `SOUNDCARD="DigiAMP"` (9), `main.pd` (50),
  and `/home/pi` paths (48); it already passes startup context via `-send "; RANDOM …;
  STARTTIME …; ACTIVEPATCH …"` (104) — the hook the assets-root handoff reuses. CONFIRMED.
- `stop.sh` is literally `pkill pd; pkill jackd; pkill python`. CONFIRMED.
- The degradation asymmetry platform-agnostic built on: `sys_wireless.read_wireless`
  returns `(None, None)` without WiFi, while `sys_i2c.scan_bus` opens `SMBus(bus)`
  *outside* its per-address try — no `/dev/i2c-1` throws uncaught. CONFIRMED.
- PD routing: `netreceive -u -b 6660`, broadcast `connect 255.255.255.255 5550`,
  admin `route reboot shutdown update getsamples addpatch patch pullpatch config`
  (`bopos.osc.pd:129`), `route-by-id` with `-1` unset. CONFIRMED.
- helper.py has no heartbeat, no ping, no liveness reply — the handler list is the
  eight admin verbs only. CONFIRMED.
- Distributed-systems' wire physics (802.11 broadcast at lowest basic rate, no
  MAC-layer ACK/retransmit; NetworkManager MAC randomization defaults; switch
  broadcast storm-control) are PLAUSIBLE-to-CONFIRMED from general knowledge, not
  repo-verifiable; nothing in the ruling depends on their exact magnitudes, only on
  "broadcast is lossy and scarce," which is safe.
- Performer-ux's `/os/mute`-via-amixer assumes a controllable mixer; on x86 the
  mechanism differs. The expert flagged this honestly; the ruling keeps the
  *guarantee* and lets the mechanism vary.

No design was invalidated by a false premise. The council's value is in the spread,
adjudicated below.

## 2. The crux

Two decisions carry everything:

**Crux 1 — where assignment authority lives.** The office-floor scenario (stateless
live-boot boxes) makes node-side persistence impossible *in general*, and DHCP churn
makes IP-correlation wrong. The only design that survives every failure scenario is
**dashboard-authoritative assignment: a persistent `uid → assignment` table at the
dashboard, pushed via an idempotent, full-state `/os/assign`, re-pushed on every
re-hello.** This flips the dashboard from a viewer into the fleet's source of truth —
the single biggest conceptual change in the contract, and it must be decided before
dashboard-3's assign flow is built.

**Crux 2 — the framework/patch boundary as a wire token.** Bob's ruling ("the
framework provides transport/orchestration, never output semantics") only becomes
enforceable when the boundary is *visible in the address*: closed framework planes
(`/os` `/io` `/sync` `/cue` `/point`) vs one open patch plane (`/p/*`), with the
**patch manifest** as the keystone that lets the dashboard build controls for a patch
it has never seen. Everything artist-facing (no more hardcoded gain/gain2/backing, no
CSV evening) falls out of this one move.

## 3. Ruling

A synthesis — protocol-designer's grammar as the skeleton, distributed-systems'
identity/transport mechanics as the muscle, platform-agnostic's declared-facts rule as
the constitution, performer-ux's install-day verbs kept, simplicity's rejections
upheld almost wholesale.

### A. Responsibility statement

> bopOS moves control and identity between a controller and a fleet of autonomous
> nodes. It guarantees each node can say **who it is, whether it's alive, what it can
> do, and that it has converged to the intended revision** — always as *declared
> facts*, never as hardware or disk assumptions. It owns identity/liveness, the OSC
> transport and namespace, convergence (update/checkout/fetch), the offboard
> peripheral-bus IO layer, and the sync/cue/spatial control plane. Everything that
> comes out of the speakers, LEDs, printer, or monitor is the patch's; engine launch
> is patch-declared; media IO (MIDI/HID/audio-in) is the engine's; control-plane
> state, spatial math, and scene authoring are the dashboard's.

Governing rule (platform-agnostic's, adopted verbatim): **every framework capability
query has a legal empty answer; a node never crashes or falls silent for lacking
hardware.** No WiFi → `rssi` absent. No I2C → `/io/scan` empty, `/io/create` →
`/io/error <name> no-bus`. No registration → unassigned-and-announcing, never silence.

### B. Grammar and vocabulary

One addressing rule (protocol-designer):

```
/<selector>/<plane>/<member>  args…    controller → fleet   (selector: all | <id>)
/<plane>/<member>             args…    node → controller    (source identifies sender)
```

Six planes, closed set except the last:

| plane | owner | contents |
|---|---|---|
| `/os/*` | framework | identity, liveness, admin, discovery, persistence, distribution — absorbs `/helper/*` **and `/system/*`** |
| `/io/*` | framework | offboard bus peripherals (verbs already bus-agnostic) |
| `/sync/*` | framework (Python) | clock offset — reserved, shaped by clock-sync thread |
| `/cue` | framework (Python) | discrete scheduled fires; engines only ever see relative ms; re-triggerable, no envelopes |
| `/point` | framework/dashboard | dumb spatial geometry `<x> <y> <radius>` — **reserved now, implemented later** (see E) |
| `/p/*` | **patch** | the only place output semantics live; `gain`/`gain2`/`backing`/`echo` move here |

Deliberately NOT first-class (simplicity's list, upheld): scene/sequencing language,
video-mask authoring, telemetry/log streaming, a capability registry, spatial falloff
math, a separate discovery handshake family, pre-minted `/gpio` `/midi` `/serial`.

### C. Identity & assignment (Crux 1 resolved)

- **`uid`** — opaque stable string the node chooses: persisted machine token →
  primary-interface MAC (discovered, not `wlan0`-hardcoded) → per-boot UUID. On every
  deployed Pi, `uid == MAC`: byte-for-byte compatible with the settled heartbeat.
- **Assignment** (`id`, `name`, positions) lives in a **persistent dashboard table
  keyed by `uid`**, seeded from `bopos.devices`, which is demoted to an optional seed
  — never a gate. IP is a return path, never identity.
- **`/all/os/assign <uid> <id> <name> [posx posy pos2x pos2y]`** — idempotent,
  full-state (positions ride in it; no separate `/os/pos` verb). Re-sending is always
  safe. **Control-plane law: every fleet command is full-state and idempotent; no
  increments.**
- Unassigned nodes take `id = -1` and heartbeat **fast (~2 s)** until assigned, then
  drop to 10 s. The fast heartbeat *is* discovery/hello and absorbs `/aloha` — one
  payload shape, no separate hello family (simplicity + dist-sys, synthesized).
- **Node-side caching, adjudicated:** nodes with persistent disk MAY cache their
  assignment via the ratified k/v persistence store so a dashboard-less autonomous Pi
  install still boots into identity; stateless boxes simply re-hello and get re-pushed.
  Dashboard remains authoritative wherever both exist.

Heartbeat (extends the settled shape by one field, strings from Python so no float
limit): **`/hb <uid> <id> <version> <engine-alive 0|1> [rssi]`** — sent by helper.py
**directly to 5550**, not through PD's netsend, so engine death ≠ device death and
the `engine-alive` flag tells the artist "box up, engine crashed" from "box gone."
`rssi` optional-by-absence.
**DECISION (Bob):** ratify the `engine-alive` field and fast-heartbeat-when-unassigned.

### D. Patch manifest (Crux 2 keystone)

One JSON manifest in the patch repo root — `bopos.patch.json` — declaring `engine`,
`entrypoint` (subsumes settled decision 5), `params` (name/type/min/max/default/
group), optional capability tags, and asset slots. helper.py serves it verbatim:
`/<id>/os/params` → `/os/params <json>` (the existing `/system/info` request/reply
pattern, reused). The dashboard renders controls from the declaration; a patch with no
manifest falls back to today's three sliders with a visible "undeclared" badge; a
`/p/*` value hitting an undeclared name gets a loud badge, not a guess. Rejected
unanimously and upheld: runtime param introspection / announce-push protocols.
**DECISION (Bob):** manifest filename/format (JSON, one file) — it's the
artist-facing authoring surface.

### E. Ports & transport

**Keep all six ports and their numbers. Unanimous — treat as settled.** The smell was
undocumented magic numbers, not socket count: the contract doc records the two LAN
ports (5550 up / 6660 down) as the public contract and the four localhost ports as
internal plumbing; symbolic names in config later is a refactor, not protocol.
Consolidation and renumbering are both rejected (flag-day risk on invisible plumbing;
breaks the audition rig's port sharing).

Transport discipline (dist-sys, adopted): **broadcast** only for low-rate, idempotent,
genuinely one-to-many messages (`/hb`, `/os/assign`, `/all/*` admin, `/cue`, `/point`);
**unicast to the requester** for all request/reply traffic (`/os/pong`, `/os/report`,
`/os/params`, fetch results). Spatial at fleet scale must be the broadcast `/point`
with node-side falloff (one 30 Hz 3-float message, not N×30 Hz per-device gains) —
but dashboard-computed per-device `/p/gain` ships **first** and remains correct for
≤12 nodes and the audition rig. `/point`'s grammar is reserved now so the scale path
is a drop-in, resolving spread 5 in favour of both sides' actual claims.

### F. IO boundary

Framework owns what is **offboard and bus-addressed on the node** (`/io/*`: I2C today;
SPI/GPIO/serial later through the same registry pattern — engines do this badly,
which is the entire justification). Engine owns its native media IO (audio, MIDI,
HID, display); if engine-side input must reach the fleet or dashboard it surfaces as
`/p/*`. No-bus is a declared legal state (see A). Code fix implied: `sys_i2c` must
degrade like `sys_wireless` already does.

### G. Capability — rejected as a subsystem, resolved as a pull

No capability broadcast, no registry, no caps list bloating the heartbeat. Static
facts are **pulled**: `/<id>/os/report` → `/os/report <json>` (engine, has_i2c,
has_wifi, audio_channels, screen, patch, uptime, git-rev, contract-version,
update_model). The heartbeat carries only the live-changing minimum (engine-alive,
rssi). The concrete uses Bob asked for, all served by the pull + manifest: hide RSSI
column for wired nodes; hide I2C UI where there's no bus; refuse pushing a PD patch
to an SC-only node; route text cues only to screen-bearing nodes; asset-presence
drives distribution diffing.

### H. Distribution & landing

Generalise `getsamples` to **`/<id>/os/fetch <source-uri> <slot>`** →
`/os/fetched <slot> <ok|err>`. Source dispatches on URI scheme: `gdrive:` survives as
an ingest source, but the fleet-scale path is the **dashboard serving LAN HTTP with a
manifest (files + hashes), nodes pulling by diff with Range-resume** — no cloud on
the critical path, works air-gapped.

**Landing (the decision Bob flagged), adjudicated for dist-sys:** assets land in a
**framework-owned, engine-neutral root outside the patch git tree** —
`~/bopOS/assets/<slot>/` — handed to every engine at launch (env var + an `ASSETS`
startup message alongside the existing `ACTIVEPATCH`/`RANDOM` sends). Rationale over
the in-patch-tree option: big binaries don't belong in a patch's git repo (they break
the patch-as-git-repo distribution model), and one predictable root serves PD, SC,
and oF identically. Legacy `patches/<active>/bop/samplepacks` is symlinked for one
release. **DECISION (Bob):** ratify the neutral-root landing convention.

### Convergence & lifecycle verbs

`/os/update` is a **convergence assertion, not a filesystem operation**: persistent
hosts git-pull + reboot (today's behaviour, unchanged); ephemeral hosts re-fetch the
mutable layer and re-exec, or honestly no-op. Every provisioning verb replies
`/os/rev <sha> <model>` so the dashboard observes convergence rather than
fire-and-forget. Lifecycle verbs always mean one thing: `/os/reboot`, `/os/shutdown`,
`/os/restart-engine` (the targeted replacement for pkill-everything), `/os/ping
<token>` → unicast `/os/pong <token> <uid>` (retiring `/echo`, as settled).

Performer-ux's two artist-facing verbs, accepted:
- **`/os/identify <uid>`** — chirp/flash to physically locate a box; the
  highest-leverage install-day primitive (50 boxes named in under an hour, no CSV
  evening). **DECISION (Bob):** user-facing behaviour — ratify.
- **`/os/mute <0|1>`** — the one framework-owned output control: a transport-level
  panic button below patch logic (amixer on Pi; degrades to engine-restart where no
  mixer exists). Muting the transport is not output *semantics*; it's the kill switch
  the Belief System lesson demands. **DECISION (Bob):** this deliberately bends the
  "outputs are patch-side" ruling for exactly one verb — ratify or strike.

### Rejected, and why (so it stays rejected)

Port consolidation and renumbering (cost without benefit, unanimous); capability
broadcast/registry (speculative machinery; pull suffices); params announce-over-OSC
(PD introspects badly, duplicates the manifest); telemetry/log streaming (heartbeat
absence is the alarm; SSH exists); envelope-carrying cues (crossfades are dashboard
param automation — discrete and continuous stay separate); a separate hello handshake
family (fast heartbeat is discovery); per-device spatial gain broadcast at fleet
scale (airtime math kills it).

### Migration (deployed fleets: Kite Choir, The Plants)

Zero port changes. `uid == MAC` so heartbeats stay compatible. `/helper/*` → `/os/*`
and bare `/gain` → `/p/gain` each aliased one release, then deleted. `bopos.devices`
keeps working as the seed. Old samplepacks path symlinked one release. A patch
without a manifest still gets the legacy three sliders. No flag day, no reflash.

## 4. Smallest first slice

After ratification, in order:

1. **Write `docs/OSC-CONTRACT.md`** from this judgment (the stitch's deliverable):
   grammar rule, plane table, node-contract facts table, message shapes, port map
   as-is, transport discipline, migration aliases.
2. **Prove the two cruxes in `simfleet`** (no hardware): (a) fast-hb → `/os/assign` →
   reboot a fake node → watch it re-hello and recover identity with nothing persisted
   node-side; (b) `bopos.patch.json` in the `default` patch + `/os/params` reply +
   dashboard rendering sliders from the declaration.
3. Two tiny code deltas that make the Node Contract true today: `sys_i2c` degrades
   like `sys_wireless`; MAC read from the discovered primary interface, not `wlan0`.

Everything else — unicast replies, `/point`, manifest distribution, `/os/mute` —
layers on after and is independently shippable.

## 5. Open DECISION list for Bob (collected)

1. `engine-alive` heartbeat field + fast-heartbeat-when-unassigned (C).
2. Manifest name/format: `bopos.patch.json`, JSON, one file (D).
3. Landing convention: framework-owned neutral assets root, `~/bopOS/assets/<slot>/` (H).
4. `/os/identify` chirp-to-locate (user-facing).
5. `/os/mute` — the one framework output verb; ratify the exception or strike it.
6. Dashboard becomes the fleet's source of truth for assignment (Crux 1) — the
   conceptual shift underlying dashboard-3.
