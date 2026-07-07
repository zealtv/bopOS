# Expert response — the platform-agnosticism seat

## 1. Lens & altitude

I design from the office floor backwards: x86 boxes, live-booted, no persistent disk,
built-in speakers, wired Ethernet, no I2C, no WiFi, MACs nobody pre-registered — a
spatial instrument within the hour. My test for the whole contract: **the same spec must
run a Pi Zero + DigiAmp + LIS3DH and a live-booted desktop, with every difference between
them expressed as a *declared fact*, not a special case in the code.** I take a
first-principles altitude on identity, the IO boundary, and what "update" means on a
stateless host, but I land each in a concrete contract clause. Pi stays primary; nothing
here costs Pi ergonomics — every change is additive or a graceful-degradation of an
existing crash.

## 2. Problem reframing

The current system doesn't *read a contract*, it *reads hardware*, and hardcodes the
answers. `start.sh` reads `wlan0`'s MAC and hardcodes `SOUNDCARD="DigiAMP"` and
`pd … main.pd`; `rc.local` assumes user `pi`; `helper.py` gates identity on a MAC being
pre-registered in `bopos.devices` (unknown MAC → "not found", silence); `sys_i2c` opens
`/dev/i2c` and will throw where there is none; `update.sh` git-pulls a writable checkout
and reboots. Each is a place the host *asserts* a fact by crashing or lying instead of
*declaring* it.

The one bright spot shows the target pattern: `sys_wireless.read_wireless()` returns
`(None, None)` when there's no WiFi instead of exploding, and `sys_info.get_ip()` works
offline. **That degradation pattern is the entire platform-agnostic contract.** The
reframe: *the framework's job is to let a node state who it is, whether it's alive, what
it can do, and that it's converged to the intended revision — and to make "I can't do
that / I don't have that" a first-class, legal answer for every one of those.*

## 3. Proposed design

### 3a. The Node Contract — the host-assumption audit as a positive spec

A bopOS node MUST be able to provide, and the contract MAY assume ONLY, these
**declared facts** (self-reported; never inferred from hardware by the framework):

| Fact | Meaning | Pi default | Live-image default |
|---|---|---|---|
| `node_token` | stable correlation key, opaque string | primary-iface MAC | primary-iface MAC or per-boot UUID |
| `engine_launch` | how the engine starts (patch-declared) | `pd -nogui -jack main.pd` | `openframeworks ./app` / `scsynth` / … |
| `audio_out` | ALSA/jack device, or `none` | `DigiAMP` | `default` (built-in) |
| `io_buses` | offboard bus kinds present | `[i2c]` | `[]` |
| `has_wifi` / rssi | link metrics available? | yes | no → field omitted |
| `update_model` | provisioning model | `persistent` | `ephemeral` |

The contract MUST NOT assume: a WiFi interface (or any specific interface name); an I2C
bus; a Google-Drive/GitHub reachable internet; a writable git checkout; a user named
`pi`; PD; or a MAC that anyone registered in advance. Everything on that list is a fact a
node declares, and for every capability query the contract **guarantees a legal empty
answer** — `rssi` omitted, `/io/scan` returns empty, `audio_out none` — rather than an
error at boot.

### 3b. Identity without pre-registration (mandate C)

Split identity into two layers:

- **`node_token`** — always present, chosen by the node, requires nobody's cooperation.
  Preference order: persisted machine token (if disk persists) → primary outbound
  interface MAC (discovered, *not* `wlan0`-hardcoded) → random per-boot UUID. This is the
  dashboard's correlation key and **replaces "correlate by source IP."**
- **Assigned identity** (`id`, `pos`, `hostname`) — soft runtime state, pushed over OSC
  by the dashboard (`/os/assign <id> [posL posR]`), OR pre-seeded from `bopos.devices` if
  that file exists. **`bopos.devices` becomes an optional convenience seed, not a gate.**
  An unregistered node is a first-class citizen: `id = -1`, announcing its `node_token`,
  fully assignable live. Unknown MAC MUST fall back to "unassigned & announcing," never
  to silence.

DECISION for Bob: the settled heartbeat `/hb <mac> <id> <version> [rssi]` keeps its
shape; I only redefine field 1 as **`node_token` (opaque string; MAC is its default
value)** and make `rssi` optional-by-absence. Deployed Pis are byte-for-byte unchanged;
the field just stops *meaning* "a MAC that must exist in a CSV."

### 3c. The framework-IO vs engine-IO line (mandate F)

Draw the line by *stack*, not by device:

- **Framework owns the offboard peripheral-bus layer** — sensors/actuators reached over a
  host peripheral bus (I2C today; SPI/serial/GPIO tomorrow), exposed as named peripherals
  over `/io/*`. It owns this *because engines do it badly or non-portably* — that is the
  whole justification, and it's why the boundary is here and not elsewhere.
- **Engine owns media IO** — audio in/out, MIDI, keyboard/mouse/HID, monitor/GPU: things
  that arrive through the engine's own native stack and *are* the art's input/output.

A host **without I2C expresses that by declaration, not special-case**: `io_buses: []`,
`/io/scan` returns empty, and `/io/create` fails **loud** with `/io/error <name> no-bus`.
`sys_i2c` MUST degrade like `sys_wireless` already does — no bus → empty scan, no import
crash. The office box thus runs the *identical* `/io/*` vocabulary and simply reports no
peripherals; the Pi Zero reports its accelerometer. Same contract, difference is a fact.
Keep the verbs bus-agnostic (`/io/create <name> <type> <addr>`) so I2C is first-class
without being baked into the OSC surface.

