# Judgment — the bopOS↔patch responsibility seam

Judge: fable, inline, 2026-07-10. Five expert designs read in full; load-bearing
claims re-verified against the repo. This is a proposal for Bob's ratification,
not a ratified design.

## 1. The decision, up front

The seam is ruled as one sentence, adopted into the contract: **bopOS provides
named, full-state *terms* the patch subscribes to and enacts; bopOS *owns* the
machinery that produces them; bopOS *enforces* exactly one thing — mute. bopOS
never composes a provided term into a patch parameter.** Under that law: master
gain becomes a broadcast term (`/all/os/master`, spelling Bob's) with the
dashboard-side `mix × master` composition retired **per patch, gated by a
declared manifest fact** (`subscribes`) so no rig ever has a flag day; points
proceed exactly as the S1 draft with encoding B, enum falloff, and a
reappearance catch-up frame; facilitator promotion splits by owner — the patch
promotes *its own params* in the manifest, admin verbs are *never* patch
business and surface only via an install-level, default-empty, confirm-gated
allowlist that Bob arbitrates against the ratified scope guard; multi-element
is ruled as a *model* (element = a positioned reception point; assignment
generalises to a position list; the latent `pos2` is retconned as element 1)
but **nothing is built now** beyond keeping the proximity loop
position-general — the process-model work is S2, bench-gated. The redesign is
**small**: three contract edits plus one new paragraph, two additive manifest
fields, and code that is net-negative on the dashboard side.

## 2. The real crux

Two decisions carry everything:

**Crux A — where composition lives.** Every incident in evidence — spatial-0
and the master multiply — is the same defect: bopOS shipped a *product*
(`mix × master`, `mix × master × spatial`) where it should have shipped
*terms*. The framework-boundary and simplicity seats arrived at the identical
sentence independently, which is the strongest convergence signal in the
session. This is the anti-spatial-0 guardrail, mechanically checkable: *if
bopOS is multiplying a value into a patch param, the seam is drawn wrong.*

**Crux B — how a responsibility relocates across a fleet you can't reflash.**
Moving the multiply is trivial; moving it *safely* is the design. The council
split three ways: move now (boundary, patch-author), gate per patch (protocol,
ops), defer entirely (simplicity). Ruled: **gate per patch by declared fact.**
This is the contract's own deepest idiom — §14: "differences are declared
facts, never special cases" — and it makes the migration a per-patch
convergence, not an event.

## 3. Council map

- **Framework-boundary** — the three-tier law (provide/own/enforce) and the
  no-composed-product sentence; the observation that deleting composition
  deletes machinery (`resend_volumes` exists *only because* bopOS composes).
  Best single contribution: the crux-A sentence.
- **Protocol** — the wire: master as `/os` plane sibling of mute differing only
  on the enforcement axis; `subscribes` as the gate; per-frame `/pt` encoding
  with enum falloff; promotion as manifest metadata. Best contribution: making
  the philosophy *spellable* with a small amendment diff.
- **Patch-author** — the guardrail is an abstraction, not the wire: `bopos.out~`
  (master multiply + declick + mute-honor + optional level meter) as the
  starter-kit sink, `[bopos.point <id>]` as the point receiver. Best
  contribution: resolving freedom-vs-boilerplate without enforcement.
- **Ops** — the migration gate; the reappearance catch-up hole in
  "silence = hold"; the honest mute boundary (engine-independent,
  helper-dependent, engine-lethal fallback); the bandwidth arithmetic
  (O(1) vs O(N)); multi-element's real blockers (pidfile/port singletons, RAM,
  xruns — not CPU). Best contribution: crux-B and the catch-up.
