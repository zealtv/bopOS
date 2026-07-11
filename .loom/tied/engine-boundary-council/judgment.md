# Judgment — engine-boundary council, 2026-07-11

Judge: Fable 5 (council integrator). Sources verified directly against
`main` @ `0cd388a` before ruling; file:line citations below are from that tree.

## 1. The decision, up front

I rule for the **sole-binder end-state with the contrarian's ordering
discipline**: `helper.py` (to become `bopos.py`) is the only LAN citizen on
every device; every engine — PD included — consumes one identical
selector-stripped localhost surface on 6661 behind a `[bopos]` façade with a
`bopos-*` bus glossary; the PD→7770 admin forward, framework meters, and the
`/rpt`/echo chain are deleted; reports become a demand-driven unicast probe,
one-shot first and leased only when a real need lands; run context is
helper-owned but launch-delivered (no OSC-at-boot); io keeps its 6662/8880
separation. This is an explicit **contract v1.2 revision** to §4/§4.1 — not a
"clarification" — sequenced so that every stage is reversible and PD's direct
6660 bind survives until the parallel relay is bench-proven, with the
single-process risk mitigated by a client lock, helper auto-restart, and a
verified helper-death drill.

## 2. The real crux

Two decisions carry everything:

1. **Does PD leave the LAN?** The consensus says yes (one spelling, one path,
   one mental model, production ≡ audition); the contrarian says no (PD's
   direct 6660 bind is a battle-tested, helper-independent master-kill path,
   and the macOS evidence is audition-only). The genuine tradeoff is
   **uniformity vs. control redundancy**: the consensus buys a surface a patch
   author holds in their head at the price of making one 1070-line Python
   process the sole control path.
2. **Is report-on-request less machinery than what it replaces?** The probe
   idea is right in shape but, as specified by creative-tools, requires a
   helper↔io wire that does not exist (`io/main.py` sends only to PD on 6662,
   io/main.py:19-20,41). The tradeoff is deleting a dumb broken broadcast vs.
   building a lease subsystem to serve one debugging use.

## 3. Council map

| seat | crux position | best contribution |
|---|---|---|
| engine-api | sole binder | the `[bopos]` façade + prefix-law bus glossary; the line-for-line PD/SC starter equivalence |
| transport | sole binder | production ≡ audition as "same relay, N=1 vs N"; the flow-by-flow bandwidth table; broadcast/unicast discipline with no exceptions |
| operations | sole binder, staged & gated | the `/helper/*` alias hole (the single fact that reorders the whole migration); the boot-race veto on OSC-delivered context; "ownership ≠ transport" |
| creative-tools | sole binder | the three-way meter category split; the lease insight (debug streams expire themselves); debug inspection ≠ musical consumption |
| simplifier | sole binder | the honest mechanism count (4 delivery paths → 1); "helper already owns admin" as the load-bearing thesis |
| contrarian | heterogeneity | forced the safety accounting: dual kill paths, the unbuilt io wire, the §4.1 re-litigation charge, the unlocked shared client — every attack cited real code |

Steel-manned, the contrarian is the best-evidenced seat at the table; the
dissent is why this ruling has gates instead of a flag day.

## 4. Adjudication of the load-bearing facts

Ground truth checks out on every point I spot-checked; no design inherits a
factual error from it.

