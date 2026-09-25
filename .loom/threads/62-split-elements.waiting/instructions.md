# 62-split-elements

**Goal:** a device can be set to **split** its elements — one engine instance
per element, each with its own Seat, targeted like any other Seat. Configured in
the Device tab; owned by bopOS.

**Status:** waiting on queue order (Bob's order: `59` i2c work first, then this).
The whole thread is a **design gate** — nothing implements past it.

Bob, 2026-08-16: *"being able to set a device to be 'split' elements … they
should be targeted like usual … this is looking like it should be bopos-side,
and configured in the device tab."*

## Bigger picture

Bob sees this as the tip of a larger refactor, together with engine
agnosticism (*"we are going to want both pd and super collider as working
engines"*). See `lore:2026-09-25-horizon-architecture-refactor-2026-08-16`. Both break the same
assumption: **one device = one engine, probably Pd**.

Constraint on how this design is written (not a scope increase): say **engine
instance**, not "the Pd", and don't route per-instance identity through a
Pd-only mechanism.

## Why it's big

Contract §5 defines *device = one uid, one heartbeat, one engine instance*.
Split moves the routable unit from the device to the engine instance. Today
everything is 1:1:

- **Identity:** `/all/os/assign` carries one id; heartbeat `/hb <uid> <id> …`
  carries one id; `selector_matches` checks one id per node. Dashboard enforces
  one Seat per uid (seed loader, `clean_seats`, and `bind` displaces).
- **Ports:** 6661 (bopos→engine) and 6662 (io→engine) are singletons.
  `bopos.py` holds one engine client. **Precedent for N exists:**
  `tools/audition.py` runs N engines with `--engine-port-base` and
  `BOPOS_ENGINE_PORT` — a split device is audition-on-a-Pi. But Pd doesn't read
  `BOPOS_ENGINE_PORT`.
- **Audio:** nothing calls `jack_connect`; `pd -jack` auto-connects to
  `system:playback_1/2`, so two instances would silently sum. Per-instance
  channel routing has **no existing mechanism**.
- **Shared node services:** persistence store (one flat keyspace), mute /
  `enabled` (device-wide ALSA), `/os/report`, patch distribution, identify,
  `deliver_engine_context`.
- **Io bridge:** one registry, one reply route to one engine. Owned by
  `59/0a` (below).

**Performance upside:** Pd uses one core (99% on `bonks-pd` on a Zero 2 W) while
three sit idle. Split is the only proposal that uses them. Say so in the
proposal.

## i2c goes to `59/0a`

Bob ruled (2026-08-16) that peripheral ownership under split — including his
manifest-declaration idea — is decided in `59-i2c-inventory/0a-io-design-review`,
not here. `0a` answers first; `3-dashboard-model` inherits its ruling. Not a
`needs/` edge.

## Stitches

1. `1-split-identity-model` — what the routable unit is; how one device carries
   N Seats. Everything else depends on it.
2. `2-instance-runtime` — ports, launch, supervision, audio channels, node-scope
   services.
3. `3-dashboard-model` — device ↔ N Seats, Device-tab config, targeting,
   simfleet.
4. `4-contract-amendment` — written last from the three rulings.

## Non-goals (unless Bob says otherwise)

- **Same patch in every instance.** Different patches per element touches
  distribution, fingerprints, manifests and presets.
- **Two, not N.** Don't be hostile to N, but don't pay for it (§5: "usually N is
  1 or 2").
