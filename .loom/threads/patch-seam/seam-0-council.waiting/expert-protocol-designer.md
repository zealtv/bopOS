# Expert response — protocol designer

## 1. Lens & altitude

I sit at the wire and the manifest. I judge a design by three tests: does a
stray packet in a broadcast log describe itself; does the change survive lossy
one-to-many delivery under the §4 idempotent law; and is the diff against the
ratified contract small, precise, and alias-migratable per §13. I deliberately
choose the **concrete-mechanism** altitude — exact addresses, args, and
manifest JSON — because Bob's real question ("how much of a redesign is this?")
is only answerable in the currency of amendment lines. My headline answer:
**small.** Three additive amendments, zero port changes, no new plane, one
one-release alias. The redesign is philosophical, not structural — and it
*deletes* machinery.

## 2. Problem reframing

"Provided, not enforced" is, in protocol terms, a statement about **who
composes the final value and where.** Today the dashboard composes
`mix × master` and streams the product into `/<id>/p/<gain>`
(`osc_bridge.py:135`), so the patch never sees master and the framework owns an
output-semantic it swore it didn't (§1). The fix is to move composition across
the seam: bopOS *broadcasts the ingredient*, the patch *does the multiply*.
That is the same move the spatial redesign already made for points (broadcast
geometry, decompose node-side). So the seam has **one shape with two delivery
channels**: fleet-global constants ride the LAN broadcast straight to the
engine socket; per-device derived values are computed by helper and handed over
localhost. Mute stays the sole *enforced* framework output control. Everything
else the framework offers is a subscribable value the patch may ignore.

## 3. Proposed design

### 3a. Master — the type case (`/os/master`)

Add one address, on the plane where the *other* framework output control
already lives:

```
/all/os/master <gain:f>     dash → fleet, broadcast, 6660, idempotent full-state
```

This is deliberately a sibling of `/all/os/mute <0|1>`. The two are the
framework's **only** output-affecting controls, and they differ in exactly the
axis the principle names: **`/os/mute` is enforced (helper amixer, below the
patch); `/os/master` is provided (broadcast, the patch multiplies it into its
own signal path).** One is safety, one is courtesy. A `0.5` on
`/all/os/master` in a log is self-describing; a dropped frame self-heals on the
next master move because it is absolute full-state, never a delta.

The patch subscribes by having a receiver and multiplying master upstream of
its own volume — **a PD edit, flagged for Bob** (house rule 23). bopOS's job
ends at broadcasting the scalar.

Whether the dashboard composes for a given device is a **declared fact**, not a
guess. Manifest top-level:

```json
"subscribes": ["master", "point"]
```

`subscribes` lists framework surfaces the patch enacts itself. If a device's
manifest subscribes to `master`, the dashboard sends the **raw mix** as
`/<id>/p/<volume>` and lets `/all/os/master` ride separately. If it does not
(legacy patch, no master receiver), the dashboard composes `mix × master` as
today — honest per-device degradation, the §8 "fail loud" ethos. This deletes
`resend_volumes` (`osc_bridge.py:146`) for subscribing devices: instead of N
per-device re-sends on every master nudge, **one broadcast**. Less coupling,
less traffic.

### 3b. Points — provided value, localhost delivery

I concur with the S1 draft and settle its open §2/§8 questions the protocol way:

- LAN wire: **encoding B (per-frame, atomic)** —
  `/pt <n> <id0> <x0> <y0> <r0> <f0> …`. All points advance on one datagram
  (matches a sequencer tick), a point absent from the frame is gone, MTU-bounded
  to dozens. `falloff` is a **small enum int** (0=linear,1=smooth,2=gauss), not
  a string — it survives PD's 32-bit floats trivially and needs no string
  parsing on the node. Keep the per-point sparse form `/pt <id> <x> <y> <r> <f>`
  for authoring edits (idempotent overwrite; `/pt/clear <id>` removes).
- Localhost delivery: helper decomposes to a shaped `0→1` proximity and hands
  the patch a **named value** — receiver spelling is Bob's (`/pt/<id> <v>` is my
  lean). **No manifest declaration of point params for v1** (`subscribes:
  ["point"]` at patch granularity is enough; per-point declaration is UI sugar
  we add only if the dashboard needs to show which points a device renders).

### 3c. Facilitator promotion — manifest metadata, not dashboard config

Promotion **must travel with the patch**, for the identical reason params do:
engine-neutral, git-diffable, survives re-deployment. A dashboard-side per-patch
config would drift from the patch it describes. So promotion is manifest.

Per-param opt-in (co-located, no duplication):

```json
{"name":"reverb","type":"f","min":0,"max":1,"default":0.2,
 "facilitator":{"label":"Room","order":2}}
```

