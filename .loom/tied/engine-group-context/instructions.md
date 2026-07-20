# engine-group-context

Expose the node's current Seat-group memberships to the active engine through
the existing bopOS-owned context surface.

## Outcome

- Deliver `groups` as the complete current membership list when the engine
  starts, alongside the other run-context values.
- Update the engine context after every successful membership change, including
  assignment/unassignment transitions that clear membership.
- Deliver group IDs as a list of OSC integers in canonical stored order. The
  no-membership representation is the single integer sentinel `-1`; valid
  group IDs remain non-negative.
- Keep the dashboard/node full-state membership acknowledgement and persistence
  behavior unchanged; only successfully applied durable state reaches the
  engine.
- Preserve engine isolation: this is node-local engine context, not a new LAN
  control plane. Do not edit `.pd` files; record any reference-patch receiver
  work for Bob in `.notes/pd-edits-for-bob.md`.

For PD, use the established `bopos-context` bus with the shape
`bopos-context groups <int...>`. Keep the non-PD engine boundary equivalent if
the current launcher/runtime context adapter needs an additive representation.

## Likely touch points

- `python/bopos.py` membership application and assignment/unassignment clears;
- `python/runcontext.py` and `bash/start-engine.sh` launch delivery;
- `tools/audition.py` parity for local audition engines;
- `docs/OSC-CONTRACT.md` / engine-context documentation.

## Verification

Add a browser-free focused verifier that proves:

1. an engine starts with the node's persisted memberships as integer values;
2. replacing membership emits exactly one complete updated context list;
3. clearing membership emits exactly `groups -1`;
4. rejected or failed-to-persist membership does not reach the engine;
5. assignment/unassignment cannot leak the previous Seat's groups; and
6. audition behavior matches the node helper.

Run focused Python compilation and the nearby launch-context and Seat-group core
regressions. Record hardware/audio and Bob's PD receiver edit as unverified
boundaries unless they are actually exercised.
