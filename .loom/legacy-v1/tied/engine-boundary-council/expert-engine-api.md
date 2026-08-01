# Expert response — Engine API / patch-author ergonomics

## 1. Lens & altitude

I sit at the patch author's bench. My unit of judgement is the *one abstraction a
first-time author holds in their head* when they open `main.pd` or `main.scd`.
I zoom to the concrete local surface: the exact buses, the exact façade object,
the minimal patch in PD and SC side by side. I justify this altitude because
every higher-level ownership question (who binds 6660, where id routing lives)
only earns its keep if it *shrinks* what the author must learn. The seam law is
already ratified; my job is to make it teachable.

## 2. Problem reframing

The contract is clean; the *node interior* is not. The same provided term reaches
PD one way (PD binds 6660, does its own selector/id routing, delivers `os master`
on a vague `osc-in` bus) and SC another way (helper strips selectors and relays
`/os/master` on 6661). Two spellings, two code paths, two mental models for one
value — that alone fails the ten-minute test. Around it sits historical silt: PD
receives LAN admin only to forward it back to helper (which already handles it on
6660), id math lives in the patch, launch context arrives from a shell `-send`,
and a permanent `/rpt` echo broadcasts anything on `osc-out`. The real problem is
**one delivery path and one vocabulary for every engine**, with transport hidden.

## 3. Proposed design

**One rule for the author: `bopos-*` is what the framework tells me; `to-bopos-*`
is what I tell the framework.** Prefix = direction, suffix = plane. That sentence
is the whole surface.

### The façade

`bopos.osc.pd` → **`bopos.pd`**, exposing the object `[bopos]`. It is the *only*
transport-aware object a patch instantiates. Its entire job:

- bind **localhost 6661** (terms/params/context/cue/notify from `bopos.py`) and
  **localhost 6662** (io), parse, and fan out to typed `bopos-*` sends;
- collect typed `to-bopos-*` receives and emit to **7770** (`bopos.py`) and
  **8880** (io);
- on load, pull context (`/config` → 7770) and populate `bopos-context`.

It does **no** LAN bind, **no** selector routing, **no** id math, **no** admin
forwarding. Those move to `bopos.py` (see §4).

### Local bus vocabulary

Framework → patch (`[r …]`):

| bus | carries | replaces |
|---|---|---|
| `bopos-master` | `<0..1>` final gain term | `os master` off `osc-in` |
| `bopos-param` | `<name> <value>` dashboard params | `p …` off `osc-in` |
| `bopos-point` | `<pointId> <element> <v>` scalars | `bopos-points` |
| `bopos-cue` | `<cueId>` relative fire | `bopos-cue` (kept) |
| `bopos-notify` | lifecycle symbols (reboot/update/identify…) | `bopos-notify` (kept) |
| `bopos-io` | `<name> <values…>` from peripherals | `from-bopos-io` |
| `bopos-context` | `id / run / seed / assets / patch` | `ID`, `RANDOM`, `STARTDATE`, `STARTTIME`, `ACTIVEPATCH`, `ASSETS` globals |

Patch → framework (`[s …]`):

| bus | carries | replaces |
|---|---|---|
| `to-bopos-io` | peripheral control / `create poll` | `to-bopos-io` (kept) |
| `to-bopos-report` | `<name> <values…>` values to surface | `osc-out` / `/rpt` echo |

`osc-in`/`osc-out`/`ID` disappear. The kept names (`to-bopos-io`, `bopos-cue`,
`bopos-notify`) were already the good half of the vocabulary; the change is to
make *every* bus obey the same prefix law.

### Command ingress & identity

**`bopos.py` is the sole LAN citizen.** It already binds 6660 and speaks v1.1;
it already strips selectors and relays to 6661 for non-PD engines. The design
simply **extends that relay to PD too** and **removes PD's 6660 bind**. So:

