# ESP32-S3 as a bopOS node — protocol feasibility

**Verdict: yes, and more cleanly than expected, because the contract was
already written for it.** The expensive parts are not the protocol.

Everything below is read against `docs/OSC-CONTRACT.md` v1.17 and the node
source at commit `ecded85`. Hardware figures are asserted from general
knowledge, not measured — see the provenance note on the item card.

## 1. The structural finding

Contract §4 says it outright: the two LAN ports (5550/6660) are **"the public
contract"**; 6661/6662/7770/8880 are **"one device's internal plumbing"**.

So an ESP32 node needs no localhost OSC loop, no second process, and no engine
in the launchable sense. **The framework layer and the engine collapse into one
firmware image, and nothing outside the box can tell.** It speaks exactly two
UDP ports; everything else is an internal function call.

Three more places where the contract already anticipates a non-Pi host:

- **§2 declares facts, never infers hardware.** The fact table has a
  "Live-image default" column beside the Pi one, and `uid`, `engine`,
  `entrypoint`, `audio_out`, `io_buses`, `has_wifi`/`rssi`, `update_model` are
  all self-reported. An S3 answers each one honestly and is a legal node.
- **§1's governing rule**: *"every framework capability query has a legal empty
  answer; a node never crashes or falls silent for lacking hardware."* An S3
  declaring `io_buses: []` is legal-empty, not degraded.
- **§14 rejects per-host branching in message semantics** — *"differences are
  declared facts, never special cases."* An S3 node needs no branch anywhere in
  the dashboard. That is the test it passes, and it is the one that matters.

There is also a quiet gift in §12. The contract sends all 64-bit time values as
**decimal strings** because Pd's OSC floats are 32-bit. That decision was made
for Pd; it happens to be exactly what a microcontroller wants. `strtoll` and
you are done. No 64-bit float, no endianness question, readable in a log.

## 2. The obligations, costed

### Cheap — plumbing, a weekend each

| obligation | contract | on an S3 |
|---|---|---|
| `/hb <uid> <id> <version> <engine-alive> [rssi]` | §6 | trivial; `uid == MAC` as on the Pi; `rssi` native via `esp_wifi_sta_get_ap_info` |
| `/all/os/assign`, `unassign` | §5 | trivial; persist to NVS |
| `/all/os/to <uid> <verb>` envelope | §5, §6 | trivial dispatch; three verbs need thought, see §4 below |
| `/os/report <json>` | §6 | small JSON builder; this *is* the capability story — pull, not broadcast |
| `/os/store` / `/os/load` | §10 | NVS key/value |
| `/os/identify` | §6 | onboard LED + a click straight through the DAC. Worth noting the firmware owns this, so it always works — on the Pi it is patch-side (`/notify identify` → `r bopos-notify`) and was found **missing on Ciro Toast** in the 2026-08-05 incident |
| **sync plane** `/sync/ping` → `/sync/pong`, `/<id>/sync/offset` | §3.1 | echo `seq` and `leaderTimeNs` verbatim (the leader stays stateless), reply `esp_timer_get_time() * 1000` as a decimal string, slew toward the pushed offset. The ns-resolution is not mandated — only that it is a monotonic ns count |
| `/pt` point proximity | §4.1 | port `python/pointfield.py` — **126 lines** |
| `/os/master` | §4.1 | one multiply in the output stage |

**The output gate is a genuine win.** §6 calls it safety-critical and
*"enforced below patch logic"*; the Pi does it with amixer and the contract
notes it *"degrades to engine-stop where no mixer exists"*. On an S3 you
multiply in the I2S write path **and** pull the amp's hardware shutdown pin.
That is a truer implementation of the stated intent than the Pi has — and the
2026-08-05 Ciro Toast investigation found `amixer -c sndrpihifiberry
scontrols` is **empty** on HiFiBerry DAC boards, so that fleet's gate is already
software-only.

### Real work, but bounded

**`/e/*` event plane (§3.2) — the trigger layer, and the whole point.**
`deadlineNs = sharedTimeNs + offsetNs`, the `"0"` fire-on-arrival sentinel,
0–3 free-form float elements, the late-grace policy. A FreeRTOS
high-priority task does this with less jitter than the Pi's path, which runs
Python → localhost UDP → Pd's 64-sample control scheduler.

Worth stating plainly, because it is the strongest single argument: **the Pi's
two-device forward-sync timing has never been measured on hardware.**
`44-event-plane/5-pd-adoption` was tied on Bob's *"that's tested on pd locally.
good enough"*, and its `verification.md` records the split deliberately — arity
0/1/2/3 across the rig, the `"0"` sentinel's audible latency, and two-device
sync, *the thing cues existed for*, all unmeasured. An S3 node would plausibly
be the tighter of the two, and building one would force that measurement.

**§3.3 automation grammar — port all of it, do not subset.**
`python/paramgen.py` is **430 lines**: fades, segment lists, `loop`, `stop`,
six LFO shapes, clock-anchored phase, curve exponents, int-crossing emission,
catch-up. Pure float math, no dependencies.

