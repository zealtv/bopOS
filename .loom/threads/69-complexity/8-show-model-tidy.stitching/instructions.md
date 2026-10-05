# 8-show-model-tidy

**Status:** after `67-repair-pass/24-show-number-boundary`
**Goal:** each show rule exists once, and the code describes today's shows.

Evidence: `lore:2026-10-05-bopos-review-show-model` F10, F11, F12.

- **F12.** `update_step`/`update_message` re-implement validators; merge the
  patch and validate through `clean_step`/`clean_message` (~40 lines less).
- **F11.** Remove the engine's unreachable defensive branches.
- **F10.** Comments still describe one `show.json` and a future engine; fix
  them. Stop writing the vestigial in-document `name` (file name is the name)
  while `tools/migrate_shows.py` still reads it. Deleting the legacy
  `show.json`, `.pre-*` backups and `migrate_shows.py` is Bob's call — not here.

Done when: UI-visible error texts unchanged; show tests, fast,
`verify_show_targets` and `verify_clear_show` green.
