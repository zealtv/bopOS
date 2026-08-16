# 62-split-elements

A device can be set to **split** its elements: it runs one engine instance per
element instead of one instance rendering N elements by cloning. Split
elements take Seats and are targeted like any other Seat. bopOS owns the
split; it is configured in the Device tab.

Raised by Bob 2026-08-16 as horizon work: *"being able to set a device to be
'split' elements … how split elements are given seats — they should be
targeted like usual. how do the i2c devices get specified and assigned. this
is looking like it should be bopos-side, and configured in the device tab. my
initial thoughts are that i2c modules are declared in the manifest, and any
element instance can choose to hook into them or control them."*

**This whole thread is a design gate.** It ends in a Bob-ratified proposal and
nothing implements past it. It is `.waiting` on queue order, not on a missing
answer — `57`, `58` and `59` hold the queue.

## This thread is the tip of something larger

Bob, 2026-08-16, on reading the sweep: *"i think the split elements is
pointing to a larger refactor that clarifies and streamlines the bopOS
architecture … as a marker of where we are heading, i think a refactor is on
the horizon"* — and, in the same breath, *"engine agnosticism should be
brought into this as well, we are going to want both pd and super collider as
working engines."*

The marker is `.notes/horizon-architecture-refactor.md`. Read it before
working `1-split-identity-model`. The short version: split and engine
agnosticism break on the same seam — the framework assumes a device has
exactly one engine, and that the engine is probably Pure Data — and
`bash/start-engine.sh` is the hinge for both, since its PD arm is the one that
cannot currently be told a port. So the rulings in this thread should be
phrased so they do not have to be reopened when the second engine arrives:
say **engine instance**, not "the Pd", and do not push per-instance identity
through a mechanism only `bopos-context` can carry.

That is a constraint on how this design is written, **not** a widening of its
scope. Do not design the refactor here.

## Why this is not a small change

Today's model is stated as a definition in contract §5: *"**device** = the
computer (one uid, one heartbeat, one engine instance); **element** = a
positioned output the patch drives. A patch renders N elements by cloning
internally (PD `[clone]`, SC synth instances) and mapping each element to its
output channel."* Split moves the routable unit from the **device** to the
**engine instance**. Every 1:1 assumption below follows from that one line.

## Starting state — measured 2026-08-16, not assumed

**Identity is 1:1 end to end.**

- `/all/os/assign <uid> <id> <name> [x y]×N` carries **one** id and N element
  positions (`python/bopos.py:779`). `NodeState.id` is a single int;
  `resolve_id` returns one (`:187`); `resolve_elements` returns the position
  list under it (`:212`).
- `selector_matches(selector, device_id, memberships)` (`:494`) matches one id
  and one group set per node. Groups are node-scope and persisted under the
  node's single assigned Seat (§5).
- The heartbeat is `/hb <uid> <id> <version> <engine_alive> [rssi]`
  (`build_heartbeat`, `:354`) — one id per device.
- Dashboard-side the inverse is enforced: `seat["bound"] = uid`, the
  `bopos.devices` seed rejects a uid already bound
  (`dashboard/state.py:271`), `clean_seats` dedupes bound uids (`:621-631`),
  and binding a uid that is already bound **displaces** the other seat
  (`dashboard/server.py:1126-1139`). `seat_for_uid` returns the first match
  (`state.py:785`).
- Point proximity is already per element — bopos.py computes it and sends
  `/pt <pointId> <element> <v>` with a 0-based element index taken from pair
  order in the assignment (`apply_points`, `:873`). Under split, "which
  element am I" moves from an index inside one engine to an identity of the
  instance itself.

**Ports are singletons — but the precedent for N is already built.**

- `docs/PORTS.md`: 6661 bopos→engine, 6662 io→engine, 7770 engine→bopos, 8880
  engine→io. Two instances collide on 6661 and 6662 at once.
- `bopos.py` binds `OSCServer(('', 7770))` and holds **one** client connected
  to `127.0.0.1:6661` behind `engine_client_lock` (`:55-58`); every
  `send_to_engine` in the file goes down it.
- `tools/audition.py` already runs N engines on one machine with
  `--engine-port-base 16661` and a per-node `BOPOS_ENGINE_PORT`
  (`:143`, `:178`, `:265`, `:325`, `:949`), and `bash/start-engine.sh` already
  honours `BOPOS_ENGINE_PORT` for non-PD engines. A split device is
  structurally audition-on-a-Pi; that is the model to lean on rather than
  invent.

