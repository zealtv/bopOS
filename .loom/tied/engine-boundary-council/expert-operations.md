# Expert design — Operations & rig reality

## 1. Lens & altitude

I am the seat that asks what happens at 3am when the WiFi is lossy, the engine
has crashed, and Bob is holding an iPad in a dark room. I judge every proposed
relocation of responsibility by two things only: its **failure story** and its
**migration story**. My altitude is deliberately low — I work at the level of
"who actually answers this packet, and what breaks if that process is dead" —
because the elegant boxes-and-arrows redesigns the other seats will draw are
invalidated by exactly one or two concrete facts about the deployed wire, and
finding those facts is my job.

## 2. Problem reframing

The brain dump reads as "PD forwards admin back to helper — smell — fix the
boundary." The ground truth reframes it: **helper already owns LAN admin.**
`handle_lan_datagram` (helper.py:775-791) handles `/os/reboot`,
`/os/restart-engine`, `/os/shutdown`, and all provisioning verbs *directly on
6660*, in its own process, with no PD involvement. The PD→7770 forward
(`process-helper-messages`) is not the reboot path — it is a **legacy
`/helper/*` alias path** that predates the contract listener. So the real
questions are not "should helper own admin" (it does) but:

1. What *only* the PD forward still serves, so cutting it doesn't orphan a
   deployed dashboard.
2. Whether identity/run-context delivery has a boot-order race.
3. How to make production and audition one topology instead of two.

The engine-dead reboot story is already sound. My job is to not regress it while
deleting the smell.

## 3. Proposed design

**Command ingress: helper owns the LAN, full stop.** helper's 6660 listener is
the actor for all `/os/*` lifecycle and provisioning. The PD→7770 forward is
deleted. 7770 survives as the **engine→helper local request channel only** —
`/config`, `/store`, `/load` (things the engine legitimately *initiates*) — and
the lifecycle/provisioning handlers are removed from the 7770 `OSCServer`
(helper.py:1051-1057) so there is exactly one code path per admin verb.

**The load-bearing migration constraint (the reason ordering matters):** today
the *only* handler for `/<id>/helper/reboot` is the PD forward — helper's 6660
listener rejects anything whose plane isn't `os` (helper.py:678). Deployed Kite
Choir / Plants dashboards are the *old* dashboards; the new one is `.waiting` on
rig adoption. Old dashboards speak `/helper/*`. **Therefore the `/helper/* →
/os/*` alias promised in §13 must be added to helper's 6660 listener *before*
the PD forward is cut.** Cut it first and legacy reboot dies silently. This is
the whole migration in one sentence: *alias in helper, then delete in PD.*

**Engine-dead reboot story, stated plainly:** dashboard broadcasts
`/<id>/os/reboot` (or legacy `/<id>/helper/reboot`) to 6660 → helper's own
listener, in its own process, reboots the box. PD being dead is irrelevant —
which is the entire point of helper heartbeating to 5550 directly. Deleting the
PD forward *strengthens* this by removing the illusion that reboot rides through
the engine.

**Identity & run-context: move ownership, not transport.** Bob wants
RANDOM/STARTDATE/STARTTIME/ACTIVEPATCH out of the shell `-send` and into bopOS's
domain. Correct on ownership — but delivering them over OSC at boot introduces a
race the shell `-send` does not have: engine starts, asks helper, helper must be
up and must reply, or the engine runs context-less. The launch-context path
degrades to *standalone* (the first-class mode); the OSC-ask path degrades to a
*silent, context-less engine*. So: **helper computes and owns these values and
writes them to a launch file/env that `start-engine.sh` sources**; the engine
still receives them atomically at launch. Ownership moves to helper; transport
stays race-free. `/id` stays as-is: engine asks `/config` on 6661-bind and
helper always answers with the resolved id (helper.py:846-850), and
`apply_assign` re-pushes `/id` on reassignment. Keep the engine's `/config` ask
on a retry until answered, so a slow helper boot self-heals instead of leaving
the engine id-less. Absolute date/time should ride as opaque strings (a run-id
is cleaner and §12-safe); they are launch context, never clock.

**Mute: unchanged, and I will veto any change to it.** Mute rides
helper/amixer below the engine (§6). Nothing here touches helper's 6660 listener
or `set_mute`, so mute is untouched by construction. Any redesign that routes
mute through the engine abstraction or a relay is a regression I reject: mute
must remain the one control that works with a dead/crashed engine.

**Report/diagnostic surface: kill the broadcast, keep a deadman tap.** The
`/rpt` echo (anything on `osc-out` → broadcast 5550) is deleted along with
`route echo`, the `PX`/`PY` prints, and framework meters (Bob blessed dropping
meters). Its one real use — watching capacitive-touch during install — is served
by **report-on-request, unicast, deadman-timed**: a dashboard-initiated
`/<id>/os/tap <peripheral> <seconds>` that helper fulfills by unicasting io
values to the requester for a bounded window, auto-expiring. This must be
unicast and time-boxed or it recreates the exact jam Bob flagged, on a transport
(broadcast to 5550) that is *already broken on macOS* (errno 49, audition-1b).
Static facts stay on the existing pull `/os/report`. No permanent stream, no
patch-authored forward, no §14 telemetry violation.

