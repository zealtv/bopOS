# Expert response — the framework/patch boundary as an API stance

## 1. Lens & altitude

I hold the framework-boundary seat: what bopOS *owns*, what it *provides*, what
it *enforces*. My test for any design is whether the seam is **statable in one
sentence** and whether every feature falls on the right side of it *without
special pleading*. I zoom to the level of the API stance — one tier above the
wire — because the spatial-0 revert, the master-gain composition, and the
facilitator scope question are the **same defect** wearing three costumes, and
you can only see that from the tier above. But I land every ruling back on
contract sections and specific lines of `osc_bridge.py`/`helper.py`.

## 2. Problem reframing

The recurring bug is not "spatial went to volume." It is: **bopOS shipped a
*product* where it should have shipped a *term*.** `send_device_param`
(`osc_bridge.py:135-144`) multiplies `mix × master` and puts the product on the
wire; the reverted engine multiplied `mix × master × spatial`. In both cases
bopOS reached across the seam and did arithmetic that belongs inside the patch's
signal graph. The patch never sees the factors; it cannot re-map them; a device
offline during the move can only be *recomputed and re-pushed* by the dashboard
(`resend_volumes`, the catch-up loop at `osc_bridge.py:237-241`). That machinery
exists *only because bopOS composed the product*. Remove the composition and the
machinery evaporates. This is why "less coupling" and "less machinery" are the
same request.

## 3. Proposed design — three tiers, one sentence

> **bopOS *provides* named terms the patch enacts, *owns* the machinery that
> produces them, and *enforces* exactly one thing: mute.**

