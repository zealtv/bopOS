# The seam from inside the patch — patch-author's ruling

## 1. Lens & altitude

I chose the **patch boundary itself**: the exact set of OSC messages that cross
localhost into the engine, and what the *minimal correct template patch* does
with each of them. That is the altitude where "provided, not enforced" either
becomes livable or becomes the bug that plays a gallery at full volume during an
opening. Principles are cheap here; the receiver, the one object I drop before
`dac~`, and the failure mode when I forget it are what I actually live with.

## 2. Problem reframing

Bob's principle is right, and my seat is the one it costs. Moving master and
spatial *out* of bopOS and *into* the patch buys freedom (I get a named 0→1
value and map it to gain, cutoff, grain density, whatever) at the price of
**boilerplate liability**: every patch I ever ship must now perform the same
master multiply, and the wire cannot tell whether I did. There is no
introspection protocol to detect a missing receiver — §14 rejected exactly that,
correctly. So the seam cannot be *enforced* and cannot be *checked*. The only
honest guardrail is to make the correct thing a **single dropped-in object**, so
that forgetting it is conspicuous rather than silent. The seam's real deliverable
is not a wire shape — it's a *starter-kit sink abstraction*.

## 3. Proposed design — the patch-side contract

**What crosses into the engine (three provided surfaces + one enforced one):**

| provided value | wire (proposed, flag for Bob) | encoding | patch obligation |
|---|---|---|---|
| master gain | `/all/os/master <m:0..1>` broadcast | plain float (low precision, no string needed) | multiply into final output |
| spatial proximity | helper→PD localhost `/pt <id> <scalar:0..1>` | plain float | map wherever (upstream of volume) |
| cue | `/cue <cueId>` localhost (already shipped) | string | fire |
| **mute (enforced)** | `/all/os/mute <0\|1>` → amixer below the patch | — | **nothing** |

Master becomes the **sibling of mute** in the `/os` plane — same broadcast,
same full-state idempotent law, same one-datagram-for-the-fleet economy. The
*only* difference is enforcement: mute is applied below patch logic; master is
handed to the patch to enact. This is strictly better than today's dashboard VCA:
one broadcast on a master nudge instead of N unicast `resend_volumes`, and no
"device offline during a master move" hole (the dashboard re-broadcasts
`/all/os/master` on any device-join, cheap and idempotent). Delete
`send_device_param`'s master multiply and `resend_volumes` from `osc_bridge.py`.

**The minimal correct patch** stops looking like a copied multiply and becomes:

```
[r osc-in] → [route p] → [route gain] → [clip 0 1] ─┐
                                                     ├→ [bopos.out~] → (dac~ inside)
              (synthesis) ─────────────────────────┘
```

**The starter kit ships `bopos.out~`** — the one object that makes the seam
safe. It is the patch's final sink, replacing `dac~`. Inside, it:
- has its own `[r bopos-master]` (fed by `bopos.osc.pd` routing `/os/master`),
  smooths it (declick ramp), and multiplies the signal;
- honors the framework mute state as a belt-and-suspenders gain kill;
- optionally republishes its post-master level as `role:"meter"` (`/<id>/p/level`),
  which closes a feedback loop — a facilitator moving master *sees* the meter
  respond, the nearest thing to consumption detection we can get without
  introspection.

