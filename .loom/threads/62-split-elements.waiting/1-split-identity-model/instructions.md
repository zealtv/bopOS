# 1-split-identity-model

Decide what a split element **is** to the framework, and how one device
carries N Seats. Every other stitch in this thread is downstream of this
ruling.

Design gate: ends in a written proposal Bob ratifies. Do not implement past it.

## The question

Bob: *"how split elements are given seats — they should be targeted like
usual."* Taken literally that means the routable unit stops being the device
and becomes the **engine instance**: N instances, N Seat ids, N group
memberships, one element position each. Confirm or reject that reading before
designing anything, because the alternative — one Seat with a sub-address per
instance — is a genuinely different system and cheaper in places.

## What must be answered

1. **The unit.** Instance-as-Seat, or Seat-plus-element-index? If
   instance-as-Seat, say what a *device* is for afterwards — it still owns the
   uid, the heartbeat, the patch, the audio hardware and the io bus, so it
   does not disappear.
2. **How assignment carries N.** `/all/os/assign <uid> <id> <name> [x y]×N` is
   idempotent full-state with one id (`python/bopos.py:779`). Candidates, all
   with costs to state:
   - a slot argument (`<uid> <slot> <id> <name> x y`), N messages, N acks;
   - one message carrying N `(id, name, x, y)` tuples, staying idempotent
     full-state — which is what the current verb's design principle points at;
   - a separate split-configuration verb, with assignment unchanged per slot.
   Whichever wins must keep §5's guarantees: idempotent, only the matching uid
   applies, the node acks by heartbeating, and unassignment leaves an explicit
   `-1` tombstone that a `bopos.devices` seed cannot resurrect.
3. **The heartbeat.** `/hb <uid> <id> …` reports one id
   (`build_heartbeat`, `:354`), and the dashboard binds a Seat by matching it.
   Does a split device beat once with N ids, or N times? Note that
   §5 makes the heartbeat the *discovery* mechanism and the assignment ack —
   both roles have to keep working for an unassigned split device.
4. **Groups.** Membership is per node today (`state.groups`, persisted under
   the single Seat, `apply_groups` `:855`, `send_groups_to_engine` `:699`) and
   the contract requires a Seat's membership never leak across an assignment
   transition. Under split, membership belongs to the instance's Seat, and the
   fail-closed clear-before-routable ordering must hold per instance.
5. **Selector matching.** `selector_matches(selector, device_id, memberships)`
   (`:494`) is called once per incoming message against the node's single id.
   Under split, one datagram may match instance A and not instance B, so
   matching moves from "does this node match" to "which of my instances
   match" — and a message matching both must reach both.
6. **Element position and `/pt`.** bopos.py computes proximity per element and
   sends `/pt <point> <element> <v>` (`apply_points`, `:873`) with a 0-based
   index from assignment pair order. Under split, does an instance still
   receive an element index (and if so, is it 0 for each instance, or its
   device-level index), or does the index disappear because the instance *is*
   the element? Whichever is chosen, say what a patch written for the
   unsplit case has to change — ideally nothing.
7. **Unsplit devices must be untouched.** The overwhelmingly common case is
   one instance, one Seat. State how the design degenerates to exactly
   today's behaviour, on the wire and in the node, so an unsplit fleet cannot
   regress.

## Evidence

- Contract §5 (identity, assignment, persistence) and its `device`/`element`
  definitions — the sentence being amended.
- `python/bopos.py`: `resolve_id` `:187`, `resolve_elements` `:212`,
  `NodeState` `:238`, `build_heartbeat` `:354`, `selector_matches` `:494`,
  `apply_assign` `:779`, `apply_unassign` `:828`, `apply_groups` `:855`,
  `apply_points` `:873`.
- `python/groups.py` for the selector grammar.
- The parent's "Starting state" section — the 1:1 inventory is already done.

## Deliver

`proposal.md` in this stitch: the ruling on the unit, the assignment/heartbeat
shape with alternatives and why they lost, the group and selector semantics,
the `/pt` answer, and the degeneracy argument for unsplit devices. Note the
contract amendment it implies but do not write it — that is `4`.

Then mark `.waiting` and surface it.
