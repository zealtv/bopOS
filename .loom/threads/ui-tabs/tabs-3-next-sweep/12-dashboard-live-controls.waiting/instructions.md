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

Depends on:

- 03 and stable Patches fleet schema;
- the tied `parameter-addresses` implementation foundation;
- tied Seat-group core plus the ratified spatial-membership UX and completed
  Seats group-authoring delivery.

Verify the flat/nested × All/Seat/Group cross-product and include iPad/touch
verification.
