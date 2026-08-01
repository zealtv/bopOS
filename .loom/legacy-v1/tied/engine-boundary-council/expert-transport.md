# Engine boundary — transport & process topology

## 1. Lens & altitude

I judge this design as sockets, senders, and packet budgets. A port earns its
existence only as an **ownership boundary** or a **measured performance choice**;
anything else is a historical accident to delete. I take a deliberately concrete
altitude — I draw the per-device, per-platform socket diagram and bound every
flow — because the whole council problem is a topology problem wearing a
vocabulary costume. Get the topology right and the naming/meter questions
collapse into it.

## 2. Problem reframing

The seed lists eight smells. Read as transport, six of them are **one** defect:
*two things own LAN ingress on the same device, and the engine is one of them.*
Because PD binds 6660 and self-routes, we get: the double-6660 bind; the
PD→helper 7770 admin round-trip (the engine routing framework verbs back to the
framework); the SC asymmetry (SC can't share 6660, so the same term travels
`os master` via PD's 6660 path *or* `/os/master` via helper's 6661 relay — two
spellings, two paths, per engine); the audition errno-48 noise (every PD still
tries the fixed 6660 bind); and the macOS errno-49 report failure (PD itself
broadcasting to 5550).

There is already a proven fix living in two places: **seam-5** (helper owns 6660,
strips the selector, delivers a local surface to SC on 6661) and
**`tools/audition.py`** (one relay owns 6660, fans out to N per-engine local
ports). These are the *same role*. The design is simply: **make that role the
only owner of LAN 6660 on every device, for every engine, on both platforms.**
The engine stops touching the LAN entirely. Production and audition stop being
two topologies — they become the same relay with N=1 vs N engines.

## 3. Proposed design

**One law: the node relay is the sole binder of LAN ports (6660 in, 5550 out).
No engine ever binds a LAN socket.** In production the relay is `helper.py`; in
audition it is `tools/audition.py` (helper wearing N virtual identities). Every
engine — PD, SC, oF — receives the identical selector-stripped local surface on
6661 and speaks upstream only over localhost.

### Production Pi / production Mac (N = 1 engine)

```
        LAN 6660  (dash → fleet, broadcast)          LAN 5550 (fleet → dash)
            │                                              ▲
            ▼                                              │ unicast replies +
      ┌───────────── helper.py (SOLE LAN owner) ───────────┤ direct heartbeat
      │  selector-route, strip, own id/assign/sync/cue/pt  │ (engine death ≠
      │  proximity math, mute, provisioning, reports       │  device death)
      └──┬─────────────────────────────┬──────────────┬────┘
   6661  │ helper → engine             │ 7770         │
  (terms,│ master /p/* pt cue id       │ engine+io →  │
   notify)▼                            │ helper       │
      ┌── engine (PD / SC / oF) ──┐    │ (REPORTS,    │
      │ consumes provided terms   │────┘  demand-only)│
      │ 8880 → io control ────────┼──► io/main.py ────┘  (io also publishes
      └────────────▲──────────────┘        │              named diag values
              6662 │ io → engine           │              upstream on 7770)
             (high-rate peripheral stream) │
                   └───────────────────────┘
```

**LAN ingress owner: helper, always.** It already speaks contract v1.1 on 6660
(`handle_lan_datagram`). Deleting PD's 6660 bind removes the second owner and
makes macOS's "can't share 6660" irrelevant — nobody shares it.

**Engine-local delivery: 6661, one channel, every engine.** PD loses its direct
6660 route and joins SC on the selector-stripped 6661 surface. Extend the seam-5
relay (drop the `expected_engine_name() != "pd"` guard, helper.py:645) so master
and `/p/*` reach PD there too; `pt`, `cue`, `id`, `identify`, `notify` already
use 6661. **The "same term, two spellings" asymmetry disappears** — there is one
spelling (`/os/master`, `/p/<name>`) delivered one way.

**IO separation stays — it is a real performance boundary, not an accident.**
6662 (io → engine, high-rate stream) and 8880 (engine → io, control) keep their
own sockets so a 10 Hz — potentially 100 Hz — peripheral bundle never contends
with control traffic on 6661, and never touches the LAN. **High-rate streaming
rule: peripheral data is localhost-only; it reaches the LAN only through the
demand-gated report facility below, never by default.**

