# Seam council — Operations / distributed-systems reality check

## 1. Lens & altitude

I sit at the **process / wire / failure-mode** level: what actually runs on a
Pi Zero 2 W, which sockets and pidfiles are singletons, how many datagrams cross
a lossy broadcast channel per second, and what stays true when a process dies or
a device was offline during a change. I chose this altitude because the seam is a
principle, but principles are ratified by their failure modes on install day. The
reverted `spatial-0` didn't fail on taste; it failed on arithmetic (N per-device
gain streams) and on coupling that a dead dashboard couldn't unwind. My job is to
mark which elegant "provided, not enforced" moves are safe to ship and which ones
quietly break a deployed fleet.

## 2. Problem reframing

"Provided, not enforced" is correct as a *responsibility* statement and dangerous
as a *migration* statement. The moment you move the master multiply out of the
dashboard and into the patch, you have changed a **contract every deployed patch
already relies on** — today the patch never sees master; the dashboard hands it a
pre-multiplied product (`osc_bridge.py:135-144`). Flip that unilaterally and every
Kite Choir patch that doesn't yet multiply master goes deaf to the master slider —
including a facilitator yanking it down. So the real problem is not "where does the
multiply live"; it's **how to relocate a responsibility across a fleet you cannot
reflash, one behaviour at a time, while keeping the one thing that must never
depend on the patch — mute — enforced below it.**

## 3. Proposed design

**Master becomes a provided broadcast value, but opt-in per patch.** Add a
framework-provided fleet value on the wire, idempotent full-state, broadcast on
change only (not streamed): `/all/os/master <m>` (spelling flagged for Bob;
`/os/*` because it is framework-provided, not patch-owned `/p/*`). helper relays
it to the engine on localhost as a named scalar (`/master <m>`, PD receiver Bob's
domain). The patch multiplies `source × gain × master` itself.

The switch is **manifest-gated so there is no flag day.** A patch opts in with a
manifest marker (e.g. param `role:"volume"` gaining a sibling `"consumes":["master"]`,
or a top-level `"master":"patch"`). Dashboard behaviour:

- Patch does **not** declare master-consumption → dashboard keeps today's VCA
  pre-multiply verbatim (`send_device_param` product, `resend_volumes`). Deployed
  fleet unchanged.
- Patch declares it → dashboard sends the **raw** `v_i` as `/id/p/<vol>` and
  broadcasts `/all/os/master`. The patch does the multiply.

Never both — double-multiply is the failure mode, so the gate is exclusive.

**Silence-All / safety is unchanged and stays enforced.** Master-to-zero is a mix
tool that depends on the patch actually subscribing; it is *not* safety. SILENCE
ALL remains `/all/os/mute 1` (amixer below patch logic; engine-stop fallback).
This is the whole payoff of the seam: by refusing to overload master with safety,
"provided, not enforced" for master becomes safe, because the enforced path
(mute) is a separate, engine-independent actor.

**Mute independence — the honest boundary.** Mute is independent of the *engine*
(amixer mutes the card whether PD is wedged, the patch is in a runaway, or the
DSP is fine — `set_mute` at `helper.py:400`). It is **not** independent of
*helper*: helper is the actor. If helper dies, mute cannot fire — but the
heartbeat (also helper-sent, 5550) stops too, so the dashboard shows the device
dead rather than falsely muted. The weak spot is the **no-mixer fallback**: there
mute = `stop-engine.sh`, which is engine-*lethal* and loses the mix on unmute.
For DigiAMP the mixer path should hold; that it exposes a mute-capable control on
the target rig **needs bench verification**. Ruling: keep mute exactly as-is;
document that "independent of the engine" is satisfied, "independent of helper" is
not, and the fallback is the degraded mode, not the design centre.

**Points — accept the node-side draft; fix the two ops holes.** The `/pt`
broadcast + node-side decomposition is the right model *because of the
arithmetic* (below). Two corrections the draft under-specifies:

1. **Reappearance catch-up.** "Silence = hold" is fine for a device that stayed
   present, but a device that was offline during a still moment gets *no* point
   frame and renders nothing. The dashboard must send one `/pt` frame on device
   (re)appearance (piggyback the existing params catch-up keyed on heartbeat), or
   emit a ~1 Hz keepalive frame even when still. Prefer the per-device catch-up —
   it costs one unicast, not fleet bandwidth.
2. **Master convergence, same shape.** Master is fleet-wide but a reappearing
   device still needs the current value; push it in the same catch-up.

**Multi-element process model — one helper, N engine instances, element is
node-internal.** This is *not* a dashboard mode. Device stays the addressing unit;
element is a sub-position the node fans out. The collisions that make this a real
project, not a config change:

- **Singletons that break:** `engine.pid` / `engine.name`, and localhost ports
  6661/7770 (and 6662/8880 for io) are one-per-device (`start-engine.sh:99`,
  contract §4). Two PD instances binding 6661/7770 collide. Fix: index instances
  and offset ports (`6661+2k`, `7770+2k`), write `engine.<k>.pid`. 6660 (LAN) is
  already SO_REUSEPORT-shared, so broadcasts reach every instance for free.
- **jackd is *not* a collision** — one jackd, N PD clients is normal jack. Good.
- **CPU is *not* the constraint** — PD is single-threaded, the Zero 2 W is
  quad-core, so 2 instances use 2 cores that were otherwise idle. The real
  constraints are **512 MB RAM** (2× PD + jack + helper + io) and **jack xruns
  with two clients** at `-p512 -n2`. Both **need bench verification**; neither is
  testable from this repo.
- **Heartbeat's single engine-alive bit** (`§6`, `helper.py:254`) cannot report N
  instances. Stage additively: keep one bit meaning **AND of all declared
  elements** (any element down reads as engine-dead — conservative, correct for an
  alarm). A per-element count is a later contract revision, flagged.
