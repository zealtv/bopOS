# 3-event-fields-wire

Implement typed event fields on the wire, as ratified in `1-typed-event-fields.tied/proposal.md`.

- `python/manifest.py`: an event's `fields` list validated by the param
  checks, plus `optional` (default false; optional fields trail and carry a
  default); `arity`/`defaults` rejected loudly; up to 16 fields.
- `python/bopos.py`: accept `f`/`i`/`s` fields within the proposal's limits
  (text: printable ASCII, no whitespace, 1–255 bytes; ints |v| ≤ 2^24);
  `fire_event_to_engine` keeps each tag.
- `dashboard/osc_bridge.py` `fire_event`: tag each field by its kind.
- `tools/simfleet.py`, `tools/audition.py`: same parity.
- Migrate the local `patches/` manifests (`bonks-pd`, `demo-pd`, `kc-test`
  as of 2026-10-26) and test fixtures. `patches/` is gitignored: say in the
  tie note that migrated patches must be pushed with the bopOS update.
- Contract: §3.2, §8, §15 — the next free version (v1.22 unless
  `62-split-elements` lands first). `docs/OSC-REFERENCE.md` examples.
- Release note: typed events need every node updated; older nodes drop them
  silently (Bob, 2026-10-26: release note only).

Done when `tools/run-tests.sh` passes with new tests for validation, node
parsing and limits, simfleet receipt and audition parity. Hardware is
`5-pd-event-fields`.