**Reports/meters: fold into one demand-driven facility on 7770, off by default.**
7770 stops being the admin round-trip (deleted — helper owns LAN admin directly,
killing smell #1) and becomes the **report upstream**: engine-authored
diagnostics *and* io peripheral values publish named values to helper here.
Helper forwards them to the LAN **only while a dashboard has an active
subscription**, **unicast to that requester**, **throttled**, with a **TTL that
auto-expires** the subscription (`/<id>/os/report <name> [hz] [ttl]` — snapshot
if no hz; bounded stream if hz). This is Bob's report-on-request instinct made
concrete. It kills the `/rpt` broadcast path, kills the macOS errno-49 failure
(helper does the LAN send with a Python unicast socket, never PD's broken
broadcast netsend), and keeps localhost sensor chatter localhost by default.
**Meters as a continuous concept are deleted** (Bob: not mission-critical); a
live level is just a report subscription. The manifest `role:"meter"` field
survives as a UI hint, but its transport is this facility, not a standing
`/<id>/p/<name>` broadcast.

### Audition Mac (N engines) — the same model

```
   LAN 6660 ──► tools/audition.py (SOLE LAN owner, N virtual ids) ──► 5550
                 strip selector, fan out per node
       ├─ 16661 → engine[0]   ├─ 16662 → engine[1]   ├─ 16663 → engine[2]
```

Identical role, identical local surface. Each engine binds **only** its
`BOPOS_ENGINE_PORT` — no fixed 6660/6661/6662 attempt, so **errno-48 noise
vanishes**. Because only the relay ever binds 6660, macOS's non-shareable stock
PD receiver stops mattering on every device, production included.

### Packet-rate / bandwidth bounds

| Flow | Port | Rate | Size | Fleet scaling |
|---|---|---|---|---|
| heartbeat | 5550 | 1/10 s (2 s unassigned) | ~50 B | O(N), ~10/s @100 nodes — trivial |
| `/pt` frame | 6660 | ≤30 Hz | ~700 B (5 pts) | **O(1)** broadcast, 3–4 KB/s |
| master/mute/assign/cue | 6660 | event, <1/s | ~40 B | O(1) idempotent broadcast |
| sync ping / pong | 6660 / 5550 | ~2 Hz | ~40 B | ping O(1); pong O(N) unicast, ~200/s @100 |
| io stream | 6662 | 10 Hz (≤100 Hz) | ~150 B | **localhost only**, ~1.5 KB/s, never LAN |
| reports (incl. touch) | 7770→5550 | **0 by default**; ≤10 Hz per active sub | ~150 B | **unicast to requester only** — never wakes 100 CPUs |

Every LAN broadcast is O(1) or low-rate idempotent; everything O(N) or high-rate
is unicast or localhost. That is the discipline §4 already demands, now enforced
with no exceptions.

## 4. How it fits the existing system

**Stays:** all six ports and their numbers; the wire on 6660/5550; the seam law;
`/pt`/proximity math; sync/cue; io's two-socket separation; audition's relay.
**Changes:** 6660's *listener* becomes helper-only; 5550's *sender* becomes
helper-only (engine never sends LAN); 6661 carries every engine including PD;
7770 flips from admin-forward to report-upstream. **Contract:** a **v1.2
amendment** to the §4 listener/sender columns and §11 meter transport, plus the
small `/os/report` subscription verb. **This is not a port renumber** — §14
rejects renumbering *without a revision*; we renumber nothing and preserve every
§13 guarantee: **zero port changes, no reflash, no flag day, `uid == MAC`.**
**PD work (Bob-owned, specify don't edit):** remove the 6660 `netreceive`;
remove `route helper → 7770`; move master/`/p/*` consumption onto the 6661
surface (PD already has this path for SC-shaped terms); repoint patch-side
diagnostics from the `/rpt`/`osc-out` broadcast onto the 7770 report bus.
**Migration:** patches rewrite in lockstep (already the §13 model). Roll helper
first (additive relay to PD), then land the PD binds removal — see step 7.

## 5. Why it's elegant / right

A patch author holds one sentence in their head: *"the framework hands me terms
on my local port; I never touch the network."* One ingress owner, one engine
surface, one upstream, per-engine identical — that is *simple, clean,
understandable, performant*. It is right on the evidence: macOS's non-shareable
6660 and errno-49 broadcast both stop mattering because the engine never binds
or sends to the LAN; the audition errno-48 noise disappears for the same reason;
and at 100-node fleet scale nothing new hits the broadcast channel — reports are
unicast and default-off. Production and audition become the *same relay*, so the
performance platform and the test rig can no longer drift apart.

## 6. Tradeoffs, risks, not-solving

- **Adds one hop for PD's control terms** (6660→helper→6661 instead of direct).
  At <1/s for master/params and ≤30 Hz for `/pt` on a localhost socket, this is
  microseconds — well inside the §12 single-threaded-PD budget. Worth it.
- **A subscription verb flirts with §14's telemetry-streaming rejection.** I
  keep it legal by making it pull/TTL-bounded and unicast, never a standing
  broadcast stream; heartbeat-absence remains the alarm.
- **Not solving:** the detailed `bopos-` bus renaming (defer to the vocabulary
  lens — I only assert the *report* bus and the collapse of `osc-in`/`osc-out`);
  the exact `role:"meter"` UI rendering; SC multi-server audio; run-context
  delivery (I assert only that one owner — the relay — should deliver it, as a
  string run-id, never epoch floats per §12).

## 7. Smallest first step

Purely additive, fully reversible, no `.pd` change: **remove the
`expected_engine_name() != "pd"` guard so helper relays `/os/master` and
`/p/<name>` to PD on 6661 *in parallel* with PD's existing 6660 path.** Verify PD
receives identical terms both ways. That single-line change proves the local
surface is sufficient for PD — the keystone hypothesis of the whole design —
while nothing is removed. Only after it passes do we take step two (Bob drops
PD's 6660 bind and the 7770 admin forward). Revert = re-add the `if`.
