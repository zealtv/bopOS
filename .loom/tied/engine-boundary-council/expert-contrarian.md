# Engine boundary — the contrarian's dissent

## 1. Lens & altitude

I am the seat paid to distrust unanimity. Five experts wrote independently and
landed on the *same* move — helper becomes the sole LAN citizen, PD stops
binding the LAN, one relayed 6661 surface for all engines, delete the admin
forward / meters / `/rpt`, add a demand-driven probe. Convergence that clean,
one day after the seam council ratified the opposite, is a smell, not a proof. I
work at two altitudes: the failure-mode altitude (what dies when helper hangs
mid-show) and the ledger altitude (count the mechanisms added vs. deleted,
honestly). My job is to find the load-bearing assumption nobody stress-tested
and hit it with repo evidence — and to concede fast where the evidence defeats
me, because an attack that doesn't survive the code is noise.

## 2. Where the consensus is strongest (steel-man)

The consensus is *right* about the cheap deletions, and I will not pretend
otherwise. The PD→7770 admin forward is genuine duplication: helper already
handles every lifecycle/provision verb directly on its own 6660 listener
(`helper.py:775-791`, `LIFECYCLE_VERBS`/`PROVISION_VERBS`), so `route helper →
process-helper-messages` exists only to hand helper a packet it already heard.
Deleting it (with the operations seat's `/helper/*→/os/*` alias landing *first*)
is pure subtraction with a live safety net. Meters are Bob-blessed cruft. The
`/rpt` broadcast, `route echo`, and `PX`/`PY` prints are dead weight. And SC
genuinely cannot share 6660 (seam-5), so *some* relay must exist. On all of
this, consensus wins. My fight is with the one leap they all made past these
safe deletions: **abolishing PD's direct 6660 bind and routing every engine's
control through the one Python process that must not fail.**

## 3. The attacks (ranked by severity)

### Attack 1 — collapsing two independent kill paths into one (severity: high)

**Claim:** "helper's death already stops heartbeats, so making it the sole
control owner loses nothing new" (transport §6; engine-api §6).

**Counter-evidence:** Today PD binds 6660 itself (`contract §4` table: "6660 |
PD"; `pd/bopos.osc.pd` line 3) and `bopos.out~` receives `os master` off the
`osc-in` bus that PD's *own* 6660 path feeds (`ground-truth §3`, lines 98-102).
So a running PD keeps full **master and `/p/*` parameter control even if
helper.py is dead or hung.** That yields two *independent* emergency-stop paths
today: (a) `/os/mute` → helper/amixer, and (b) `/all/os/master 0` → PD-direct,
idempotent, spam-safe, needs no helper. The consensus routes master through
helper's 6661 relay, so **both** kill paths now depend on the same 1070-line
Python process that spawns subprocesses, runs `git pull`, and does blocking I/O.
One hung helper thread and the facilitator has no master fade *and* no mute.

**Predicted failure:** a helper hang during a show freezes the last master
value with no operator recourse. Deployed installs "run networkless for months"
— fine for audio (PD's synth graph plays regardless), but the moment a laptop or
iPad is plugged in for a performance, control redundancy that exists today is
gone. Redundancy on the safety-critical path is exactly what you don't casually
delete.

### Attack 2 — the probe facility is *more* machinery than it deletes (severity: high)

**Claim:** report-on-request is simpler than the always-on `/rpt` broadcast
(all five seats; probe/tap/lease).

**Counter-evidence — count it honestly.** Deleted: four PD objects
(`osc-out → gate → oscformat rpt → netsend`) and a dumb stream. Added: a new OSC
verb, per-subscription lease state in helper, a deadman/TTL timer, rate
limiting, dashboard UI, **and a wire that does not exist today.** The capacitive
case is `io/main.py` → PD on 6662 (`io/main.py:19-20`); **helper never talks to
io at all** (`ground-truth §5`; helper has no io channel). Creative-tools §3
blithely writes "io → helper → unicast," but that arrow is unbuilt: to fulfil a
touch probe helper must open a new helper↔io link and io must learn to publish
upstream. That is net-new plumbing to replace a four-object echo. The lease is a
timer, the timer needs a thread, the thread needs teardown — this is the
mechanism-count going *up* while claiming taste points for going down.

**Predicted failure:** the "simpler" replacement ships as three stitches of
lease/timer/io-bridge work and a §14 fight (below), to serve one debugging use
Bob already tolerates.

### Attack 3 — re-litigating a one-day-old ratified decision (severity: high)

**Claim:** amending §4's listener table is "a clarification, not a port change"
(engine-api §4; simplifier §4; transport §4 calls it v1.2).

**Counter-evidence:** `contract §4` opens "The six ports stay exactly as
deployed" and names "6660 | PD" as listener; `§4.1` states "PD retains its
deployed direct 6660 routing path"; the **seam-5 result (2026-07-11, yesterday)
explicitly ratified** "PD retains its existing direct 6660 path and receives no
duplicate relay." `§14` rejects "port consolidation... without a contract
revision" and a "parameter-dump/query verb." The council was chartered to design
the *node interior* (the engine boundary), and instead every seat rewrites the
ratified LAN transport table and reverses a decision that is 24 hours old. A
leased streaming probe is "telemetry streaming... with a TTL" — precisely §14's
rejected item wearing a costume. This isn't designing the engine boundary; it's
re-opening the seam council.

**Predicted failure:** Bob's ratification gate stalls because the deliverable
quietly overturns his own most load-bearing table, and the "engine boundary"
question (bus vocabulary, ownership of id-routing, run-context delivery) — the
thing actually asked for — arrives buried under a transport re-litigation.

### Attack 4 — the macOS justification doesn't reach production (severity: medium)

**Claim:** PD must stop binding the LAN because macOS breaks (errno-48 shared
bind, errno-49 broadcast).

**Counter-evidence:** every macOS failure in the record is **audition-only,
N>1** (`audition-0`, `audition-1b`): errno-48 is *three* PDs contending for one
6660; errno-49 is PD's `/rpt` netsend to `255.255.255.255:5550`. A production
Mac runs **N=1** — one PD binds 6660 with zero contention. And PD's *only* send
to 5550 is the `/rpt` path (`ground-truth §2` egress) — which the consensus is
deleting anyway. So **deleting `/rpt` alone dissolves errno-49 without touching
PD's 6660 bind.** The two changes are separable; the consensus welds a forced
deletion (`/rpt`) to an unforced one (PD's LAN bind) and credits the platform
for both.

**Predicted failure:** production PD's battle-tested `netreceive` (proven in
Kite Choir and The Plants) is torn out to solve a problem that only exists in
the audition rig, which `tools/audition.py` already solves without touching
production topology.

### Attack 5 — is one pyOSC3 OSCClient a worthy owner? (severity: medium, partly conceded)

**Claim:** the extra hop is "microseconds, well inside budget" and thread-safe
enough (transport §6).

**Honest concession first:** `/pt` at 30 Hz *already* rides helper→6661
(`helper.py:545-584`), so the consensus adds **no** new hop to the spatial hot
path — the "30 Hz × N through Python" framing overstates it. The only new
relayed traffic is master/params at <1/s. Latency is a non-issue; I withdraw
that part.

**What survives:** helper's single `OSCClient` (`helper.py:42-44`) is already
`send()`-ed from multiple threads with **no lock** — `fire_cue_to_engine` on the
cue-scheduler thread (`helper.py:1028-1036`) vs. `apply_points` on the LAN
listener thread (`helper.py:574-582`). That's a latent UDP interleave bug today;
the consensus loads master/mute onto the same unsynchronized client and makes it
the sole path for *all* control. And note: helper uses `pyOSC3` while the relay
they want to "generalize," `tools/audition.py`, uses `python-osc` — the "same
role" claim glosses two different libraries.

**Predicted failure:** rare, hard-to-repro garbled datagrams under concurrent
send, on the one process now carrying everything.

## 4. My alternative — heterogeneity as honesty

Don't pretend PD and SC are the same when the platform says they aren't. Ship
the safe deletions everyone agrees on; keep the working path that survives
helper death.

1. **Keep PD's direct 6660 bind in production (N=1).** It is battle-tested,
   independent of helper, and preserves the second kill path. Master and `/p/*`
   reach PD without a relay hop or a helper dependency.
2. **Relay only where the platform forces it** — non-PD engines (SC can't share
   6660) and audition N>1 (macOS). This is exactly the seam-5 guard
   (`helper.py:645`) and `tools/audition.py` *as they already exist*. Keep the
   `!= "pd"` guard; do not generalize it to production PD.
3. **Delete the true cruft, fleet-wide, per-patch in lockstep (§13):** the
   PD→7770 admin forward (after the `/helper/*` alias lands in helper first),
   `route echo`, `PX`/`PY`, the `/rpt` broadcast, framework meters. Deleting
   `/rpt` alone fixes macOS errno-49.
4. **For the one real echo use (capacitive touch), the minimum:** a *one-shot*
   unicast `/<id>/os/probe <name>` answered from sources helper already reads,
   plus — only if Bob wants live touch — a bounded io→helper snapshot. No
   standing lease/timer/subscription subsystem until a second use case earns it.
5. **Fix the latent client race** with a lock around `client.send()` regardless
   of which topology wins.

Net: every deletion the consensus makes safely, none of the transport-table
reversal, and the engine keeps the redundancy it has today. Uniformity is a
future migration (opt-in, per-rig, bench-gated — the operations seat's "Stage
4"), not a flag-day this council mandates.

## 5. What I'd concede under evidence

- **Attack 1 dies** if a bench test shows a hung/killed helper mid-show and a
  measured recovery: kill `helper.py` while PD plays, then verify whether
  `/all/os/master 0` from a laptop still cuts PD audio (it should today; that's
  the redundancy I claim). If Bob rules the amixer mute is the *only* sanctioned
  kill path and the PD-direct one is untrusted, the redundancy argument weakens.
- **Attack 2 dies** if someone specs the probe with an honest mechanism count
  and it comes in *at or below* what `/rpt` costs — including the new helper↔io
  wire. I'll believe it when the io bridge is drawn, not asserted.
- **Attack 4 dies** if a production Mac (single PD) reproduces errno-48/49 with
  no audition sharing — i.e. if the macOS breakage is general, not N>1. Nobody
  has run that test; the record is audition-only.
- **Attack 5 dies** with a soak test hammering `client.send()` from the cue and
  LAN threads showing no garbled datagrams — or is trivially closed by the lock.

## 6. Smallest first step for my alternative

**Land the `/helper/*→/os/*` alias in helper's 6660 listener, then delete only
the PD→7770 admin forward and the duplicate 7770 handlers — and stop there.**
Pure subtraction, reversible, no wire change, verifiable on simfleet (kill the
engine, confirm reboot via helper alone). This banks the deletion all five seats
*and* I agree on, while touching neither PD's 6660 bind nor the transport table.
Only after that verifies do we argue about whether PD should ever leave the LAN
— separately, on its own evidence, not welded to cruft removal.
