# 4-node-daemon-tidy

**Status:** verified within the user's boundaries; see `verification.md`,
`id-type-proposal.md` and `import-assessment.md`.
**Goal:** remove the dead defensive code and duplication in `python/bopos.py`.

1. **`send_to_engine` never raises** — it catches every send error and returns
   a bool — yet ~10 callers wrap it in try/except (`apply_assign`,
   `apply_unassign`, `apply_points`, `relay_provided_term`,
   `fire_event_to_engine`, `load_callback`, `send_groups_to_engine`, …). Remove
   the wrappers; use the return value where a caller actually cares.
2. **Duplicated cache warming** — `_asset_warm_loop` / `warm_asset_cache` /
   `initialise_asset_cache` and the patch trio are copies. One helper.
3. While here: the `/notify` + `send_to_engine` preamble repeated in every
   lifecycle callback; `/id` sent as float in `apply_assign`/`apply_unassign`
   but int elsewhere — pick one (int; check the Pd side reads either, note in
   `64-pd-edits-owed` if not).
4. Module import has side effects — binding port 7770 and reading node state at
   import. Say whether moving that under `__main__` is worth it (tests import
   the module); do it if cheap.

Done when: behaviour unchanged, fast tier green.