Any param carrying a `facilitator` object renders as a control on `/facilitator`
(ordered by `order`, labelled by `label`). `role:"volume"` still implicitly
promotes the volume card. That closes the seed's "custom subset of controls"
ask with one optional field.

For **bopOS commands on the facilitator** (the tension with the ratified scope
guard, ground-truth #9): I take a position. The guard exists so a facilitator
can't reboot the rig mid-show *by accident*. It should not forbid the patch
author (Bob, at design time, in git) from promoting a curated verb. Resolve it
as an explicit, closed opt-in — top-level manifest:

```json
"facilitator": {"commands": ["restart-engine", "shutdown"]}
```

Only verbs named here appear, rendered as confirm-gated buttons that emit the
existing `/all/os/<verb>` / `/<id>/os/<verb>`. The guard becomes "no admin verbs
*unless the manifest promotes them*" — still a closed set, still declared, no
new wire. Bob arbitrates the default (my recommendation: empty by default).

### 3d. Element addressing — additive sub-selector, staged

The wire and node persistence **already carry two positions**
(`helper.py:491`, the Belief-era `pos2` remnant). Element addressing is latent;
we make it explicit without touching device addressing.

- **Assignment generalises to a position list** (§5), one pair per element:
  `/all/os/assign <uid> <id> <name> [x0 y0 x1 y1 …]`. Today's `pos2` is
  retconned as element 1. Fully backward compatible.
- **Sub-selector `<id>.<el>`** addresses an element:
  `/12.1/p/gain 0.5` = device 12, element 1. Route-by-id splits on `.`; the
  base id delivers the packet, the `.el` suffix is consumed by helper/patch
  (PD receiver convention — flagged). Bare `/12/...` = whole device (element 0
  implicit). `/all/...` unchanged.
- Manifest declares count: `"elements": 2` (default 1; **same patch per
  element** — the seed's allowed simplification). One engine instance runs N
  logical elements (localhost ports stay singletons — the engine's job, flagged).
- helper computes **N proximity values** (one per element position) and delivers
  each to its element.

**No new dashboard mode.** A device with `elements>1` renders additively as a
group of element sub-cards + N position handles; every `elements:1` device is
untouched. Multi-element is an S2 stage; S1 ships single-element with the
position-list wire as the forward-compat hook.

## 4. How it fits the existing system

- **osc_bridge.py:** add `send("/all/os/master", [m])`; gate the `mix × master`
  multiply in `send_device_param` on `not subscribes("master")`; delete
  `resend_volumes` for subscribers. Facilitator render reads the new manifest
  fields already carried in `device["declared"]` / manifest.
- **helper.py:** already ignores non-admin `/os/*` on 6660, so `/os/master`
  needs no node handler (it is for PD); add `/pt` decomposition + element fan-out
  (S1/S2). `apply_assign` already stores a position list (`helper.py:502`).
- **simfleet.py:** parse `/pt`, decompose per element, log the named value
  (same-stitch house rule); accept `/os/master` inertly.
- **Migration (§13):** master alias window = one release — subscribing devices
  use `/os/master`, non-subscribers keep composed `/p/<gain>`, both coexist
  per-device with zero flag day. No port change, no reflash.

## 5. Why it's right

It honors "provided, not enforced" by making the seam a *wire fact*:
`/os/mute` (enforced) and `/os/master` (provided) are visibly one plane apart in
only the enforcement axis. It **removes** coupling — dashboard-side composition
and `resend_volumes` go away; N re-sends collapse to one idempotent broadcast.

The closed-namespace-vs-growing-surface tension resolves cleanly: the provided
surface stays **closed and tiny** (mute, master, point, sync, cue), extended
only by contract revision exactly like the shorthand registry (§3). The
*unbounded* growth stays where it belongs — `/p/*`, patch-owned. "Provided, not
enforced" does not inflate the framework namespace; it reclassifies a handful of
closed-set addresses as subscribe-and-enact.

## 6. Tradeoffs, risks, not-solving

- Master does nothing until a patch adds the receiver (PD edit, Bob's). The
  `subscribes` gate makes this honest, not silent, but it is a real dependency.
- Dotted sub-selector leans on PD's route-by-id splitting on `.` — a receiver
  convention I flag, not fix.
- I am **not** solving: point authoring UI, sequencer integration, or the
  engine-side mechanics of running N elements in one process. Those are S1/S2 and
  scene-sequencing.

## 7. Smallest first step

Ship **master only**: add `/all/os/master` to §4/§6 and the wire; add
`subscribes` to §8; gate composition in `osc_bridge.py`; teach `simfleet` to
accept it inertly; alias one release. One address, one manifest key, one deleted
method — the type case proven before points and elements build on the same seam.
