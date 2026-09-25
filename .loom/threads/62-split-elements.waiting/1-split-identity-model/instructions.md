# 1-split-identity-model

**Status:** waiting (parent) · design gate
**Goal:** decide what a split element *is* to the framework and how one device
carries N Seats. Everything else in `62` depends on this.

## First, confirm the reading

"Targeted like usual" suggests the routable unit becomes the **engine
instance**: N instances, N Seat ids, N group memberships, one position each.
The alternative — one Seat with a sub-address per instance — is a different,
sometimes cheaper system. Confirm or reject before designing.

## Answer

1. **The unit.** Instance-as-Seat or Seat-plus-index? If instance-as-Seat, what
   is a *device* for afterwards (uid, heartbeat, patch, audio hardware, io bus)?
2. **Assignment carrying N.** `/all/os/assign <uid> <id> <name> [x y]×N` today.
   Options: per-slot messages; one message with N tuples (keeps
   idempotent full-state); a separate split-config verb. Must keep §5's
   guarantees: idempotent, uid-matched, heartbeat as ack, `-1` unassign
   tombstone.
3. **Heartbeat.** One beat with N ids, or N beats? It's also discovery — must
   still work for an unassigned split device.
4. **Groups.** Membership moves to the instance's Seat; the fail-closed
   clear-before-routable ordering must hold per instance.
5. **Selector matching.** Becomes "which of my instances match"; a message
   matching both must reach both.
6. **`/pt <point> <element> <v>`.** Does an instance still get an element index
   (0 each, or device-level?) or does the index vanish? Ideally unsplit patches
   change nothing.
7. **Unsplit devices unchanged.** Show how the design degenerates to exactly
   today's wire and node behaviour.

## Where to look

Contract §5; `python/bopos.py` (`resolve_id`, `resolve_elements`, `NodeState`,
`build_heartbeat`, `selector_matches`, `apply_assign`, `apply_unassign`,
`apply_groups`, `apply_points`); `python/groups.py`. The parent's inventory is
already done.

## Deliver

`proposal.md`: the unit, assignment/heartbeat shape (with rejected options),
group and selector semantics, `/pt` answer, degeneracy argument. Note the
implied contract changes (written in `4`). Mark `.waiting`, surface to Bob.