The reason not to subset is a contract argument, not a taste one. An unconsumed
**patch parameter** is a legal no-op (§1 seam law — *"a patch that doesn't
consume a term simply isn't controllable by it"*). But the automation grammar
is **framework-owned**, not patch-owned. A node that receives
`lfo sine 0 1 2s` and silently treats it as a constant is not empty, it is
**wrong** — and wrong quietly, which is the worst failure this repo keeps
finding. Subsetting therefore needs a declared fact plus dashboard gating, i.e.
a contract revision. 430 lines of arithmetic is cheaper than that revision.

**`/os/fetch` (§9) — the expensive one, and it should be split.**
`python/fetcher.py` is only **294 lines** and the wire format is modest: a
manifest of `{path, size, sha256}`, diff against local, HTTP Range-resume,
hash-verify, prune-to-manifest. `esp_http_client` + hardware SHA-256 + FATFS
covers it.

The question is not whether it can be written but whether the node should pull
**hundreds of megabytes of samples** over 2.4GHz. The repo's own field history
argues for splitting the tiers: **both** distribution incidents in `CLAUDE.md`
— Ciro Toast 2026-08-05 and Finn Jet 2026-08-13 — were **stale manifests**, not
stale samples. The lesson recorded there is *"a manifest hard break reaches the
field at the speed of patch distribution, not of the sweep that made it"*, and
the failure mode is a crash-loop.

Patch manifests are kilobytes. So: implement `patch:<name>` fetch over the
network, and let heavy media arrive on the card. That converges exactly the
thing that has actually broken twice, and skips the transfer that would be
slow. See `open-questions.md` — how the dashboard should *describe* a node
whose media is sideloaded is a real gate, not a detail.

One convenient measured fact for the media side: `manifest.validate()` passes
unknown top-level keys through untouched (`python/manifest.py`, the `validate`
body only checks known keys and returns the mutated dict). **ESP32 sample
bindings can ride inside the same `bopos.patch.json` without touching the
Pi-side validator.**

## 3. Effort

Asserted, not measured. Roughly:

| piece | lines of C, order of |
|---|---|
| OSC codec for the used subset | 400 |
| framework layer — identity, hb, admin, persistence, sync | 1500 |
| paramgen port | 600 |
| sampler, mixer, SD/PSRAM voice management | 1200 |
| fetch (patch tier) | 400 |

~4–5k lines of ESP-IDF C. Weeks, not months, for someone fluent in ESP-IDF.
**The riskiest parts are audio buffer tuning and broadcast reliability, not the
protocol** — the protocol is genuinely portable, which is the finding.

## 4. What does not map, and must be decided rather than fudged

- **`shutdown`** — deep sleep is effectively a one-way trip; nothing wakes it
  over WiFi in a venue. Honest options: reply `err`, or redefine it as
  mute-and-idle. Do not silently no-op it.
- **`engine-alive`** — collapses to always-1. This **loses a real diagnostic**:
  §6 calls "box up, engine crashed" vs "box gone" one of *"the two mid-show
  failures an artist must tell apart"*. Best recovery is to report the audio
  task's watchdog state, so the bit still means something.
- **`updatebopos` / `version`** — OTA (`esp_https_ota`) is solved, but the
  heartbeat's `version` is a **git shorthand** today and would become a
  firmware version string. Harmless, but the dashboard's currentness UX
  (`framework-version-management`, still unbuilt) should know there are two
  kinds.
- **`hostname`** — mDNS name rather than `sethostname` + reboot. Different
  semantics under the same verb.
- **`restart-engine`** — re-init the audio task. Fine.

## 5. Two risks worth writing down before anyone starts

**1. WiFi power save will eat your events.** The contract leans on broadcast
for `/os/assign`, `/all/*` admin, `/e/*`, `/pt` at 20–30Hz, `/os/mute`,
`/os/master` and `/sync/ping` at ~2Hz (§4, transport discipline). ESP32 station
default is `WIFI_PS_MIN_MODEM`, which **delays and drops multicast/broadcast
frames**. `esp_wifi_set_ps(WIFI_PS_NONE)` is mandatory, and it is the kind of
bug that presents as maddening intermittent event loss rather than as a
failure. Also raise the lwIP UDP receive queue: `/pt` at fleet scale is a
sustained parse load in the lwIP task.

*(Asserted from general knowledge; verify on a bench before trusting it.)*

**2. The constrained-reference-target flips.** §12 names the Pi Zero 2 W as the
constrained reference. An S3 is dramatically more constrained in RAM and
dramatically **less** constrained in timing determinism. Any rule of thumb
inherited from "will this run on a Zero 2" needs re-deriving, in both
directions.

Related and measured: `.loom/threads/pi-zero-performance/measurements-2026-08-13-finn-jet.md`
found Pd costing **51% of a core on `demo-pd` and 99% on `bonks-pd`**, with the
JACK client thread idle and three of four cores unable to help, because Pd's
audio path is single-threaded. The 51% floor on a nearly empty patch is
unexplained and is paid by every patch on every node. A fixed-function sampler
on an S3 has no such floor — but it also cannot do anything Pd can do.

## 6. Where it wins, and where it is not a node at all

Wins: sub-second boot against the Pi's ~25s; roughly an order of magnitude less
power; no filesystem to corrupt on a power cut, which is the Pi's classic field
failure; tighter event timing; and a per-node cost low enough to change what
scale of piece is affordable.

Does not win: **synthesis, DSP, or Bob's hand-patched Pd workflow.** For "N
speakers that fire precisely together" an S3 is the better node. For anything
that needs to *make* a sound rather than play one, it is not a node — it is a
different instrument, and pretending otherwise is how the contract gets bent.

## 7. Ordering

The strategic question is not feasibility, it is sequence.
`.notes/horizon-architecture-refactor.md` Force 2 has engine agnosticism
half-built, and records the single biggest unknown: **`sclang` has never
launched under the framework, on a Pi or a laptop — text-verified only.**

An ESP32 node is engine agnosticism taken to its limit: the engine is not even
a process. If the refactor lands the abstraction that note names — *an engine
instance with an identity, a port, a kind and a liveness state* — an S3 slots in
as a kind whose port is "in-process". If it does not, an S3 forces that refactor
anyway, from a harder direction and with a soldering iron involved.

The horizon note's own standing constraint applies: *"the system works today and
must keep working; prefer small ordered changes over rewrites."*