1. **The `/helper/*` alias hole — CONFIRMED.** helper's 6660 listener rejects
   any non-`os` plane (`if len(parts) != 3 or parts[1] != "os" … return False`,
   helper.py:678). The 7770 `OSCServer` handlers are selector-free `/config
   /update /reboot …` (helper.py:1048-1059) and are fed only by PD's `route
   helper` forward (bopos.osc.pd lines 44,48) and the SC starter's `/config`
   (main.scd:120). The day PD stops forwarding, legacy `/helper/*` verbs from
   deployed dashboards die silently. **The alias lands in helper's 6660
   listener before any deletion. Non-negotiable.**
2. **Dual emergency stop — CONFIRMED, with bounds.** PD binds 6660 itself
   (bopos.osc.pd line 3) and `bopos.out~` takes `os master` off `osc-in`, so
   `/all/os/master 0` reaches a running PD with helper dead. But the
   redundancy is narrower than the dissent implies: it exists only for PD
   (SC already rides the relay), only for master (mute is helper/amixer-only,
   set_mute helper.py:416-435), and helper death already costs heartbeats,
   mute, reboot, points, and cues — i.e. spatial shows already stake control
   on helper. The loss is real but marginal, and it is buyable back: systemd
   auto-restart bounds the outage to seconds, and the mute-spam procedure
   (§4) already falls back to engine-stop. Accepted as a **bench-gated risk**,
   not a veto.
3. **Probe machinery count — contrarian PARTIALLY RIGHT.** The io→helper arrow
   is unbuilt (verified §5 above); a leased touch stream is net-new plumbing
   (lease state, timer, teardown, io upstream publisher). But a **one-shot
   unicast probe** answering sources helper already reads is nearly free and
   still deletes the whole `/rpt` chain. Ruling: one-shot now, lease specified
   but deferred until the touch-debug need actually lands.
4. **Run-context boot race — CONFIRMED.** Context arrives atomically in the
   `pd … -send "; RANDOM …; STARTDATE …"` launch line
   (bash/start-engine.sh:91); the SC starter's `/config` ask (main.scd:120)
   has no retry — a slow helper means a context-less engine. Operations'
   ownership-not-transport split is correct and adopted.
5. **Pi Zero relay cost — NEGLIGIBLE.** `/pt` already relays through helper at
   ≤30 Hz (helper.py:545-584 path, client at :42-44); cues already ride the
   same client (helper.py:1028-1036). The consensus adds only master/params at
   <1 msg/s. The real defect found here is the **unlocked `OSCClient` shared
   by the cue-scheduler and LAN-listener threads** — a pre-existing race that
   gets a lock regardless of topology.
6. **The re-litigation charge — PARTIALLY ACCEPTED.** §4 names PD the 6660
   listener and §4.1 says "PD retains its deployed direct 6660 routing path";
   seam-5 (tied yesterday) said the same. Changing this is a **revision, and
   must be presented as one** — the experts calling it a "clarification" were
   wrong. But it is a *legitimate* revision: the evidence (SC cannot share
   6660; macOS stock PD cannot either, errno 48; PD's 5550 broadcast fails on
   macOS, errno 49 — audition-0/1b results) post-dates v1.1's drafting, §13's
   fleet guarantees are untouched (zero port *numbers* change, no reflash, no
   flag day), and CLAUDE.md explicitly permits explicit, justified revisions.
   The contrarian's narrower point — errno 48/49 are audition-only and
   deleting `/rpt` alone dissolves errno 49 — is factually right; the
   production-Mac N=1 case is untested and goes on the bench list.

## 5. The ruling, in detail

**LAN ingress.** `bopos.py` (née helper) is the sole binder of LAN 6660 and
sole sender to 5550 on every device. Engines never touch a LAN socket. In
audition, `tools/audition.py` plays the identical role with N virtual
identities; production is the N=1 case. (Cleanup note: unify the two relays'
OSC libraries — helper uses pyOSC3, audition python-osc.)

**Engine-facing surface (localhost 6661, identical for PD/SC/oF), the stable
vocabulary:**

```
/id <n>            identity (pushed on assign; answered to /config)
/os/master <0..1>  master term, selector-stripped
/p/<name> <v…>     patch params, selector-stripped
/pt <point> <element> <v>   point proximity scalars
/cue <id>          relative cue fire
/notify <event>    framework audible events (identify, provisioning acks)
```

Engine→framework, localhost 7770, request-only: `/config`, `/store`, `/load`,
`/report <name> <values…>` (patch-authored values for the probe facility).
Never admin. Engine→io control stays on 8880; io→engine stream stays on 6662.

**PD bus glossary** (the `[bopos]` façade in `bopos.pd` is the only
transport-aware object; prefix = direction): in — `bopos-master`,
`bopos-param`, `bopos-point`, `bopos-cue`, `bopos-notify`, `bopos-io`,
`bopos-context`; out — `to-bopos-io`, `to-bopos-report`. Hyphenated, matching
the existing good half (`bopos-notify`, `to-bopos-io`); `osc-in`, `osc-out`,
`ID`, `PX`, `PY`, `route-by-id`, and all in-patch selector/id routing are
deleted. SC uses the same nouns on the same 6661 grammar — the two starters
become the same document.

**Identity & run context.** `bopos.py` owns both. `/id` stays OSC (push on
assign; `/config` answered always, engine retries until answered). Run
context (`seed`, `run` id string, `patch`, `assets`) is **generated by a
bopOS-owned step and delivered at launch** (`-send`/env via start-engine.sh)
— no OSC-at-boot; absolute wall time never enters an engine (§12); standalone
boot degrades to standalone, never to a silent engine.

**IO.** 6662/8880 kept as a measured performance boundary (10-100 Hz
peripheral bundles never contend with control on 6661; a blocked I2C read
never stalls the engine surface). io's `/system/*` facts are marked
deprecated in favor of `/os/report` (prune later; not load-bearing).

**Meters: deleted.** `meter_loop`, `METERS`/`METER_INTERVAL` config, and the
streamed `role:"meter"` transport go. `role:"meter"` survives only as a
manifest UI hint ("render read-only") for values a patch chooses to publish.

**Reports/diagnostics.** Delete the `/rpt` chain, `route echo`, the 6661
fallthrough-to-LAN, PX/PY prints, and `bopos.feedback.pd`. Add
`/<id>/os/probe <what>` → unicast `/os/probe <id> <what> <values…>` reply,
one-shot, answering sources bopos.py already holds (rssi, cpu_temp,
patch-reported values). The **leased form** `/<id>/os/probe <what> <hz> <ttl>`
(≤10 Hz, TTL ≤60 s, unicast, timer owned by bopos.py, auto-expiring) is
ratified as the wire shape but **built only when the touch-debug need lands**,
because it requires the new io→bopos.py upstream. Bounds: one-shot ≈ free; an
active lease ≤10 Hz × ~150 B ≈ 1.5 KB/s unicast to one requester, O(1) in
fleet size, zero by default. Everything else on the LAN stays as today:
heartbeats O(N) at 0.1 Hz, `/pt` O(1) at ≤30 Hz ≈ 3-4 KB/s, control events
<1/s. Nothing new touches the broadcast channel.

**Production vs audition.** One topology. Engines take their ingress port from
launch context (`BOPOS_ENGINE_PORT`, default 6661); audition instances stop
attempting the fixed 6660/6661/6662 binds (errno-48 noise gone).

**Naming — ruled explicitly, per Bob's note.** The rename condition ("only
alongside a clarified role") is now met: the process that owns LAN ingress,
identity, sync/cue, provided-term relay, persistence, and the probe is not a
"helper." **`helper.py` → `bopos.py`: ratified**, landing as a separate,
behavior-free commit *after* migration stages 0-2 (operations' bisect
argument — never mid-migration). **`bopos.osc.pd` → `bopos.pd` exposing
`[bopos]`: ratified**, landing in Bob's PD edit wave with the bus glossary.

**Contract v1.2** (explicit revision, §13 guarantees intact): §4 table —
6660 listener becomes bopos.py (all engines), 5550 sender becomes bopos.py
only, 6661 listener "engine (PD/SC/oF)", 7770 becomes engine→framework
request-only; §4.1 — one delivery column for all engines, the "PD retains its
direct path" sentence removed; §6 — add `/os/probe`; §8/§11 — meters
deleted/redefined; §13 — note the `/helper/*` alias now lives in the 6660
listener. Node-internal, no contract text: bus renames, the façade, launch
context, the client lock.

## 6. Rejected, and why

- **Heterogeneity as the end-state (contrarian §4).** Rejected: it freezes the
  two-spellings asymmetry into doctrine, keeps production and audition as
  different topologies, and preserves a redundancy that is PD-only,
  master-only, and already absent from every spatial show. **Accepted from
  the dissent:** the alias-first ordering, the client lock, the honest
  mechanism count on the probe (hence one-shot-first), the demand that §4/§4.1
  changes be a named revision, and the bench gates in §7.
- **Simplifier's deletion of 6662** — rejected; transport's isolation argument
  is measured, and folding io into 6661 couples a blocking I2C stream to the
  control surface to save one port number.
- **Engine-api's OSC `/config` pull for run context** — rejected on
  operations' boot-race evidence; ownership moves, transport stays launch-time.
- **Creative-tools' full lease subsystem now** — deferred, not rejected; the
  wire shape is ratified, the build waits for the need.
- **Dropping meters' replacement entirely** — no; the one-shot probe is cheap
  and covers the "is box 3 alive-and-loud" question.

## 7. Risks & open questions (bench list)

1. **Helper-death drill (the contrarian's test):** kill/hang bopos.py mid-show
   on a rig; measure time-to-restored-control with systemd `Restart=always`;
   confirm mute-spam falls back to engine-stop. If recovery is not seconds,
   revisit the sole-binder ruling before the PD bind is removed.
2. **Production Mac, N=1, PD binding nothing:** verify the relay path on a
   single-engine Mac (untested today; the errno record is audition-only).
3. **Client race:** lock `client.send()`; soak-test cue+LAN threads.
4. **`/config` retry:** the SC starter needs a retry loop; verify a slow
   bopos.py boot self-heals.
5. **Touch-debug demand:** the leased probe and io→bopos.py upstream are
   unbuilt; do not build until Bob actually reaches for it.
6. **Hardware verification** of the whole seam needs a real rig (say so in
   stitches; don't claim it).

## 8. Recommended first slice, then sequence

**First slice (reversible, Python-only, no wire change, no .pd edit):** add
the `/helper/*→/os/*` alias to `handle_lan_datagram` and a lock around
`client.send()`; verify via simfleet that a legacy `/<id>/helper/reboot`
reboots with the engine killed. Revert = delete the alias.

Then, in order:
1. **Agent:** drop the `!= "pd"` guard (helper.py:645) so master/`/p/*` relay
   to PD *in parallel* with its 6660 path (idempotent duplicates are harmless);
   verify on audition rig + simfleet that PD hears everything on 6661.
2. **Agent:** delete the 7770 admin handlers (keep `/config /store /load`);
   add `/os/probe` one-shot; delete `meter_loop`. Run the helper-death drill.
3. **Bob (.pd edit wave, specified not implemented):** remove the 6660
   `netreceive`, `route helper` forward, `route echo`, id routing, PX/PY;
   adopt the `bopos-*` buses and the `[bopos]` façade; retire
   `bopos.feedback.pd`; parameterize the ingress port. Bench on Mac N=1.
4. **Agent:** launch-context generator + start-engine.sh sourcing; SC starter
   retry; audition.py fixed-bind cleanup.
5. **Agent:** contract v1.2 text; then the behavior-free rename commits
   (`helper.py`→`bopos.py`, `bopos.osc.pd`→`bopos.pd`).