- **Positions already ride the wire for 2 elements:** assign parses up to 4 floats
  = 2 positions (`helper.py:491-519`), the Belief L/R remnant. So the **stereo
  two-element case is representable today**; helper computes proximity per element
  position and delivers to each instance's port. N>2 needs a new encoding — later.

### Bandwidth arithmetic (the constraint that decides it)

- **Node-side `/pt`, frame form B:** `/pt <n> [id x y r f]×n`, ~20 B/point +
  overhead. M=5 points ≈ 120 B payload; at 30 Hz ≈ **3.6 KB/s, one broadcast,
  reaches all N nodes, independent of N.**
- **Rejected `spatial-0`:** dashboard computes per-device gain → **N streams** at
  25 Hz. N=12 → 300 msg/s; N=100 → **2500 msg/s** on the lossy, ACK-less, basic-rate
  broadcast channel, contending with `/hb` and `/sync/ping`. That is the number
  that kills it, and why §4/§14 already reject per-device fleet-scale gain
  broadcast. Node-side is O(1) in fleet size; dashboard-side is O(N). Settled.

### Facilitator promotion — draw the line at *reversibility*

Promote patch `/p/*` params freely: a manifest `"facilitator": true` (or reuse
`group`) marks a subset onto the iPad. These are bounded by manifest min/max,
patch-enacted, idempotent — worst case is a bad mix, recovered by a preset. Safe.
The break surface is **admin verbs**, and the scope guard is right to be nervous:
`/os/update` triggers git-pull-plus-**reboot** (`update_callback` → `reboot`), so
one accidental touch is 60 s of dead device mid-show. Ruling: allow
*reversible/non-destructive* verbs on the facilitator (identify, the existing
mute/SILENCE, optionally start-all); keep *destructive convergence* verbs
(update/checkout/reboot/shutdown) **off** the facilitator, or behind hold-to-confirm
in a separate "danger" strip. The seam principle helps here: everything a
facilitator can touch is either bounded-and-patch-enacted or the enforced mute —
nothing they touch can wedge a box irreversibly.

## 4. How it fits the existing system

- `dashboard/osc_bridge.py`: `send_device_param`/`resend_volumes` gain the
  master-gate branch; add master + `/pt` to the per-device reappearance catch-up
  (the mechanism at `osc_bridge.py:237-241` already exists).
- `python/helper.py`: relay `/all/os/master` to the engine (localhost); add
  `/pt` parse + node-side falloff (salvaged `linear/smooth/gauss`); proximity per
  element position; the multi-instance work touches `start-engine.sh` /
  `stop-engine.sh` / `engine_alive` and is its own stitch.
- `tools/simfleet.py`: same node-side `/pt` decomposition and master relay so
  verifies read node-computed values (house rule: protocol features land in the
  sim same stitch).
- **Migration (§13):** zero port changes, no reflash, no flag day — satisfied by
  the master opt-in gate (deployed patches keep dashboard VCA), the reappearance
  catch-up (additive), and staging multi-element as a later, bench-gated stitch.
  Any transition alias lives exactly one release.

## 5. Why it's elegant / right

It honours "provided, not enforced" *without betting safety on it*: master is
provided and patch-enacted; mute stays enforced and engine-independent; the two
never overload. It respects the arithmetic that reverted spatial-0 (O(1) broadcast
vs O(N)). Constraints I claim **kill or gate** the obvious-elegant version:

- Moving the master multiply into the patch **unconditionally** breaks every
  deployed patch — *killed*, replaced by the manifest opt-in gate.
- "Silence = hold" for points **loses state for reappearing devices** — *gated* by
  a catch-up frame.
- Two-PD-per-Pi is **not CPU-bound but is RAM- and xrun-bound** — *gated on bench
  verification*, not shippable-as-verified from this repo.
- Mute is engine-independent but **helper-dependent**, and the no-mixer fallback
  is engine-lethal — *bench-verify DigiAMP exposes a mute control* before calling
  mute-independence done.

## 6. Tradeoffs, risks, what I'm NOT solving

- The master opt-in means two code paths for one release (VCA vs patch-side).
  Accepted: it's the price of no flag day. Delete the VCA path only when the fleet
  has converged — a judgment call, not this session's.
- I am **not** solving point-authoring UI, sequencer integration, N>2 element wire
  encoding, or a per-element heartbeat count — all flagged additive/later.
- I am **not** giving standalone mode a remote mute (there is no controller);
  patches must default master=1.0 and treat absent points as "source at own gain".
- PD receiver spellings (`/master`, `/pt/<id>`) and manifest key names are Bob's
  co-design at ratification (house rule) — proposed, not fixed.

## 7. Smallest first step

**Ships now** (Kite Choir / Playable Streets, stereo single-element, no hardware
needed): (a) node-side `/pt` decomposition in helper + simfleet with the
**reappearance catch-up frame**, driven by a test driver and asserted in a
browser-free `verify_*.py`; (b) the **master opt-in gate** in `osc_bridge.py`
with deployed patches unchanged (VCA default) and one manifest example that
consumes master; (c) facilitator param-promotion marker (patch `/p/*` only) with
destructive admin verbs explicitly excluded. All of this is Python/JS/sim — fully
verifiable in this repo.

**Bench-gated (needs a rig, do not claim verified):** DigiAMP mute-control
presence; and the multi-element process model (port-offset launch, `engine.<k>.pid`,
engine-alive = AND, 2× PD RAM/xrun on a Zero 2 W). Design it now so it lands
additively; run it on Bob's dev Pi before it ships.

**Later (contract revisions):** N>2 element wire encoding, per-element liveness
count, point-authoring UI, deleting the VCA compat path once the fleet converges.