So master is **provided-not-enforced on the wire, but effectively guaranteed at
the template**, because the correct sink object does the multiply and the
starter patch already wires it. Freedom is intact (ignore `bopos.out~`, use raw
`dac~`, map master to a filter if you're feeling clever); the boilerplate is
gone (one object, not a per-patch copy).

**Points** get a peer abstraction, `[bopos.point <id>]`, that outputs the 0→1
proximity scalar for one point (internally `[r bopos-point] → [route <id>]`). I
recommend the **routed single-receiver wire** (`/pt <id> <val>`), not
`/pt/<id>`: it scales to arbitrary point counts with no per-point receiver
sprawl, the abstraction hides the routing, and unlistened points cost nothing.
**No manifest declaration of points for v1** — the patch listens by name; add
declaration only if the dashboard later needs to show which points a device
renders. From SC/oF the same three surfaces arrive as ordinary OSC on the engine
port; the equivalent of `bopos.out~` is a ~10-line SynthDef master bus / an
`ofxBopos::Out` mix stage. The abstraction is the contract in every engine.

**Promotion to the facilitator** is a **per-param manifest flag**, not a new
plane: add `"promote": true` to a param declaration. The dashboard renders
promoted params (plus the existing `role:"volume"` card) on `/facilitator`. This
lives with the patch, is diffable, and needs zero wire change. **Position on the
scope guard (Bob arbitrates):** the patch may promote *its own params*; it may
**not** promote admin verbs. Shutdown/reboot/update are framework lifecycle, not
patch business — a patch author has no standing to put "reboot" on a
facilitator's iPad. If an install wants admin on the facilitator, that is an
**installation-level dashboard config**, decided by the technician deploying the
rig, never by the patch repo. Keep the ratified guard; add an install-config
escape hatch outside the manifest.

**Multi-element:** from my seat the patch **does not change**. Element is a
launch-time identity, delivered like `ID`/`PX`/`PY` already are — one added
startup send, `ELEMENT <n>`, plus that element's own position. Each element is
the *same patch* launched N times; helper decomposes points per-element position,
so `bopos.point` just works per instance. The real cost is not the patch — it's
that localhost ports (6661/6662/7770/8880) are device singletons; N engines
collide. That is a launcher/helper multiplexing problem, staged for S2, and it
lands additively because the patch and the `pos2` slots already tolerate it.

**Manifest additions (all optional, additive):** `"promote": true` per param;
nothing else. Points undeclared; master/mute undeclared (framework-provided).

## 4. How it fits the existing system

Kite Choir / The Plants keep working: they already `route gain` and multiply;
they simply *ignore* `/os/master` and `/pt` (unconsumed = no-op, exactly as
today), so master reverts to per-device faders for legacy patches — no flag day.
The **template/starter-kit stitch must add**: `bopos.out~`, `bopos.point`, a
`main.pd` wired through both, the `bopos.osc.pd` routes for `/os/master` and
localhost `/pt` (Bob's edit — I flag spellings, don't write them), the `simfleet`
node-side decomposition + master handling, and a `verify_*.py` asserting
`out == in × master` and `proximity == falloff(distance)`.

## 5. Why it's elegant / right

It confronts the freedom-vs-boilerplate tension head-on and refuses to resolve it
by enforcement. **The abstraction *is* the guardrail.** Provided-not-enforced is
livable precisely because "enact it" collapses to "use the sink object we ship."
A patch that ignores the surface degrades honestly: it plays, unmastered and
unspatialised — the same graceful "unconsumed = silent no-op" the framework
already trusts everywhere. Master and mute end up as twins distinguished by one
axis (enforcement), which is conceptually tidy and kills N-resend traffic.

## 6. Tradeoffs, risks, not-solving

- **You cannot detect a forgotten multiply over the wire.** Accepted; the meter
  echo is the only feedback, and it's optional. Mitigation is cultural: the
  template ships correct, the docs lead with `bopos.out~`.
- SC/oF authors must re-implement the sink; the abstraction is a *convention*,
  not a binary. Unavoidable given engine-agnosticism.
- Not solving: the multi-element port multiplexing (S2), point authoring UI,
  raw-distance exposure, admin-on-facilitator install config (flagged, deferred).

## 7. Smallest first step

Ship `/all/os/master` as a broadcast, delete the dashboard-side master multiply,
and ship `bopos.out~` (master multiply + declick) wired into the `templates/`
`main.pd`. That one slice moves master across the seam, gives every future patch
a drop-in that makes the seam safe, and proves the pattern before points or
promotion land.
