# 12-dashboard-live-controls

This is the single downstream integration point for promoted live controls
after nested parameter addresses and Seat groups land. Do not implement their
control surfaces in parallel stitches.

Add All / Group / Seat targeting for every promoted patch parameter alongside
Seat cards. Render the ratified nested parameter tree without flattening its
standard OSC identity; send one of:

```text
/all/p/<path...> <value>
/<seat-id>/p/<path...> <value>
/g<group-id>/p/<path...> <value>
```

Review cue/preset/card targeting after Seat labels land. Group writes update
every member Seat's durable value, including offline/unbound members, before
the one group OSC datagram is emitted. Preserve fleet/single-device promoted
admin scopes and fail-closed promotion.

Add compact **Send all** actions to the Dashboard for each Seat and for all
Seats. These replay the current durable parameter snapshot to the selected
scope so a running engine can be refreshed without touching every control.
Keep the actions idempotent and do not add explanatory UI copy.

Add mute/unmute for one physical device. Treat this as physical-box state,
distinct from the existing fleet safety mute and from patch parameters. Audit
the selector/UID targeting and convergence semantics before choosing the wire
shape; do not silently make it Seat-owned. Seat and Group mute/solo are a
separate, trickier design and are explicitly deferred from this stitch.
The resulting exact-UID proposal is in `device-mute-contract-proposal.md` and
must be ratified before this subfeature is implemented.

Depends on:

- 03 and stable Patches fleet schema;
- the tied `parameter-addresses` implementation foundation;
- tied Seat-group core plus the ratified spatial-membership UX and completed
  Seats group-authoring delivery.

Verify the flat/nested × All/Seat/Group cross-product, per-Seat and All
parameter replay, individual-device mute convergence, and iPad/touch behavior.
