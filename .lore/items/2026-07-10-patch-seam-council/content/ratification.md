# Ratification — Bob's rulings on the seam judgment (2026-07-10)

Bob's feedback on `judgment.md`, recorded as rulings. Where this file and the
judgment differ, **this file wins**. Open items at the bottom.

## R1 — Backwards compatibility is disregarded

All existing patches will be rewritten for this version of bopOS. "We're
essentially building something from scratch here." Consequences:

- **Master ships unconditionally.** `/all/os/master` broadcast; the dashboard
  **never** composes `mix × master`; delete `send_device_param`'s multiply and
  `resend_volumes` outright. The judgment's crux-B ruling (the `subscribes`
  manifest gate) is **overruled as unnecessary caution** — there is no
  dual-path release, no VCA fallback. A patch that doesn't consume master
  isn't master-controllable; that's the honest degradation, full stop.
- **The `subscribes` manifest field is dropped** from the §8 amendment (its
  purpose was the gate). If dashboard UI later wants to show which devices
  render points, that's a future additive field, on evidence.
- §13's patch-facing transition aliases are moot (consistent with Bob's
  2026-07-07 relaxation: patches update in lockstep with bopOS). Fleet-level
  guarantees (no port changes, uid==MAC) still stand.

## R2 — Multi-element: single instance, internal cloning; true N

- **One patch instance per device.** Inside it, the patch does "any cloning or
  duplicating required to generate multiple elements" (PD `[clone]`; SC synth
  instances), assigns each element to the correct output channel, and reads
  that element's position/point values. This adopts the framework-boundary
  seat's model and **dissolves the S2 process-model problem** (no N pidfiles,
  no localhost port collisions) for the ruled case. Different-patches-per-
  element stays deferred.
- **Scale is real N, not 2:** usually one or two elements, but a computer with
  many outputs must drive them all by ID-ing many elements. Assignment
  generalises to a genuine position list (proposal: `/all/os/assign <uid>
  <id> <name> [x y]×N`, element index = pair order).
- **Tidy the `pos2` naming** — it's a Belief-era remnant; reconsider the label
  as part of the contract-amendment stitch (terminology: element positions,
  indexed, not pos1/pos2).

## R3 — SuperCollider is first-class in the starter kit

The starter kit ships **both** PD and SC templates: `bopos.out~` /
`bopos.point` and their SC equivalents (master-bus mix stage, point-scalar
responder). Only `.pd` is Bob-gated; **agents build the SC side.**

## R4 — PD edits get a visible waiting room

Done in-session: top-level loom stitch **`pd-edits-for-bob.waiting`**, live
list at **`.notes/pd-edits-for-bob.md`** (consolidates the tied
osc-schema-contract list, the clock-sync `/cue` receiver, and the seam wave:
`/os/master` pass-through, point-scalar delivery, `bopos.out~`,
`bopos.point`). Agents append there as stitches hit new edits.

## R5 — Judgment §7 items

1. **Delivery channel:** provided terms ride the 6660 broadcast; each engine's
   boilerplate handles reception (bopos.osc.pd for PD; the SC template for
   SC). Bob is open to a tidier engine-universal routing in `bopos.osc.pd` if
   it's performance-neutral — worth proposing, not critical.
2. **Receiver shape: routed single receiver, ratified.** Flat-arg messages
   (`/pt <id> … <v>`) over nested addresses — Bob has measured flat args as
   slightly more efficient than nested-address sprays. Applies to the
   localhost delivery and supports frame-form B on the LAN.
3. **Mix-vs-enacted readout: accepted as-is.** Future idea recorded, not
   opened: a **dump/query verb** (query a param, or a device's whole current
   state — Bob used a `dump` command in the old BOP framework). Deferred as a
   patch responsibility for now; note it would need a contract revision (§14
   currently rejects runtime parameter introspection), so it must arrive as a
   deliberate amendment when evidence demands.
4. **Mute hardware:** "bench-gated" explained (see session notes): the amixer
   mute path depends on the sound device exposing an ALSA mute-capable mixer
   control, which can't be verified from the repo — only on real hardware.
   **New requirement recorded:** mute must work across the board zoo —
   DigiAMP, Pimoroni Audio SHIM, class-compliant USB cards — so `set_mute`'s
   control discovery gets verified per-board on a rig, and boards without a
   usable control fall to the engine-stop path knowingly.
5. **Two master code paths:** moot under R1 — single path from day one.

## R6 — Admin verbs on the facilitator (ruled in follow-up, same day)

**Install-level allowlist ratified** (judgment §5e as ruled): promotion of
framework verbs lives in `installation.json` (`facilitator_commands`),
**default empty** — the ratified no-admin-verbs scope guard holds until an
install opts in — confirm-gated, destructive convergence verbs
(update/checkout/reboot/shutdown) hold-to-confirm at minimum. Never
patch-manifest-promoted.

## Disposition

Ratification complete. Implementation staged for autopilot behind the
`seam-1-contract-amendment` gate (Bob reviews the amendment draft text there;
usage limits ended this session before implementation by design).
