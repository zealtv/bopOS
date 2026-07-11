# Engine boundary — the Simplifier's design

## 1. Lens & altitude

I am the existence-challenger. My first move is deletion; abstraction is my last
resort. I judge this design by two numbers: **how much a newcomer must learn
before their first patch makes sound**, and **how many distinct mechanisms exist
for one job**. I sit one level above the wiring, at "what is the minimal set of
mechanisms," because the brief's own smells (§9 of ground-truth) are all
*duplication* — two ingress surfaces, two spellings of `master`, two admin paths,
three fixed binds per engine. You don't cure duplication one wire at a time; you
name the one true shape and delete everything that isn't it.

## 2. Problem reframing — the count

**Distinct mechanisms that put a value in front of the engine today: four.**
(1) PD binds LAN 6660 itself and selector/id-routes in-patch. (2) helper's 6661
client pushes `id/pt/cue/load/identify`. (3) helper's 6661 *selector-stripped
relay* for non-PD engines (`/os/master`, `/p/*`). (4) the shell `-send` startup
message (`RANDOM/STARTDATE/…/ASSETS`). **Ingress surfaces at helper: two** (the
contract-speaking 6660 listener *and* the legacy selector-free 7770 OSCServer,
which handle the same admin verbs). **Engine outbound: two** (PD→7770 admin
forward, PD→8880 io). **Fixed engine binds: three** (6660/6661/6662), even for an
audition instance that also has its own `BOPOS_ENGINE_PORT`. So `master` arrives
at PD as `os master` on the `osc-in` bus but at SC as `/os/master` on 6661 —
*the same term, two paths, per engine*. That asymmetry is the disease.

Two facts make the cure obvious. **First: helper already binds 6660 and already
handles every admin verb directly** (helper.py:775-791, `LIFECYCLE_VERBS`/
`PROVISION_VERBS`). The 7770 admin handlers and PD's `route helper` forward exist
*only to serve each other* — helper hears the identical LAN packet without PD's
help. **Second: `tools/audition.py` already owns 6660 and fans out
selector-stripped terms to each engine's local port** (ground-truth §6). The
"unified relay" I'm about to propose is not speculative — it is running in the
audition rig today, for N engines. Production helper should simply do what the
audition relay already does, for one.

## 3. Proposed design — one door in, one door out

**The engine sees exactly two localhost ports, identical for PD / SC / oF:**
`6661` in (everything the framework provides, selector-stripped) and one egress
to the framework. No engine ever binds a LAN port. No engine ever selector-routes.

**Deleted outright:**

- **PD's LAN 6660 bind.** helper owns 6660 for *all* engines and relays the
  engine-bound subset selector-stripped on 6661. This merges mechanisms (1) and
  (3) into one — there is no "PD path" and "non-PD relay," only *the* 6661
  surface. It also dissolves the macOS shared-socket problem (only helper binds
  LAN sockets; ground-truth §6) and smell #7 (audition instances need no fixed
  6660/6661/6662 binds).
- **The 7770 admin path** — PD's `route helper`→`process-helper-messages`
  forward *and* the 7770 OSCServer's ten admin handlers. helper's 6660 listener
  already does this job. Kills smells #1 and #8 (dual ingress).
