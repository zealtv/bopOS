# 01-suite-inventory-and-runner-contract

Establish the baseline before migrating archived assertions.

- Inventory the current `tests/` files by code surface, dependency tier, and
  invocation style.
- Define the durable-contract inclusion test: a check belongs in `tests/` only
  when the property should survive implementation and copy changes.
- Define fast browser-free and slower browser/integration tiers, using
  `~/.venvs/bopos/bin/python` and the constraints in `docs/VERIFICATION.md`.
- Produce a coverage/migration matrix naming the tied guards worth inspecting
  in children `02`–`06`; do not sweep or repair the archive.
- Recommend one stable local entry point for child `07` to implement.

Keep this a planning/inventory stitch. Do not migrate assertions here. Record
the result in the stitch so it travels to `.loom/tied/`.
