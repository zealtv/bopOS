# Proposal: finish the Seat / Device boundary

**Status: awaiting Bob's ratification.** This is the design gate before
`07-seats-workspace`, `08-unbound-admin-seam`, and `09-devices-workspace`.
It refines the already-ratified seats-first model; it does not reopen it.

## Decision in one paragraph

A **Seat** is the durable logical place in the piece; a **Device** is one
physical computer identified by stable `uid`. Keep one runtime device roster,
keyed by uid, and one binding fact: `seat.bound = uid | null`. Both map-first
and device-first assignment call the same atomic binding operation. Seat ID
changes are a real reindex transaction that moves the seat and every preset
reference together. Device administration addresses a physical uid even when
the node advertises seat ID `-1`, through one small UID envelope on the existing
OSC admin plane.

## 1. One model, two workspaces

The canonical records remain:

```text
seats[str(id)] = {id, name, positions, params, bound}
devices[uid]   = {uid, hostname, online, ip, version, report, ...runtime facts}
```

- Seat owns authored identity, geometry and live parameter values. Device does
  not acquire copies of them.
- Device owns physical identity, liveness, framework/engine facts and observed
  content state. It remains inspectable and administrable whether bound or
  unbound.
- `seat.bound` is the only dashboard-authoritative binding edge. The node's
  contract-required persisted assignment is a convergence replica for
  dashboard-less operation, not a second dashboard record. A uid may occur in
  at most one seat; a seat holds at most one uid. Enforce that invariant when
  loading installation state, venue snapshots and CSV seeds as well as when
  binding. Derived `device → seat` lookups never become a second record.
- Devices renders exactly one row per real uid. Bound/unbound/online/offline are
  filters or badges on that roster, not additional lists containing the same
  row. Virtual audition instances remain runtime-only and outside the physical
  Devices roster.

The device roster is runtime/recent-discovery state, keyed once by uid; it is
not added to `installation.json`. A bound uid is remembered by its Seat.
Unbound offline devices disappear across a dashboard restart and rejoin on
heartbeat. Durable friendly device aliases, if wanted, remain the later
`14-device-alias-design` decision rather than becoming a second roster here.

The two setup journeys are views over the same operation:

1. **Map-first:** select a Seat, Identify an available device, then Assign it.
2. **Device-first:** select an unbound Device, Identify it, then Assign it to an
   empty Seat.

The backend primitive is `bind(seat_id, uid)`. It validates both records and the
one-to-one invariant, changes the single `seat.bound` edge, persists once, sends
the seat's complete `/all/os/assign`, and emits one full-state result. “Complete”
assignment here means ID, name and positions; params continue through the
existing declaration/catch-up path.

Replacing, unbinding, deleting, forgetting, moving a uid, or loading a venue
must also revoke any displaced node's persisted assignment. If that node is
online, the operation first sends UID-targeted `unassign` and waits for its
`/hb <uid> -1 ...`; timeout rejects the operation without changing dashboard
state. If it is offline, the dashboard may commit, then sends `unassign` on its
next heartbeat before treating it as an available device. This prevents two
live nodes retaining the same selector. A crash between a successful unassign
and dashboard commit is recoverable: the unchanged authoritative Seat is
replayed on reconnect. Replacement is always explicit and confirmed, never an
incidental dropdown side effect.

## 2. Seat ID reindex is one transaction

`reindex_seat(old_id, new_id)` is distinct from ordinary `update_seat`:

1. Parse a non-negative integer new ID; reject a collision before mutation.
2. Build a replacement state in memory. Move `seats[str(old_id)]` to
   `seats[str(new_id)]` and update the embedded `seat.id`.
3. In every preset, treat a missing `seats` map as empty, but reject any present
   non-map. Move `preset.seats[str(old_id)]` to the new key while preserving all
   unrelated preset fields. A destination key collision rejects the whole
   operation even if that key is currently orphaned.
4. Validate the entire replacement before mutation. Replace memory once and use
   the existing temp-file + `os.replace` save for one atomic durable commit.
   Then send the newly indexed seat's assignment to its bound node. In
   Simulation, restart the managed fleet so runtime seat IDs match the commit.