- **Simplicity** — the honest size ("a dozen misplaced lines, not an
  architecture"); the principle is already ratified in §3/§6, so amend the two
  places code and text violate it rather than re-ratifying; hold the admin-verb
  guard; build nothing for multi-element. Best contribution: keeping the diff
  small enough to hold in one head. Its master *deferral* is overruled (below)
  but its "one PD-edit event, not two" packaging is adopted.

## 4. Adjudication of load-bearing facts

1. **"Master composition is ~a dozen lines"** — holds. `osc_bridge.py:135-153`
   (`send_device_param` multiply + `resend_volumes`) plus the catch-up re-push
   at 237-241. Verified.
2. **"Moving master breaks every deployed Kite Choir patch"** (ops) — **does
   not hold as stated.** The dashboard goal stitch is `.waiting` on Bob
   adopting it on a real rig (CLAUDE.md:37; loom `dashboard.waiting`), so *no
   deployed installation runs the VCA master today*. The claim is really about
   the expected adoption path (Bob trials the dashboard on un-edited Kite Choir
   patches, where VCA master would just work). The gate is still the right
   shape — but as a declared-fact idiom, not an emergency brake.
3. **"The principle is already the ratified contract"** (simplicity) —
   **partially holds.** §3 (`/p/*` is "the only place output semantics live")
   and §6 (mute the one framework output control) say it; but §1 explicitly
   grants the dashboard "spatial math" and §4 blesses dashboard-computed
   `/p/gain` as "the correct first implementation." The contract is internally
   split; the amendment is genuinely needed, not re-litigation.
4. **"`pos2` already rides the wire and is persisted"** — holds
   (`helper.py:491-519` parses and stores up to 4 floats). Element identity is
   latent, free to preserve.
5. **"Localhost ports and pidfile are singletons that collide under N
   engines"** — holds (`start-engine.sh:99` one pid; §4's 6661/6662/7770/8880
   one-per-device). The multi-element cost is node-launch, not dashboard.
6. **"helper ignores unknown `/os/*` members on 6660"** — holds
   (`handle_lan_datagram` matches known verbs, falls through otherwise), so a
   new provided term breaks nothing node-side.
7. **"Mute is engine-independent"** — holds with ops' honest caveat: helper is
   the actor (helper dead ⇒ no mute, but also no heartbeat, so the failure is
   visible), and the no-mixer fallback is engine-lethal. DigiAMP's
   mute-capable control **needs bench verification**.
8. **Bandwidth arithmetic** — holds. Frame-form `/pt` at 5 points/30 Hz is
   ~3–4 KB/s broadcast, O(1) in fleet size; the reverted model was O(N) streams
   on an ACK-less basic-rate channel. Settles node-side as primary, confirming
   the 2026-07-10 agreement.

## 5. The ruling, in detail

**(a) Contract amendment** (one stitch, ratify-gated):
- **§1**: strike the dashboard's claim to "spatial math"; the framework/
  dashboard provides spatial *geometry*, the node computes proximity (owned),
  the patch maps it (its own). Add the seam sentence: *bopOS provides terms,
  owns the machinery that produces them, enforces only mute, and never
  composes a provided term into a patch parameter.*
- **§4**: strike "dashboard-computed `/p/gain` is the correct first
  implementation"; node-side `/pt` decomposition is **primary** at any scale.
- **§8**: add `subscribes: [...]` (top-level, optional; names framework
  surfaces the patch enacts itself — `"master"`, `"point"`) and a per-param
  `facilitator` flag (boolean or `{label, order}` — protocol's richer form only
  if the UI needs it; start boolean).
- **New short section (Provided terms)**: registry of provided values —
  `master`, `point` — extended only by contract revision, exactly like the
  shorthand registry. §6/§14 stand unchanged; add ops' honest-mute note to §6.

**(b) Master.** `/all/os/master <0..1>` broadcast on 6660, idempotent
full-state, sent on change and in the per-device catch-up push. If a manifest
declares `subscribes:["master"]`, the dashboard sends the volume param **raw**
and never composes; otherwise today's VCA composition continues verbatim.
Exclusive gate — never both (double-multiply is the failure mode). The
simplicity seat's deferral is **overruled** because the seed explicitly asks
for provided master and the type case is what proves the seam — but its
packaging is adopted: the patch-side receiver lands in the *same* PD-edit
event as the point receivers (one edit wave, `bopos.out~` carries both).

**(c) Points.** S1 draft confirmed with the protocol seat's settlements:
frame-form B (`/pt <n> <id0> <x0> <y0> <r0> <f0> …`, atomic, MTU-bounded) as
the moving wire; sparse per-point form + `/pt/clear <id>` for authoring edits;
falloff as enum int (0=linear, 1=smooth, 2=gauss — the salvaged curves);
~20–30 Hz while moving, silence when still, **plus ops' catch-up**: one frame
(and the current master) unicast to a device on (re)appearance, piggybacking
the existing params catch-up. helper computes proximity per point *per
assigned position* and delivers a named scalar to the engine; `simfleet`
decomposes identically in the same stitch. No per-point manifest declaration
in v1 (`subscribes:["point"]` is patch-granularity and enough).