- **PD's `route-by-id`, `s ID`, `route id`-off-`osc-in`** selector/identity
  machinery. helper selector-filters before delivery; identity is framework
  state, delivered, not derived in-patch (smell #2).
- **Meters, entirely** (Bob's blessing). No `meter_loop`, no `METERS`/
  `METER_INTERVAL` config, no `role:"meter"`. A "level" a patch wants seen is
  just a `/p/<name>` it chooses to publish — no framework meter concept exists.
- **The `/rpt` echo path**: `s osc-out`→broadcast-`/rpt`-on-5550, `route echo`,
  the 6661 fallthrough-to-LAN, and the `PX/PY` dev prints (smell #5). This is the
  broadcast chatter that also happens to be broken on macOS (errno 49).
- **The shell `-send` startup context as a separate mechanism.** Run context
  folds into the identity reply (below).
- **6662.** io writes the engine's *single* ingress port (6661), not a second one.

**What merges:**

- **Run context into the identity reply.** When the engine comes up it sends one
  `hello` on its egress port; helper replies on 6661 with `id` plus
  `ACTIVEPATCH/ASSETS/RANDOM` in one shot (dates as strings or dropped — absolute
  time stays out, §12). One mechanism answers "who am I and what is my world,"
  replacing the `/config` dance *and* the shell send (smell #3).
- **The two provided-term spellings into one.** §4.1's delivery column collapses:
  helper relays *every* provided term selector-stripped on 6661 to *every*
  engine. PD stops being special. `bopos.out~` receives `master` on the same
  `from-bopos` bus SC does.
- **io stays a separate process** (I2C polling can block; a hung read must not
  stall heartbeats — that isolation is *justified*, not historical), but its
  engine-facing wire collapses: io→engine writes 6661 (the one door in);
  patch→io control rides the engine's one egress and helper demuxes it to io
  internally. The patch author never learns an io port.

**Engine-facing seam after:** `6661` in, one egress out. **That is the whole
API a starter patch binds.**

**Port/process diagram:**

```
        dashboard (LAN)
      5550 ↑        ↓ 6660           ← unchanged wire (helper owns both)
   ┌─────── helper.py (bopos.py) ───────┐
   │   owns LAN, identity, admin,       │
   │   sync/cue, provided-term relay,   │
   │   persistence, io demux            │
   └── 6661 ↓ (from-bopos)   ↑ egress (to-bopos) ──┘
            │                │
         engine  ←── 6661 ── io/main.py (I2C isolation; framework-internal)
      (PD/SC/oF: binds 6661, sends egress — nothing else)
```

## 4. How it fits — changes vs stays, contract impact

**Stays:** LAN wire (5550/6660), `/hb`, assignment, sync/cue plane, the seam law,
manifest/params. **§13 holds intact:** zero LAN port changes, `uid == MAC`, no
reflash, no flag day. Patches rewrite in lockstep (already sanctioned) — the PD
patch loses its 6660 bind and its `route helper`/`route echo` forwards.

**Node-internal, no contract change:** who binds 6660 (helper vs PD), deleting
the 7770 admin redundancy, `/rpt`/echo/`PX`/`PY` removal, renaming `osc-in`/
`osc-out` → `from-bopos`/`to-bopos`.

**Needs an explicit contract revision:** §4 table (6660 listener PD→helper; drop
6662; 7770 becomes the generic engine→framework egress; note engines bind only
6661+egress). §4.1 delivery column (one relay, all engines). §8/§11 (delete
`role:"meter"` and the framework meter loop). And the one *addition* below.

## 5. Why it's right — the learn-before-first-sound argument

Today a patch author must learn: three inbound ports, two of which they must not
collide on across instances; that `master` is spelled two ways depending on
engine; that admin arrives on the LAN and must be forwarded back to a Python
process on a fourth port; and a bus vocabulary (`osc-in`, `bopos-notify`,
`to-bopos-io`, …) that mixes transport with ownership. **After: bind 6661, read
selector-stripped terms; send to one egress to talk back.** Five sentences, and
PD and SC starters become the *same* document with a different syntax. The
newcomer's first sound needs one port and one bus. That is the entire case.

## 6. Tradeoffs, risks, what I delete

- **I delete meters.** Anyone wanting continuous device VU loses it. Mitigation:
  the report-on-request facility below covers the *one real* use (Bob's
  capacitive-touch debug), and any patch can still publish a `/p/<name>` it wants
  the dashboard to render.
- **PD stops binding the LAN.** Real risk: PD's in-patch routing was battle-tested
  in deployed installs. Mitigation: helper's 6660 path is already live and
  simfleet-exercised; migrate behind it, don't flag-day it (step 7).
- **The one *addition* I must be honest about — report-on-request.** To replace
  the `/rpt` chain without reintroducing §14's rejected telemetry-streaming, I
  add a *bounded pull*: `/<id>/os/tap <source> <ttl>` → helper unicasts that io
  source to the requester, rate-limited, auto-expiring, **off by default**. It is
  categorically not a stream (finite TTL, unicast, demand-driven), but it *is*
  new surface and needs deliberate ratification, not a silent slide-in.
- **Not solving:** the io *internal* helper↔io transport (thread vs localhost
  pair) — an implementation choice below the seam. And I keep three processes;
  merging io into helper is tempting but the blocking-I2C isolation is a real
  reason, so I stop at deleting io's *engine-facing* ports, not the process.

## 7. Smallest first step

**Delete PD's `route helper`→7770 forward and the 7770 admin handlers — nothing
else.** helper's 6660 listener already handles every admin verb; this slice is
pure subtraction with an existing safety net, and simfleet already drives
`/os/reboot|update|checkout` on 6660. Verify the fleet still reboots/updates via
helper alone, then proceed to the 6660-bind move and the 6661 unification. It is
instantly reversible (re-add PD's forward) and proves the load-bearing thesis —
*helper already owns ingress* — before any wire moves.