**Tier 1 — Provided (subscribable).** Named OSC values bopOS puts within the
patch's reach. The patch subscribes by receiver name and does the arithmetic
itself. The law: **bopOS never sends a composed product — only atomic terms**,
idempotent and full-state. No subscriber is a legal silent no-op (identical to
today's "no `role:volume` → status-only card," §8). Members: `master`, the
per-param mix values (`/p/*`), point proximity scalars, the relative-time
`/cue` fire.

**Tier 2 — Enforced (safety).** Exactly one member: **mute**. Transport-level,
below patch logic (`helper.py:400-419`), engine-stop fallback. This is the whole
of what bopOS imposes regardless of patch cooperation. §6 stands unchanged and
becomes the *definition* of the enforced tier, not an exception to it.

**Tier 3 — Owned (framework-internal).** Identity, liveness, convergence, the
sync offset math, the IO bus, the asset root, **and the proximity math**. The
patch consumes their *outputs* as Provided values but has no say and no
responsibility in them. Node-local computation (proximity from device position)
is an Owned implementation detail of a Provided value — not a seam crossing.

**Where each thing lands, no special pleading:**

- **Master gain → Provided.** Stop composing. `send_device_param` sends the mix
  *unmultiplied*; the dashboard broadcasts master as its own fleet scalar. Wire
  (spelling flagged for Bob): `/all/os/master <m>` — framework-originated,
  fleet-wide, idempotent, direct-broadcast on 6660 where the patch already
  listens. The patch multiplies master into its own output stage. `master`
  needs no node computation, so it needs **no helper hop** — the patch
  subscribes directly, exactly as it subscribes to `/p/gain` today.
- **Points → Provided, via Owned compute.** Dashboard broadcasts geometry
  (`/pt`, per the S1 draft); helper decomposes to a per-point proximity scalar
  0→1 and delivers it to the engine on localhost 6661. Because points *use
  device position*, the compute is node-local (Owned) but the delivered scalar
  is a plain Provided term the patch maps upstream of its own volume. This is
  the honest reading of §14: *geometry broadcast + node compute* is blessed;
  the rejected thing is *per-device gain products broadcast at fleet scale*.
- **Params → Provided**, unchanged (`/p/*`, §8). They were already terms.
- **Cue → Provided**, unchanged; helper converts absolute→relative (Owned) and
  fires the bare term (§3.1). Already correct.
- **Mute → Enforced.** The one exception, correctly placed.

**The compute-location rule falls out for free:** if a Provided value needs
node-local state (position), helper computes and relays; if it is a pure fleet
constant (master), it broadcasts and the patch subscribes. Same tier, different
plumbing — a mechanical consequence, not a new concept.

**Facilitator promotion — split by owner.** The patch owns its params, so the
*patch* promotes them: a param declaration gains `"facilitator": true` (additive
to §8, sits beside `role`). bopOS commands are *framework* surface, so the
*install* promotes them, not the patch: an `installation.json` allowlist naming
which safe `/os/*` verbs surface on `/facilitator`. Two owners, each declaring
their own side — no special pleading, and it resolves the scope-guard tension
(Q6): the guard was about *human role safety*, so the default allowlist is
empty (guard intact) and Bob opts specific verbs in per install. Flag for Bob's
arbitration; the mechanism is neutral to his call.

**Multi-element — additive, not a mode.** device stays the identity unit (one
uid, one heartbeat, one engine process — the singleton localhost ports at
`start-engine.sh` are not worth breaking). **element = a positioned point of
reception *within* one patch instance.** Assignment already tolerates two
positions (`helper.py:491-519`); generalize to N element positions. helper
computes proximity per point *per element* and delivers `/pt/<pointId>` tagged
by element index; the patch routes element-0→L, element-1→R itself. Belief's
"two positioned patches per Pi" becomes "one patch, two positioned elements" —
which the seed explicitly permits as the same-patch simplification.
Different-patches-per-element needs the multi-instance engine model and is
deferred; it is *not* nearly free. No dashboard mode — just N position handles
per device card.

## 4. Fit with the existing system

**Contract.** Amend **§1** (drop "spatial math… dashboard's" for fleet scale;
add the no-product law) and **§4** (overturn "dashboard-computed `/p/gain` is
the correct first implementation"; node-side `/pt` is primary; add: bopOS ships
terms, never products). **§6 stands** as the enforced tier. **§8 additive**:
`"facilitator"` param flag. **§14 stands** — clarify that node compute ≠ the
rejected per-device-gain-broadcast. New: `/all/os/master` (or Bob's spelling)
registered as a Provided fleet scalar.

**Code.** `osc_bridge.py`: delete the `mix × master` multiply in
`send_device_param`, delete `resend_volumes`, drop the master recompose from the
catch-up push — **net negative lines**. Add a one-line master broadcast on the
master-change ws command. `helper.py`: add the salvaged falloff module +
per-element proximity delivery; generalize `apply_assign` to N positions.
`simfleet`: mirror node-side decomposition (house rule — same stitch).

## 5. Why it's right — the enforcement-vs-freedom tension head-on

If the patch must enact master, every patch must implement a multiply — is that
liability or freedom? **Freedom, made safe by a default.** The framework's
guarantees are *exactly* the Enforced tier, and that tier is *exactly one
member*: silence on demand. Everything else is opt-in capability that degrades
honestly — a patch ignoring master simply isn't master-controllable, the same
already-ratified degradation as "no volume param → status-only card." The
`templates/` reference patch ships the master/volume/mute wiring so the common
case is free. This is precisely the web platform (browser enforces the security
sandbox; pages opt into everything else) and VST (host enforces automation
delivery; a plugin ignoring a param just doesn't respond). The boundary is
statable in one sentence, and — the real prize — it is *smaller* than today's:
bopOS stops owning the mix arithmetic, so an entire class of resync machinery
disappears.

## 6. Tradeoffs, risks, non-goals

- **Cost:** master control now depends on a PD receiver Bob must add; until it
  lands, master is inert on un-updated patches. Mitigated by direct broadcast
  (no new hop) and the template.
- **Risk:** the facilitator card shows the mix, not the enacted value — already
  a known §Q2 wart, now more visible since bopOS no longer knows the product.
  Acceptable; flag if a "sent value" readout is wanted.
- **Not solving:** different-patches-per-element (needs multi-instance engine),
  point authoring UI, sequencer integration, raw-distance exposure. All
  deferred, all additive on this seam.

## 7. Smallest first step

**Ship master gain as a Provided term.** One slice, the type case, zero node
compute, zero new PD design beyond a receiver Bob adds later: (1) stop composing
in `send_device_param`; send the mix raw. (2) Broadcast `/all/os/master <m>` on
master change. (3) Delete `resend_volumes` and the master recompose. Migration
is clean — the raw volume param is exactly what a pre-master patch already
expects, so there is no flag day and no port change; a patch *gains* master the
day its receiver lands. This one move proves the entire seam and removes code.