**(d) The starter kit is the guardrail.** `templates/` ships `bopos.out~`
(master multiply, declick, mute-honor, optional `role:"meter"` level echo) and
`[bopos.point <id>]`, with SC/oF equivalents documented as conventions. The
`.pd` internals are Bob's co-design; agents scaffold the manifest, README, and
verify. A patch that ignores the surface degrades honestly (plays unmastered,
unspatialised) — the same "unconsumed = no-op" the framework already trusts.

**(e) Facilitator promotion — split by owner.** Patch params: the manifest
`facilitator` flag; the dashboard renders promoted params on `/facilitator`
alongside the volume card. Admin verbs: **not patch business** (a patch repo
has no standing to put reboot on an iPad; the same patch plays different
venues). If wanted, an install-level allowlist (`installation.json`), default
empty so the ratified scope guard holds until Bob opts in, confirm-gated,
with ops' reversibility line: destructive convergence verbs
(update/checkout/reboot/shutdown) stay off or behind hold-to-confirm. The
protocol seat's manifest `facilitator.commands` is **rejected** (promotion
authority belongs to the venue, not the repo). **Bob arbitrates** this whole
item — it amends his own ratified guard.

**(f) Multi-element.** Ruled as a model, not a build: **device** = the
computer (one uid, one heartbeat, one helper); **element** = a positioned
reception point; `/all/os/assign` generalises to a position list (pos2
retconned as element 1); helper's proximity loop iterates positions (a
for-loop, not machinery). Everything else — N engine instances vs one instance
with N elements, port offsets, per-element liveness, `<id>.<el>` addressing —
is **S2, bench-gated**, opened only on un-defer evidence (a booked
split-channel install). It is explicitly **not a dashboard mode**; a
multi-position device is just a card with N handles when it arrives.

## 6. Explicitly rejected

- **Unconditional master move** (boundary/patch-author): right destination,
  no migration story for the expected adoption path. Cost: none — the gate
  converges to the same end state.
- **Master deferral** (simplicity): overruled by the seed's explicit ask and
  by the one-edit-wave packaging that makes it nearly free.
- **Manifest-promoted admin verbs** (protocol): promotion authority for
  framework verbs belongs to the install, not the patch repo.
- **Elements inside one patch instance as the ruled model** (boundary): kept
  *available* (it's the cheap stereo path) but not ruled — it forecloses
  different-patches-per-element, which stays open at zero cost by deferring.
- **Any new dashboard/bopOS "mode"**, second config surface, or per-point
  manifest declaration in v1.

## 7. Risks and open questions the build must confront

1. **Delivery channel for provided terms into the engine**: PD hears 6660
   directly (`bopos.osc.pd` routing is Bob's); non-PD engines may need helper
   relay on the established localhost path (the `/cue` pattern). Council lean:
   whatever channel the engine already gets `/p/*` on; mechanics flagged for
   Bob at ratification.
2. **PD receiver spellings** (`/pt <id> <v>` routed single receiver vs
   `/pt/<id>`; the master receiver name) — Bob's co-design; council lean is the
   routed single receiver hidden inside the abstractions.
3. **Facilitator shows the mix, not the enacted value** once master moves
   patch-side — accepted wart; the `bopos.out~` meter echo is the only
   feedback loop available without §14-rejected introspection.
4. **Bench-gated**: DigiAMP mute control; everything multi-element.
5. **Two master code paths** (VCA vs subscribed) live until the fleet
   converges; deleting the VCA path is a later judgment call.

## 8. Recommended first slice

**Slice 1 (one stitch): the contract amendment** — §1/§4/§8 + the Provided
terms section, ratified by Bob. Nothing implements past it.
**Slice 2: S1 implementation** — node-side `/pt` in `helper.py` + `simfleet`
(salvaged falloffs, catch-up frame), browser-free `verify_*.py`. **Slice 3:
master** — `/all/os/master` + the `subscribes` gate in `osc_bridge.py`
(net-negative diff), simfleet accepts it, one example manifest.
**Slice 4: facilitator param promotion** (render addition + flag). **In
parallel, Bob-paced:** the `templates/` PD edits (`bopos.out~`,
`bopos.point`, `bopos.osc.pd` routes) in one edit wave. Then re-scope the
`spatial-audio` thread (spatial-1 → author/move points; spatial-2 unchanged;
`spatial-0b-redesign-review` closes into this ruling) and record S2's
un-defer evidence in the loom.
