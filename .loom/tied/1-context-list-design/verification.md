# Design verification

Checked 2026-07-23.

## Sources inspected

- `CLAUDE.md`, the latest handoff, Loom status/protocol, and
  `docs/VERIFICATION.md`
- current run-context contract sections 4.2, 9, 13, and revision history
- `bash/start-engine.sh`, `python/runcontext.py`, and the asset inventory,
  validation, fetch, and drop paths in `python/bopos.py`,
  `python/identity.py`, and `python/fetcher.py`
- `pd/bopos~.pd` and the shipped PD template (read-only)
- `patches/demo-sc/main.scd`, `tools/audition.py`, and
  `tools/perf_matrix.sh`
- dashboard device inventory, active manifest-slot state, and Assets
  workspace
- the accepted 2026-07-15 asset-management record and prior engine-boundary
  decision

## Findings

- The existing top-level asset-slot model already supplies multiple
  independently managed slots. A separate registry would duplicate and risk
  drifting from fetch, inventory, and dashboard state.
- `installed_assets()` already provides the correct visible,
  non-symlink-directory selection and deterministic name ordering, but the
  rule is local to `bopos.py`; implementation should share it with run context.
- Production, audition, performance tooling, the SC demo, PD's singleton
  helper, templates, and docs all currently assume one root and are included
  in the proposal's touch surface.
- `/os/assets`, fetch/drop, and manifest `slots` do not need a wire change.
- SuperCollider's installed standard class library provides
  `String:parseJSON`; JSON-array environment delivery does not require a
  Quark.
- The proposal preserves the current access semantics by listing every
  installed slot, while keeping active manifest slots as dashboard safety
  metadata.

## Checks

- `git diff --check` — passed.
- No `.pd` file was edited.
- No runtime or contract implementation was started before ratification.
- Hardware, PD behavior, and engine launch were not tested because this stitch
  is still a design gate.
