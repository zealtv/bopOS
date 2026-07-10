# Contract amendment draft — the seam ruling (for Bob's review)

Exact edits to `docs/OSC-CONTRACT.md`, drafted from the seam council judgment
as amended by Bob's ratification (2026-07-10). Address/receiver spellings are
**proposals** — mark up anything you'd spell differently and the applier
follows your markup. Everything else is the ratified ruling.

---

## Edit 1 — §1, the ownership paragraph (the seam law)

**Replace** the second paragraph ("The framework owns: …") **with:**

> The framework owns: identity/liveness, the OSC transport and namespace,
> convergence (update/checkout/fetch), the offboard peripheral-bus IO layer,
> the sync/cue plane, and the machinery that produces provided terms (clock
> offset estimation, point-proximity math). Everything that comes out of the
> speakers, LEDs, printer, or monitor is the **patch's**; engine launch is
> **patch-declared**; media IO (MIDI/HID/audio-in) is the **engine's**;
> control-plane state, point geometry and authoring, and scene authoring are
> the **dashboard's**.
>
> **The seam law (ratified 2026-07-10):** bopOS **provides** named,
> full-state *terms* the patch subscribes to and enacts; bopOS **owns** the
> machinery that produces them; bopOS **enforces** exactly one output
> control — mute. **bopOS never composes a provided term into a patch
> parameter.** A patch that doesn't consume a term simply isn't controllable
> by it — unconsumed is a legal no-op, never an error.

*(Delta: "spatial control plane" → "the machinery that produces provided
terms"; the dashboard's "spatial math" → "point geometry and authoring"; the
law added. This is what catches the next spatial-0.)*

## Edit 2 — §3, the planes table `/pt` row

**Replace** the `/pt` row **with:**

> | `/pt` (canonical `/point`) | framework/dashboard | point geometry broadcast — moving sound sources, arbitrary count; each device decomposes locally (§4.1) |

## Edit 3 — §4 transport discipline, the spatial bullet