**Audio routing is implicit, and two instances would silently sum.**

- Nothing in the repo calls `jack_connect` (grep: zero hits outside test
  names). `pd -nogui -jack` auto-connects to `system:playback_1/2`.
- Today the patch itself maps element → output channel. Split takes that
  responsibility away from the patch and gives it to nobody. Per-instance
  channel assignment is the one piece of this design with **no existing
  mechanism at all**.

**Node-scope services that two instances would share.**

- The persistence store (`store`/`load` on 7770, flat key namespace,
  `python/store.py`).
- Mute and `enabled`: `enforce_mute`/`set_device_enabled` (`:571`, `:604`) act
  on ALSA controls device-wide.
- `/os/report`, patch distribution, the patch fingerprint, framework version,
  hostname, LED identify — all one per uid.
- `deliver_engine_context` (`:741`) redelivers id, groups and static params to
  *the* engine as idempotent full state; under split it must redeliver
  per-instance state to the right instance.

**The io bridge is the sharpest edge — and it is already an open design gate.**

- `python/io/main.py` is one process listening on 8880 and constructing
  exactly **one** OSC client, hardcoded to `127.0.0.1:6662` (`:40-41`) — the
  engine. Everything it knows goes to Pure Data and nowhere else.
- Peripherals are created **dynamically from the patch** (`create adc1
  ads1015 0x48` into `[s to-bopos-io]`, re-run on every engine restart via
  `loadbang`). Two instances means two creators racing on one registry, one
  reply route serving two consumers, and contended writes to a shared
  peripheral.
- **`59-i2c-inventory/0a-io-design-review` already owns this**, and it is at
  the head of the queue. Its question 2 is *"Ownership. Who owns a peripheral
  — the patch or the operator?"* Split adds a third axis to that same
  question: *which instance*. Bob ruled 2026-08-16 that the manifest-declared
  peripheral idea belongs to `0a`, not here — see "Relationship to 0a" below.

**One argument in favour that is easy to miss.** `pi-zero-performance/
measurements-2026-08-13-finn-jet.md` measured Pd at **51%** of a core on
`demo-pd` and **99%** on `bonks-pd`, with the JACK client thread idle and
three of four cores unable to help, because Pd's audio path is
single-threaded. Split is the only shape currently on the table that uses
those cores. It is a performance answer as well as an addressing one, and that
should be said in the proposal rather than rediscovered later.

## Relationship to `0a-io-design-review`

**Bob's ruling, 2026-08-16: the i2c half of this idea goes into `0a`, not into
a stitch here.** `0a` is already deciding peripheral ownership and transport
for the whole io layer, it is already queued ahead of everything, and two
design gates answering the same ownership question in different sessions is
exactly how this layer got muddy the first time.

So this thread carries the split-specific *constraint* and `0a` carries the
*ruling*. A note to that effect has been appended to `0a`'s instructions:
peripheral ownership must be expressed in terms that survive N engine
instances on one device, and Bob's manifest-declaration idea (i2c modules
declared in the manifest, instances hooking into or controlling them, bound in
the Device tab) is an input to `0a`'s question 2.

`0a` is not a `needs/` edge of this thread. It answers first because it is
queued first; if it ships before this design is worked, `3-dashboard-model`
inherits its ruling rather than reopening it.

## Children

1. `1-split-identity-model` — the gate the rest hang off: is the routable unit
   the instance, and how does one device carry N Seats.
2. `2-instance-runtime` — ports, launch, supervision, JACK channels, and what
   stays node-scope.
3. `3-dashboard-model` — device ↔ N seats in the dashboard, the Device tab
   split configuration, Control targeting, simfleet parity.
4. `4-contract-amendment` — written last, from the three rulings above.

## Explicit non-goals unless Bob says otherwise

- **Split instances run the same patch.** Bob said "two instances of the
  patch". Different patches per element is a much larger change (distribution,
  fingerprint, manifest, presets are all patch-scoped) and is out until asked
  for.
- **Not a generalisation to N.** Bob said two. The design should not be
  *hostile* to N, but it must not pay for N it will not use — §5 already notes
  "usually N is 1 or 2".