**Audition vs production: one topology, parameterized by launch context.** Today
every PD binds fixed 6660/6661/6662 even under audition, logging errno 48 on
macOS. The fix: the engine abstraction takes its ingress port(s) from launch
context (`BOPOS_ENGINE_PORT`), with production defaults being the deployed
numbers. Production = default parameterization; audition = per-instance ports.
Same code path. helper (production, one engine) and `audition.py` (N engines)
are then the *same role*: a LAN-fronting relay that strips selectors and fans
out a selector-stripped local surface — exactly what seam-5 already does for SC.
The elegant end-state is PD *also* consuming that local surface instead of
binding 6660 itself, unifying PD and SC — but that is a real PD rewrite with
flag-day risk, so it is opt-in and last (Stage 4 below), never a fleet event.

**Staged migration (no flag day):**
- **Stage 1 (helper-only, reversible):** add `/helper/*→/os/*` alias to helper's
  6660 listener; delete the PD forward and the duplicate 7770 lifecycle/provision
  handlers. Verify reboot/restart via simfleet. Zero wire change to dashboards.
- **Stage 2 (Bob PD edit):** parameterize engine ingress ports from launch
  context; production defaults unchanged → zero wire change, kills audition
  errno 48.
- **Stage 3 (helper + shell):** helper owns run-context via a launch file/env;
  shell sources it. No OSC round-trip.
- **Stage 4 (opt-in, per-rig, last):** PD consumes helper's local selector-
  stripped surface instead of binding 6660, converging with SC. Per-patch, never
  fleet-wide.
- Cruft removal (`/rpt`, echo, PX/PY, meters) lands per-patch, since §13 already
  rewrites patches in lockstep.

## 4. How it fits the existing system

**Stays:** six-port map, mute path, heartbeat-direct-to-5550, `/os/report`
pull, `/pt`/`/cue`/master delivery, 6661/6662/8880 local plumbing, standalone
operation. **Changes:** PD→7770 forward deleted; 7770 reduced to
config/store/load; `/helper/*` alias moves into helper's 6660 listener;
`/rpt`/echo/meters deleted; run-context ownership moves to helper via launch
context. **Contract revisions needed:** §6/§11 — drop framework meters; §6/§7 —
add the deadman `/os/tap` (or explicitly rule it out and accept only static
`/os/report`, which I'd also accept). **§13 compliance:** zero port changes, no
reflash, uid==MAC preserved; `/helper/*` alias honored for one release *in the
right process*; patches rewrite in lockstep as already ratified.

## 5. Why it's elegant / right

Against Bob's taste — simple, clean, understandable, performant — the win is that
the failure story gets *shorter*. Before: "reboot rides LAN→PD→7770→helper, and
also LAN→helper, and `/helper/*` only works through PD." After: "the dashboard
talks to helper; helper is the actor; the engine only ever receives things it
enacts." A patch author holds one rule in their head — *the engine receives, it
never administers* — and an operator holds one rule — *if helper heartbeats, the
box is manageable even with a dead engine*. That is the design collapsing two
overlapping ingress surfaces into one, with no new capability and no lost one.

## 6. Tradeoffs, risks, what I am NOT solving

- **The `/helper/*` alias is the trap.** Any seat that says "cut the PD forward,
  helper already owns admin" without adding the alias *first* orphans every
  deployed dashboard's reboot. This ordering is non-negotiable.
- **Ownership ≠ transport.** Any design that delivers identity/run-context to the
  engine over OSC at boot must answer: what runs when helper is slow or down at
  boot? The honest answer is a silent engine; the launch-context path degrades to
  standalone. I reject OSC-at-boot for context.
- **Any live-tap that broadcasts is invalid** — it rebuilds the `/rpt` jam on a
  macOS-broken transport. Deadman + unicast or nothing.
- **Rename helper.py→bopos.py and the bus renames are cosmetic** and must land in
  a separate, behavior-free commit. Renaming mid-migration destroys the ability
  to bisect a 3am failure; do not bundle it with the forward deletion.
- **Not solving:** Stage 4's PD-consumes-local-surface rewrite (Bob-owned,
  bench-gated); DigiAMP mute-control bench verification (still owed); multi-
  element engine topology.

## 7. Smallest first step

Stage 1, and only its safe half first: **add the `/helper/*→/os/*` alias to
helper's 6660 `handle_lan_datagram` and verify a legacy `/<id>/helper/reboot`
now reboots via helper alone (simfleet, engine killed).** This is a pure
addition, fully reversible, changes no wire, and *proves the engine-dead reboot
story is real and not PD-dependent* before anything is deleted. Only once that
verifies green does the PD forward and the 7770 duplicate come out.