### 3d. What `/os/*` verbs mean on mutable-Pi vs immutable-live-image (the boot/update story)

`git pull + reboot` isn't just meaningless on a stateless host — reboot *reverts to the
base image and destroys the bopOS install itself*. So redefine the verb, not the fleet:

> **`/os/update` is a convergence assertion, not a filesystem operation: "this node
> should now be running the published framework/patch/asset revision." WHAT is fixed by
> the contract; HOW is chosen by the node's `update_model` fact.**

- `update_model: persistent` (Pi) → git pull in place + reboot. Today's behaviour, intact.
- `update_model: ephemeral` (live-image) → re-fetch the mutable layer (patches/samples)
  into the RAM/overlay working dir and **re-exec the run state without a full reboot**; if
  a new base image is genuinely required, `/os/update` is an **honest no-op** that replies
  `/os/rev <sha> ephemeral image-managed` instead of pretending.

Verbs split into two honesty classes: **lifecycle verbs that always mean one thing**
(`/os/reboot`, `/os/shutdown`, `/os/restart-engine` — the targeted replacement for
pkill-everything, `/os/ping`→`/os/pong`), and **provisioning verbs whose mechanism is
host-declared** (`/os/update`, `/os/checkout`, distribution). Every provisioning verb MUST
reply with the resulting state (`/os/rev <sha> <model>`) so the dashboard observes
*convergence*, not fire-and-forget into a void.

### 3e. Responsibility statement (mandate A)

> **bopOS moves control and identity between a controller and a fleet of autonomous
> nodes, and guarantees each node can say who it is, whether it's alive, what it can do,
> and that it's converged to the intended revision — regardless of the hardware or OS
> image beneath it.** It owns node identity/liveness, the OSC transport and namespace, the
> convergence contract, the offboard peripheral-bus IO layer, and the sync/cue/spatial
> control plane — always as *declared facts and assertions, never as hardware or disk
> assumptions.* It does NOT own output semantics (patch), engine launch (patch-declared),
> media IO (engine), or the host's provisioning mechanism (declared, not assumed).
> Everything sonic/visual/physical is the patch's; everything about *being a networked
> node* is the framework's.

## 4. How it fits the existing system

**Stays:** the OSC-on-fixed-ports spine, broadcast liveness, `/io/*` + `/system/*`, the
patch-as-git-repo model, `bopos.config` (patch-level) and `bopos.devices` (now optional).
**Changes (all additive/degradation):** discover the primary interface instead of
hardcoding `wlan0`; `sys_i2c` degrades to empty scan; identity falls back to
unassigned-but-announcing; `update_model`, `engine_launch`, `audio_out` move from
hardcoded to declared facts (the soundcard one is already a ratified TODO). **Migration
for deployed Pi fleets:** zero behavioural change — MAC stays the default `node_token`,
`bopos.devices` stays the seed, `update_model` defaults to `persistent`, `/helper` stays
aliased one release. A Pi that never sees the office floor never notices.

## 5. Why it's right (both reference hosts, same contract)

- **Pi Zero:** `node_token`=eth/wlan MAC (seeded to id 3 via `bopos.devices`),
  `engine_launch`=`pd … main.pd`, `audio_out`=DigiAMP, `io_buses`=`[i2c]` (LIS3DH found),
  `has_wifi`=yes, `update_model`=persistent. `/os/update` = git pull + reboot.
- **Live-image desktop:** `node_token`=eth0 MAC or per-boot UUID (assigned id 3 live over
  OSC), `engine_launch`=`openframeworks ./app`, `audio_out`=`default`, `io_buses`=`[]`
  (`/io/scan` empty), `rssi` absent, `update_model`=ephemeral. `/os/update` = re-pull
  patches + re-exec engine, reply `/os/rev … ephemeral`.

Same heartbeat, same `/io/*`, same `/os/*`, same assign flow. Every divergence is one row
in the facts table. This is exactly the values: *smallest vocabulary that works* (no new
verbs — I redefined field semantics and added one facts concept), *fail loud*
(`/io/error no-bus`, honest `/os/rev`), *performance stability* (no per-host branching in
the hot path), and Pi-primary (defaults reproduce today's behaviour bit-for-bit).

## 6. Tradeoffs, risks, what I'm NOT solving

- **Risk:** `node_token` decoupled from MAC could confuse a workflow that eyeballs MACs.
  Mitigation: MAC *is* the default token value, so nothing changes until someone opts into
  ephemeral UUIDs.
- **Risk:** the honest-no-op `/os/update` on ephemeral hosts can read as "nothing
  happened." Mitigation: the mandatory `/os/rev` reply makes convergence visible.
- **NOT solving:** the live-image *build* itself; the distribution transport and landing
  location (mandate H — I only require it honour `update_model` and reply with resulting
  state); the full vocabulary (B); clock-sync internals. I set the requirements those
  seats must meet, not their designs.

## 7. Smallest first step

Add a **"Node Contract"** section to `docs/OSC-CONTRACT.md`: the declared-facts table
above plus the one governing rule — *every framework capability query has a legal empty
answer; a node never crashes or falls silent for lacking hardware.* Prove it with the two
smallest code deltas that make it true: (1) `sys_i2c.scan_bus` degrades like
`sys_wireless` (no bus → empty, no import crash); (2) read the MAC from the discovered
primary interface, not `wlan0`. That single symmetry — "no bus, no WiFi, no
registration, no PD are all legal declared states" — *is* the platform-agnostic contract
in miniature, and it lands without touching a deployed Pi's behaviour.
