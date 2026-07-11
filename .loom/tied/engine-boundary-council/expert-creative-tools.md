# Engine boundary — the creative-tools & composition-UX lens

## 1. Lens & altitude

I judge this boundary by one question: does it make composing and debugging an
installation feel *less mysterious*? The wire names are the words Bob types while
patching; the dashboard surfaces are the composer's feedback loop. I take a
**mid altitude** — I rule concretely on meters, the diagnostic facility, and the
bus glossary (my domain), and I stay light on command-ingress/port-topology
(adjacent seats own those), touching them only where they leak into the patch
author's mental model.

## 2. Problem reframing

The "meter" debate is a category error. Three things wear the word: (a) *measured
audio telemetry* — "is signal actually coming out of box 3"; (b) *sensor
inspection* — "what does the touch strip read right now"; (c) *patch-authored
synthetic feedback* — an LFO phase, a step index, a number the composer wants to
watch. They have been conflated into two always-on streams (`level → /rpt`
broadcast, and helper's `rssi/cpu_temp → /<id>/p/<name>`), both of which are
low-value chatter that §14 already frowns on, and one of which (the `/rpt`
broadcast) is *broken on macOS* (errno-49).

The real creative need underneath all three is identical and Bob already named
it: **report on request**. You look at a value when you want to look. Nothing
should run forever. So I collapse the whole meter concept into one demand-driven
diagnostic, and I delete the streaming meter outright — which Bob explicitly
blessed as a valid solve.

## 3. Proposed design

### The meter ruling: delete the stream, keep the *probeable value*

There is **no streaming meter and no separate "meter" wire type.** `role:"meter"`
survives in the manifest (§8) but is **redefined**: it no longer means "the patch
republishes this outward continuously." It means "this named value is
*probeable* — bopOS may ask for it and render it read-only." Lifecycle: **off by
default, demand-driven, never streamed.** Scope: named — a framework source
(`rssi`, `cpu_temp`, `level`), a `/p/*`-declared patch value, or an io channel.
`helper.meter_loop` is **deleted**.

### The diagnostic facility: `/os/probe` — one clean verb replaces all cruft

```
/<id>/os/probe <what> [lease-s]      dash → node   (unicast)
/os/probe <id> <what> <values…>      node → dash   (unicast reply)
```

- **One-shot by default.** `/<id>/os/probe level` → one unicast reply with the
  current value. This is how a facilitator asks "is box 3 making sound" mid-show
  without waking the fleet — it obeys §4's unicast-reply discipline exactly like
  `/os/report`.
- **Leased streaming for the case that genuinely needs motion.** `<lease-s>`
  opens a bounded window: `/<id>/os/probe io:touch 8` streams the 12-channel
  touch strip at ~10 Hz for **eight seconds, then auto-stops.** The lease is the
  whole insight: *debugging streams are leased, never permanent.* Helper owns the
  timer, so if the dashboard dies mid-lease the stream still expires — no orphan
  chatter, no `/rpt` that broadcasts forever.
- **Rate/bandwidth:** one-shot is free; a lease is ≤10 Hz, unicast to the single
  asker, O(1) in fleet size, and time-bounded. This is *inspection, not
  telemetry* — it is not automatic, not fleet-wide, and not an alarm surface
  (heartbeat absence stays the alarm, §14 intact).
- **Deleted for good:** the `/rpt` echo path, `route echo`, the `osc-out →
  oscformat rpt → broadcast 5550` chain, and the `PX`/`PY` dev prints. Because
  probe replies are **unicast**, the macOS errno-49 broadcast bug is *dissolved,
  not fixed* — the failing send simply no longer exists.

### The touch-sensor case, concretely

Today: `io/main.py` (10 Hz) → PD 6662 → PD echoes to `osc-out` → `/rpt`
broadcast → PD dashboard. Circuitous, always-on, routes a *sensor* through the
*audio engine* for no reason.

New: the diagnostic path **skips the patch entirely.** `io/main.py` already holds
the values. `/<id>/os/probe io:touch 8` leases a forward from io → helper →
unicast to the laptop, rendered as a live 12-bar strip in the tech dashboard for
eight seconds. The engine is never in the debug loop. The patch sees touch data
*only if the composition consumes it* — in which case it is already `/p/*`
outbound (§11), a musical choice, not a debug artifact. **Debug inspection and
musical consumption are finally separated**, which is exactly the mystery Bob
wants gone.

### Notification (bopos-notify)

Notifications are a **small closed vocabulary of framework audible confirmations**
— `identify`, and provisioning-verb acks — not a patch concern. Keep the single
notify bus and its tone in the `bopos.out~` sink (post-master, pre-mute is
correct: you must hear identify at low master, but mute still kills it). Trigger
is `/os/identify` / `/os/notify <event>` on the local engine surface.
**Retire `bopos.feedback.pd` entirely** — its read-a-sequence-file machinery
(aloha/reboot/click) is superseded cruft.

### The bus / term glossary — the artist-facing vocabulary

Reserve the **`bopos.` prefix (dot, matching `bopos.out~`)** for framework-owned
buses. The name states *what it carries*, from the patch author's seat — never
raw transport direction. Same nouns across PD and SC (different syntax, identical
words), so a composer carries one vocabulary between engines.

| bopos bus (PD `[r …]` / SC key) | carries | replaces |
|---|---|---|
| `bopos.master` | master term 0..1 | `route os / route master` on osc-in |
| `bopos.point` | point scalar, keyed `[id, element]` | `bopos-points` |
| `bopos.cue` | named relative fire | `bopos-cue` |
| `bopos.p.<name>` | patch param in | `/p/*` on osc-in |
| `bopos.notify` | framework audible event | `bopos-notify` |
| `bopos.run` | id + seed + active-patch + run-id (**no absolute time**, §12) | `ID`/`RANDOM`/`STARTDATE`/`STARTTIME`/`ACTIVEPATCH` |
| `bopos.io` | sensor values in from io | `from-bopos-io` |
| `bopos.io.out` | peripheral control out | `to-bopos-io` |
| `bopos.probe` | patch answers a probe out | `osc-out` / `/rpt` |

**Killed:** `osc-in`, `osc-out`, `PX`, `PY`. The patch stops seeing raw OSC — it
sees named, typed buses, so the bus names *are* the contract's nouns. Drop a
`[r bopos.master]` and you have master; no decoding `route os`. (`helper.py` →
`bopos.py` is a good rename now that it owns admin ingress + probe, but it is
lower priority than the glossary and only worth it with the role clarified.)

## 4. How it fits the existing system

- **Dashboard:** the existing meters surface becomes a **probe readout** (one-shot
  values + leased live strips). Facilitator view is **unchanged** — status dot,
  volume card, `engine-alive` bit; a one-shot `probe level` is the only addition,
  behind a tap. `role:"volume"`/`facilitator` promotion untouched.
- **Contract revisions needed:** §11 — meters move from streamed republish to
  demand-driven probe; §6 — add `/os/probe` to the debug family; §8 —
  `role:"meter"` redefined as "probeable," not "republished"; §14 — record the
  leased probe as *bounded interactive inspection*, explicitly not the rejected
  telemetry stream (leased, unicast, user-initiated, never an alarm).
- **Stays:** heartbeat as the alarm, `/os/report` for static facts, mute below
  patch, the seam law, `/pt`/master/cue delivery.

## 5. Why it's elegant / right

- **Install week:** installer taps "watch touch 10s," 12 bars wiggle live, then
  stop themselves. No patch, no permanent broadcast, no `/rpt` mystery.
- **Desk + audition rig:** the composer drops `[bopos.master]`, `[bopos.point]`,
  `[bopos.cue]`; the SC twin uses the same nouns. The patch reads like the
  contract.
- **Quiet device mid-show:** `engine-alive` already says "engine up"; a one-shot
  `probe level` answers "is signal flowing" without waking 100 CPUs.

Against Bob's taste: **simple** (one verb replaces echo + rpt + prints + meters);
**clean** (patch buses are purely creative, admin/diagnostic live elsewhere);
**understandable** (bus names = contract nouns); **performant** (leased, unicast,
O(1), nothing runs forever).

## 6. Tradeoffs, risks, not-solving

- No always-on VU. If Bob later wants a persistent stage meter for a specific
  show, that is a deliberate future revision — I bet on his own ruling that he
  won't miss it.
- Synthetic patch feedback (case c) is folded into probeable named values, not a
  new stream type. A composer who truly wants a live synthetic readout uses a
  lease. Accepted.
- **Not solving:** command-ingress ownership depth, port topology, the macOS
  broadcast fix (my design *dissolves* it by deleting the broadcast). The lease
  timer must live in helper, not the dashboard — called out above.

## 7. Smallest first step

Add `/os/probe <what> [lease]` to `helper.py` as a **one-shot unicast responder**
for the sources it already reads (`rssi`, `cpu_temp`) plus an `io:<name>`
passthrough, rendered in the tech dashboard's existing meters surface as a
readout; leave `meter_loop` disabled (its default already-off) pending deletion.
Fully additive, reversible, **touches no `.pd` files**, and proves the
demand-driven model before any bus rename or PD edit wave. The glossary rename is
a separate Bob-paced PD edit.
