# Seat groups — survey and design proposal

Status: **ratified by Bob on 2026-07-15** together with the nested
parameter-address proposal. No implementation or OSC contract change has been
made.

## Recommendation

Add a third fleet selector form, `g<group-id>`, alongside `all` and a numeric
Seat ID:

```text
/<selector>/<plane>/<member>...  selector: all | <seat-id> | g<group-id>
```

Examples:

```text
/0/p/gain 0.5
/g1/p/gain 0.5
/g1/p/track1/fx/distortion 0.5
/all/p/track1/fx/distortion 0.5
```

Every node receives the same broadcast UDP datagram and decides locally whether
its assigned Seat matches the selector. A matching node strips only the first
segment. The engine therefore receives:

```text
/p/track1/fx/distortion 0.5
```

for all three fleet scopes. Group selection is framework routing and is never
visible to Pure Data, SuperCollider, or another engine.

This is a **medium, bounded cross-cutting change**. Selector matching itself is
small. The work is mostly making Seat membership durable and convergent across
the dashboard, real nodes, simulation, audition, and venue state. It should not
require a new port, a new plane, engine-specific address shaping, or any `.pd`
edit.

## Selector grammar

- A group selector is lowercase `g` followed by a canonical non-negative
  decimal integer: `g0`, `g1`, `g27`.
- Leading zeroes are invalid except for `g0`: `g01` does not alias `g1`.
- The spelling is case-sensitive: `G1` is invalid.
- `all`, numeric Seat IDs, and `g<id>` cannot collide.
- Group IDs are wire identities. A separate display name may be changed without
  changing the selector.
- A node with no assigned Seat (`id == -1`) never matches a group selector,
  even if corrupt or stale membership exists locally.
- Version 1 has no nested groups. A group contains Seats, not other groups.

The address stays standard OSC. `g1` is an ordinary OSC path segment; there is
no wildcard, expansion syntax, dot encoding, or dashboard-only shorthand.

## What a group contains

Groups contain **Seats**, not devices. This preserves the existing identity
boundary:

- a Seat carries authored installation state;
- a physical device is temporarily bound to a Seat;
- replacing the device bound to Seat 2 does not change Seat 2's groups;
- an unbound Seat remains a member and retains dashboard parameter values;
- an unassigned device belongs to no group.

A Seat may belong to multiple groups. Groups may be empty. Group display names
are optional but useful in the facilitator UI. Deleting a group removes its ID
from every Seat as one durable state transition.

Recommended dashboard state shape:

```json
{
  "groups": {
    "1": {"id": 1, "name": "Front row"},
    "2": {"id": 2, "name": "Guitars"}
  },
  "seats": {
    "0": {"id": 0, "groups": [1, 2]},
    "1": {"id": 1, "groups": [1]}
  }
}
```

The real Seat records keep their existing name, positions, params, and binding;
the example shows only the new fields. Group IDs and Seat membership are
included in venue snapshots. Presets remain parameter snapshots and do not copy
or replace group structure.

## Node-side membership and standalone operation

Dashboard fan-out is not sufficient. Translating `/g1/p/gain` into several
numeric packets in the dashboard would mean direct OSC senders could not use
groups, operation would depend on the dashboard, packet cost would scale with
group size, and a lost packet could split the group.

Instead, every assigned node persists the complete group set for its Seat. This
keeps `/g1/...` usable from any OSC controller and preserves the project's
dashboard-less, standalone design.

Use an additive full-state membership command:

```text
/all/os/groups <uid:string> <group-id:int32>...
```

All nodes receive it; only the exact UID applies it. The trailing list replaces
the node's complete membership, so an empty list means “no groups”. The node
validates non-negative, unique integers, persists the list, then replies to the
controller:

```text
/os/groups <uid:string> <group-id:int32>...
```

The reply is attributable even when simulated nodes share an IP address. The
dashboard treats an exact reply as convergence, retries a lost update for a
bounded interval, and replays the full membership when a device reconnects.
`/os/report` should also include `groups` as an inspectable persisted fact, but
report is reconciliation evidence rather than the immediate write receipt.

This should remain separate from `/all/os/assign`. Assignment's existing
variadic tail is an unframed list of element-position floats; inserting group
IDs there would be ambiguous and would break older nodes. A separate idempotent
full-state command is additive and independently retryable.

### Safe transitions

- `/all/os/to <uid> unassign` clears persisted groups in the same operation that
  sets ID `-1`; a stale unbound box must never respond to `/g...`.
- Reassigning a node directly to a different Seat ID clears its previous groups
  before the new assignment becomes routable. The dashboard then sends the new
  Seat's full group set. The safe temporary state is omission, never accidental
  membership in the old Seat's groups.
- Replaying the same Seat assignment does not clear groups. Otherwise routine
  assignment repair followed by a lost membership packet could erase valid
  standalone state.
- A failed membership persistence write leaves the previous in-memory and
  persisted set intact and emits no success receipt.

The two messages are not transactionally atomic on the wire, but these rules
make every partial ordering fail closed. This is proportionate to the existing
UDP assignment convergence model and avoids replacing the ratified assignment
envelope.

## Selector scope

The selector grammar is framework-wide, but each member still defines its
allowed scopes. The clean rule is:

> A group selector is legal wherever a concrete numeric Seat selector is legal.

That includes patch parameters and ordinary selector-addressed `/os`, `/io`,
and `/sync/offset` messages. Existing special cases remain special:

- `/cue` and `/pt` are selectorless and fleet-wide; this proposal does not add
  group cues or group point fields.
- `/sync/ping` is selectorless broadcast.
- `/all/os/to <uid> ...`, `/all/os/assign ...`, and `/all/os/groups ...` are
  exact administrative envelopes and remain literally `/all/...`.
- Any verb already constrained to `all` only or one exact UID keeps that
  constraint.

This avoids a “groups work only for gain knobs” dialect while preserving the
explicit exceptions already in the contract. Querying a group may produce one
reply per online member; replies retain their existing UID/source attribution.
The dashboard may continue issuing per-device queries when it wants bounded,
row-attributable results.

## Dashboard behavior

The Seats workspace is the authoring surface:

- create, rename, and delete groups;
- add or remove one Seat from multiple groups;
- display the canonical token (`g1`) beside its editable display name;
- validate changes before saving and synchronizing bound nodes.

The future Dashboard live-controls surface can choose All, one Group, or one
Seat. A group parameter change has two coordinated effects:

1. update the canonical parameter value for **every member Seat**, including
   offline and currently unbound Seats;
2. emit one `/g<id>/p/<qualified-parameter> <value>` datagram for online nodes.

Updating Seat state rather than only current devices is important: an offline
member must receive the same value during later parameter catch-up. Overlapping
groups are unsurprising last-write-wins control scopes; sending to `g1` then
`g2` updates Seats in both twice, in message order.

Group-scoped framework values need to follow the state semantics of their
member. Stateless commands can simply use the group selector. A dashboard-owned
full-state value such as master must update all member Seat/device mirrors or
remain outside the group UI until that state model exists; the wire grammar
alone must not create a misleading dashboard state.

## Cross-impact with nested parameter addresses

The two proposals compose without ambiguity because they own different address
regions:

```text
/g1 /p/track1/fx/distortion
 ^       ^
selector parameter hierarchy
```

The only transformation is:

```text
/g1/p/track1/fx/distortion  ->  /p/track1/fx/distortion
```

Consequences for `param-address-0-design`:

- extend its selector grammar from `all | <id>` to
  `all | <id> | g<group-id>`;
- keep the manifest `path` and leaf `name` design unchanged;
- keep the canonical dashboard/preset parameter key
  `track1/fx/distortion` unchanged;
- ensure dashboard address construction accepts a selector token separately
  from the qualified parameter segments;
- test the cross-product of flat/nested paths and all/Seat/group selectors;
- never include `g1` in the stored parameter key or the engine address.

Implementation should centralize these two concepts in separate helpers:

- `parameter_segments(declaration)` / `parameter_key(declaration)` owns the
  patch hierarchy;
- `selector_matches(selector, seat_id, groups)` owns fleet targeting.

Keeping them separate prevents UI strings or slash-joined keys from becoming a
second OSC parser. The parameter-address work is the natural first foundation
for variable-length `/p/...` relay; group membership can then extend the same
matcher and address builders without reworking engine delivery twice.

## Expected implementation surface

The principal production areas are:

- `docs/OSC-CONTRACT.md` — selector grammar, group state envelope, persistence,
  receipts, and scope exceptions;
- `python/bopos.py` — persisted membership, fail-closed transitions, group
  matching, command/reply, report fact, and variable-length selected relay;
- `dashboard/state.py` — group catalog, Seat membership, validation, durable and
  venue state;
- `dashboard/osc_bridge.py` and `dashboard/server.py` — synchronize/reconcile
  membership, group target resolution, and stored parameter fan-out;
- dashboard Seats and live-control UI — group authoring and selector choice;
- `tools/simfleet.py` and `tools/audition.py` — identical membership and matching
  behavior;
- focused protocol/state/browser regressions plus existing selector regressions.

The exact file count depends on where the upcoming live controls land, but this
is likely a dozen production files plus tests. The core node matcher is surgical;
end-to-end correctness is not.

No `.pd` work is required. Pd and every other engine receive the same
selector-free standard OSC message they receive for numeric or `all` selection.

## Implementation sequence after ratification

1. Ratify and amend the OSC contract for lowercase `g<id>` and the membership
   envelope.
2. Implement shared node persistence/matching plus focused real-helper tests.
3. Extend simulator and audition nodes in the same protocol stitch.
4. Add durable dashboard group/Seat state and venue validation.
5. Add acknowledged membership synchronization and reconnection repair.
6. Add Seats authoring UI and its browser verification.
7. Integrate All / Group / Seat into Dashboard live controls, sharing the nested
   parameter address helpers.
8. Run the combined nested-address/group-selector matrix and a real-LAN smoke
   test before claiming rig adoption.

## Ratified decisions

Bob ratified the following as one coherent decision on 2026-07-15:

1. lowercase `g<non-negative-id>` selectors (`g1`, never `G1` or `g01`);
2. multiple groups per Seat, no nested groups in version 1;
3. a durable group catalog plus `groups: [id...]` on each Seat;
4. node-local persisted membership synchronized by the additive full-state
   `/all/os/groups <uid> ...` envelope and `/os/groups <uid> ...` receipt;
5. group selectors wherever numeric Seat selectors are legal, retaining the
   contract's explicit selectorless/all-only/UID-only exceptions;
6. group-targeted parameter writes update all member Seats, including offline
   and unbound members, before one standard OSC group datagram is emitted.

These points lock the cross-impact in the nested parameter-address proposal. UI
layout details remain with the Seats and Dashboard live-control implementation
stitches.