- selector/id routing becomes framework state in `bopos.py` (Bob: "feels like a
  bopOS responsibility"). The engine only ever receives messages *already
  addressed to it* — no `route-by-id`, no `s ID` in the patch.
- the `route helper → 7770` forward is **deleted**: it was pure duplication
  (helper already handles those verbs on 6660). Smell #1 gone.
- the engine speaks to `bopos.py` on 7770 for exactly three things: pull context
  (`/config`), persistence (`store`/`load`), and report values. Never admin.

### The canonical engine-facing wire (6661)

One local grammar, identical for PD, SC, oF — this is the real deliverable:

```
/os/master <v>            /p/<name> <v>          /pt <point> <element> <v>
/cue <id>                 /context <k> <v…>      /notify <sym>
```

PD parses it with `oscparse`+`route`; SC with `OSCdef`; oF with its receiver.
Same spellings, same path, genuine equivalence. The "PD gets `os master`, SC gets
`/os/master`" asymmetry (ground-truth §7) is dissolved.

### Startup context

Kill the shell `-send`. On load the engine pulls `/config`; `bopos.py` replies
with `/context id <n> run <str> seed <int> assets <path> patch <name>`.
`RANDOM`→`seed`, `ACTIVEPATCH`→`patch`, `STARTDATE`/`STARTTIME`→ an opaque
per-launch `run` string (never a float; absolute wall time never enters the
engine, §12). One owner (`bopos.py`), one delivery, uniform across engines.

### Meters & the report path

Drop the framework "meter" concept. A meter is just a patch-authored value on
`to-bopos-report <name> <value>`, which `bopos.py` surfaces as the ratified
`/<id>/p/<name>` (§11) — directed, not PD's broken `255.255.255.255:5550`
netsend (fixes macOS errno-49). The author owns *what* and *how often*; off
unless published; a manifest `role:"meter"`/`debug` param gates it patch-side.
That is Bob's "report-on-request" without a new verb (§11 forbids one): demand
lives in the patch, not the framework. `bopos.out~` loses all `level`/report
wiring. The capacitive-touch case becomes: io → `bopos-io` → author republishes
`to-bopos-report touch …` when a debug param is on. `route echo`, the `osc-out`
broadcast, and `PX`/`PY` prints are deleted outright.

### Minimal patch — PD (pseudocode)

```
[bopos]                                  ; binds 6661/6662, no args
[r bopos-context] -> route id run seed assets patch
[r bopos-param]   -> route gain frequency -> synth
[r bopos-point]   -> [bopos.point 0]  -> proximity
[r bopos-cue]     -> route ping       -> action
[r bopos-io]      -> route touch       -> ...
[osc~ 220] -* -> [bopos.out~] -> [dac~] ; master+notify+mute inside
[s to-bopos-io]      <- "led 0 255"
[s to-bopos-report]  <- "touch $1 $2 ..."   ; surfaces as /<id>/p/touch
```

### Minimal patch — SC (equivalent)

```
OSCdef(\master,  {|m| ~out.set(\master, m[1])       }, '/os/master', recvPort:6661);
OSCdef(\param,   {|m| ~setParam.(m[0].asString, m[1])}, '/p/gain',    recvPort:6661);
OSCdef(\point,   {|m| ~point.(m[1],m[2],m[3])        }, '/pt',        recvPort:6661);
OSCdef(\cue,     {|m| ~cues[m[1]].value              }, '/cue',       recvPort:6661);
OSCdef(\context, {|m| ~ctx.(m)                        }, '/context',   recvPort:6661);
NetAddr("127.0.0.1",7770).sendMsg('/config');            // pull context
~report = {|n ...v| NetAddr("127.0.0.1",7770).sendMsg('/report', n, *v)};
~io     = {|n ...v| NetAddr("127.0.0.1",8880).sendMsg("/"++n, *v)};
```

The two patches are now line-for-line the same abstraction.

## 4. How it fits the existing system

- **Ports:** all six survive; the fleet wire is untouched (§13 satisfied). The
  only change is *which process binds 6660* — PD drops it, `bopos.py` keeps it.
  Node-internal, but it edits §4's listener table, so it needs a stated
  **clarification revision**, not a port change.
- **Provided terms / planes:** unchanged. `master`, `point`, `cue`, `/p/*`,
  `/io/*` all as ratified. The 6661 grammar is an *informative* "engine-facing
  local surface" subsection — node interior, not fleet contract.
- **Meters:** no wire change; collapses into §11's `/<id>/p/<name>`. `/rpt`
  (never a contract address) retired.
- **Context pull:** replaces shell `-send`; node-internal.
- Nothing here touches §14's rejected list: no consolidation, no new verb, no
  subscription stream, no term composition.

## 5. Why it's elegant / right

Transport-vs-terms is separated *by construction*: `[bopos]` is the only object
that knows a port exists; everything else is a named bus whose prefix states its
direction. A patch author learns two prefixes and seven receive buses in ten
minutes, and the SC author learns literally the same seven. Ownership follows the
contract's own instinct — the framework owns identity, selectors, and machinery;
the patch owns only what comes out. We *delete* more than we add: the PD→helper
forward, id routing, echo broadcast, dev prints, shell context, per-engine
spelling, the meter subsystem. That is the taste criterion — simpler, cleaner,
and faster (no double 6660 bind, no permanent broadcast chatter) — met by
subtraction.

## 6. Tradeoffs, risks, not-solving

- **All terms now ride 6661 into PD**, including 30 Hz points — but they already
  do (helper decomposes `/pt` to 6661 today); master/params/context are low-rate.
  No new per-frame load (§12 honoured).
- **`bopos.py` becomes more central.** Its death already stops heartbeats, so the
  failure stays visible; acceptable.
- **oF** gets a `bopos.of` wrapper (same two socket pairs, same callbacks) — I
  specify its shape, not its code.
- **Not solving:** the amixer mute matrix, sync internals, the manifest schema,
  and whether `helper.py` renames to `bopos.py` (I endorse it as the cosmetic
  *last* step; the role clarification is what matters, not the filename).

## 7. Smallest first step

Purely additive, Python-only, reversible, no `.pd` edit: in `bopos.py`, drop the
`!= "pd"` guard so master + params are relayed selector-stripped to 6661 for the
PD engine too, and add a `/config`→`/context` bundle reply. PD keeps its old
6660 path in parallel (harmless duplication) so nothing breaks. Verify with the
audition rig + simfleet that PD hears master/params/context on 6661. Once green,
Bob's PD edit (remove the 6660 bind, forward, id routing, echo, prints; add the
`bopos-*` buses) lands against a surface that already works.
