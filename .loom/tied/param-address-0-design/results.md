# param-address-0 survey result

The parameter-address surface is a medium, bounded cross-cutting change. The
current flat name is simultaneously the manifest identity, fleet and engine OSC
suffix, dashboard/preset key, and UI label/group member. The proposal separates
hierarchy from the leaf name and keeps current flat behavior unchanged.

Recommended shape:

- optional manifest `path` array plus existing leaf `name`;
- slash-qualified public identity and stored key;
- the same literal nested address on the fleet and engine surfaces;
- one engine-agnostic standard OSC surface with no Pd-specific adaptation;
- Pure Data receives the native parsed hierarchy, with nested consumer routes
  added by Bob for patches that adopt nested parameters.

The design and impact survey is in `proposal.md`. Bob ratified it together with
the companion Seat-group proposal on 2026-07-15. No contract, runtime,
dashboard, manifest, or `.pd` implementation changed.
The original dot-flattening survey is retained at
`.lore/items/2026-07-15-nested-parameter-address-design/` for decision history.
It is superseded by the amended engine-agnostic proposal at
`.lore/items/2026-07-15-osc-native-nested-parameter-address-design/`.

The later Seat-group review confirms that lowercase group selection composes
without changing parameter identity:

```text
/g1/p/track1/fx/distortion -> /p/track1/fx/distortion
```

Group membership is a separate fleet-routing concern. `g1` is never part of a
manifest declaration, stored parameter key, preset key, or engine address. The
companion design is lore-kept at
`.lore/items/2026-07-15-seat-group-selector-design/`.

## Survey evidence

- `python-osc` and `pyOSC3` both round-tripped
  `/all/p/guitar/reverb/gain 0.5` without changing the address or value.
- Local Pure Data is 0.55.2. Static inspection of `pd/bopos.pd` confirms
  `[oscparse]` followed by `[route p]` publishes the remaining parameter list on
  `bopos-param`; `/p/track1/fx/distortion 0.5` therefore becomes
  `track1 fx distortion 0.5` without changing the framework abstraction.
- The exact flat-depth gates were found in `python/relay.py`, `python/bopos.py`,
  `tools/audition.py`, and `tools/simfleet.py`.
- Dashboard value identity flows through `dashboard/osc_bridge.py`,
  `dashboard/server.py`, `dashboard/state.py`, the patch editor, facilitator
  controls, Seat values, presets, and venue copies.
- `python/store.py` is not part of dashboard parameter persistence and need not
  change.

## Verification

- Documentation/design consistency review against `CLAUDE.md`,
  `docs/OSC-CONTRACT.md` §§3, 4.1, 4.2, 8, 10, 12–14, the ratified patch-editor
  design, the tab information architecture, and current implementation: passed.
- `./.lore/lore.sh status`: 22 valid items, index refreshed, 0 invalid, 0
  partial; each lore payload and stitch proposal matched before keeping.
- `git diff --check`: passed.
- No runtime code, browser behavior, OSC contract, stored installation state,
  hardware, or `.pd` file changed; implementation verification is not applicable
  to this proposal-only stitch.

## Bob amendment

Bob rejected dot-flattening and requires true OSC hierarchy through the common,
engine-agnostic surface. The amended proposal preserves
`/p/track1/fx/distortion` identically for Pure Data, SuperCollider, and future
engines. In Pd, `oscparse` exposes the path as atoms for nested `[route]`
objects. The earlier lore capture is superseded by the amended capture recorded
after this result.

## Ratification

Bob ratified the complete amended proposal on 2026-07-15: separate manifest
`path` plus leaf `name`, canonical slash keys and remove-plus-add path moves,
`path` as authoritative hierarchy with legacy `group` compatibility, and the
lowercase `g<id>` selector cross-product.