5. Broadcast full state so selection reconciles by the returned new ID.

There is no interval where presets point at a missing seat, no delete-then-add
API, and no partial durable success. Seat name, positions, params and binding
move unchanged. OSC assignment and Simulation restart are post-commit
convergence effects: a failure leaves the committed model visible as degraded
and retryable rather than rolling it back. Venue files are snapshots: reindex
affects the current installation and its current presets; separately saved
venues change only when explicitly saved again. Loading a saved venue may
intentionally restore older IDs, but must validate the same one-to-one invariant
and revoke changed live assignments before committing the snapshot.

## 3. Full administration for an unbound uid

The current selector grammar is `all | seat-id`; consequently every unbound
node matches `-1`. Keep that grammar for performance/fleet control and add one
explicit admin envelope:

```text
/all/os/to <uid:string> <verb:string> [args...]
```

Every node receives the broadcast, compares the first argument with its own
opaque uid, and only the exact match dispatches the remaining verb and args to
the existing `/os` handler. The uid stays an OSC string rather than becoming an
address component, so MAC punctuation and future opaque uid forms are safe.

This is a targeting mechanism, not a general remote-execution mechanism:

- The node uses direct framework dispatch with an exact verb allowlist and each
  existing verb's arity/validation—never recursive OSC-address dispatch.
  Initially this is only the administration promised by Devices: `identify`,
  `report`, `reboot`, `shutdown`, `restart-engine`, `updatebopos`, plus the new
  idempotent `unassign`. Unassign clears the persisted node assignment, sets
  framework/engine ID to `-1`, keeps hostname, and wakes an immediate heartbeat.
  Content distribution, patch parameters, probes and storage are deliberately
  excluded. A later verb joins only through an explicit contract amendment.
- `/all/os/assign <uid> ...` remains the dedicated idempotent assignment form.
- Provided terms, patch parameters and safety mute retain their fleet/seat
  selectors; they do not pass through the UID envelope.
- The dashboard may use the envelope for any single physical device, bound or
  unbound, so the UI does not fork its action implementation by binding state.
- `/os/report` already carries uid. Ratify the node's already-implemented
  additive lifecycle receipt extension as `/os/rev <sha> <model> <uid>`, so
  lifecycle acceptance/provision convergence is attributable without treating
  source IP as identity. Identify has no reply; unassign confirms through the
  uid-bearing `id=-1` heartbeat. No unattributable reply family is admitted by
  the initial allowlist.

This replaces the special Identify exception with one uniform mechanism while
preserving `/all/os/identify <uid>` as a compatibility spelling until callers
move. `08-unbound-admin-seam` must bump/amend `docs/OSC-CONTRACT.md` and implement
the node, dashboard, simulator and focused same-`-1` isolation regression
together.

## 4. Workspace consequences after ratification

- **Implementation dependency:** land **08 Admin seam before completing 07
  Seats**. The accepted numbering described the UX order, but safe unbind,
  replacement, delete and venue load require UID-targeted `unassign`; 07 must
  not expose those mutations using dashboard-only state changes.
- **07 Seats:** seat create/delete/name/ID/positions/params and binding live
  here; reindex has collision feedback and preset migration; map-first setup is
  retained.
- **08 Admin seam:** ratify and implement `/all/os/to`, including proof that one
  of several unbound nodes executes a destructive command while its peers do
  not, plus the unassign handshake required by binding removal/replacement.
- **09 Devices:** one physical roster, device-first binding, complete facts and
  actions for bound and unbound rows, Identify, fleet-wide shutdown, drift and
  repair. No seat geometry, seat naming or mix parameters.

## Ratification questions

1. Accept the single `seat.bound` edge and one device roster, with both setup
   journeys calling the same confirmed binding operation?
2. Accept atomic Seat ID reindex across the seat key, embedded ID and every
   current preset reference, while saved venues remain explicit snapshots?
3. Ratify `/all/os/to <uid> <verb> [args...]`, the six existing admin verbs plus
   `unassign`, and attributable `/os/rev <sha> <model> <uid>` receipts as the
   UID-targeted admin seam?
4. Accept the safety dependency **08 before completion of 07**, despite the
   existing stitch numbering?