**Replace** the final bullet ("Spatial at fleet scale is the broadcast `/pt`
… remains fine ≤ ~12 nodes and on the audition rig.") **with:**

> - Spatial is the broadcast `/pt` with **node-side decomposition, at every
>   scale** — never per-device gain streams. (The dashboard-computed
>   `/p/gain` model was built and reverted 2026-07-10: it is O(N) streams on
>   a lossy broadcast channel, and it composed a product into a patch
>   parameter, violating the §1 seam law. See lore
>   `2026-07-10-patch-seam-council`.)

**And add** `/os/master` to the broadcast list in the first bullet
(`/hb`, `/os/assign`, `/all/*` admin, `/cue`, `/pt`, `/os/mute`,
`/os/master`).

## Edit 4 — new §4.1 "Provided terms" (insert after §4's transport bullets)

> ### 4.1 Provided terms
>
> The registry of values bopOS provides for patches to enact. Like the
> shorthand registry (§3), it grows **only by contract revision.** Terms are
> full-state, idempotent, and optional to consume; the starter-kit
> abstractions (PD and SC both first-class) are the reference consumers.
>
> | term | wire | delivery to the engine | patch obligation (if consumed) |
> |---|---|---|---|
> | **master** | `/all/os/master <0..1>` — broadcast on change, 6660; also sent in the per-device catch-up push | direct: the engine's OS layer routes it to a named receive | multiply into the final output stage (the `bopos.out~` twin), upstream of nothing — it is the last gain before mute |
> | **point** | `/pt <n> <id x y r f>×n` — one frame, all points, atomic; ~20–30 Hz while moving; **silence = hold**; sparse per-point form `/pt <id> <x> <y> <r> <f>` and `/pt/clear <id>` for authoring edits; `f` is a falloff enum (0 linear, 1 smooth, 2 gauss) | helper computes proximity 0→1 per point **per element position** and sends flat-args on 6661 (proposed: `/pt <pointId> <element> <v>`) | map wherever it likes (gain, cutoff, …), upstream of its own volume |
>
> - The **catch-up rule**: a device (re)appearing gets the current `/pt`
>   frame and master unicast (piggybacked on the params catch-up) — silence
>   = hold only holds for devices that were present.
> - Point values are **shaped scalars**, not geometry (raw distance may be
>   added later as an option, by revision).
> - `/cue` (§3.1) is a provided term avant la lettre: helper owns the clock
>   math, the engine receives the bare relative fire.

## Edit 5 — §5 assignment: element positions (true N, `pos2` retired)

**Replace** the assign line and its explanation **with:**

> ```
> /all/os/assign <uid> <id> <name> [x y]×N
> ```
>
> Idempotent full-state; **element positions** ride in it, one `x y` pair per
> element, element index = pair order (no separate verb; the old
> `posx posy pos2x pos2y` spelling is retired — it was two unlabelled
> elements). **device** = the computer (one uid, one heartbeat, one engine
> instance); **element** = a positioned output the patch drives. A patch
> renders N elements by cloning internally (PD `[clone]`, SC synth
> instances) and mapping each element to its output channel; helper computes
> per-element point proximity from this list. Usually N is 1 or 2, but a
> many-output computer IDs as many elements as it drives.

## Edit 6 — §6, the mute paragraph (honest boundary + board zoo)

**Append to** the `/os/mute` bullet:

> Honest boundary: mute is independent of the **engine** (amixer acts below
> patch logic), not of **helper** — helper is the actor, and a dead helper
> also stops heartbeating, so the failure is visible, never silent. Where no
> mixer control accepts a mute, the fallback is engine-stop: silencing but
> engine-lethal — a degraded mode, not the design centre. The mixer path must
> be verified per audio board on real hardware (DigiAMP, Pimoroni Audio SHIM,
> class-compliant USB — the candidate-control list in `set_mute` grows as
> boards are benched).

## Edit 7 — §8 manifest: the `facilitator` flag

**Add** after the `role` bullet:

> - **`facilitator` (optional; additive, ratified 2026-07-10):** a param
>   declaration may carry `"facilitator": true` to promote it onto the
>   `/facilitator` surface as a control (rendered beside the volume card;
>   values flow as ordinary `/<sel>/p/<name>`). Promotion of **framework
>   verbs** is *never* a manifest concern: an install-level allowlist in
>   `installation.json` (`"facilitator_commands": […]`, **default empty**)
>   opts specific verbs onto the surface, confirm-gated, with destructive
>   convergence verbs (update/checkout/reboot/shutdown) at minimum
>   hold-to-confirm. The patch promotes its params; the venue promotes its
>   verbs.

## Edit 8 — §13 migration: patches rewrite in lockstep

**Replace** the transition-aliases bullet **with:**

> - Patches are **rewritten in lockstep** with this contract version (ratified
>   2026-07-10: patch-facing wire compatibility is a non-goal — no bare
>   `/gain`-style aliases, no dashboard-side master composition for legacy
>   patches). Fleet-level guarantees stand: `/helper/*` → `/os/*` alias one
>   release, `bopos.devices` seed, samplepacks symlink, zero port changes,
>   `uid == MAC`.

## Edit 9 — §14 additions

**Add** to the rejected-by-design list:

> dashboard-side composition of provided terms into patch parameters (the
> spatial-0 / master-multiply defect — see §1 seam law); a runtime
> parameter-dump/query verb (a patch may implement its own dump; a framework
> `/os/dump` arrives, if ever, as a deliberate revision when evidence
> demands).

---

## Not in the contract (recorded here so it isn't lost)

- The dashboard shows the **mix**, not the patch-enacted product — accepted;
  the optional `bopos.out~` level echo (`role:"meter"`) is the feedback loop.
- `simfleet` consumes every provided term in the same stitch that lands it
  (house rule) — it is the reference *fake* consumer as the starter kits are
  the reference real ones.
