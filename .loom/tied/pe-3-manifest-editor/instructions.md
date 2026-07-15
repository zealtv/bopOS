# pe-3-manifest-editor

UI-driven `bopos.patch.json` editing (ratified design:
`.lore/items/2026-07-14-patch-editor-design-ratified/`, proposal §5). Needs
pe-2 tied (lives in the editor UI).

- Param CRUD: name, type (`f`/`i`), min/max, default, group, facilitator
  flag. Cue CRUD: id, label, description. Writes are atomic (temp +
  rename) and validated through `python/manifest.py` before landing —
  invalid edits never reach disk. Warn on param rename/remove that PD
  receives must follow.
- Liveness (no dev-mode carve-out): on save, re-render the panel from the
  new manifest; sends already flow (relay doesn't validate `/p/*`,
  `/os/params` re-reads per request). No engine restart on manifest save.
- `engine`, `entrypoint`, `caps`, `slots` render read-only.
- **New patch** (Q2, Bob verbatim: "i want a stub written - but i'll provide
  the file to copy"): create `patches/<name>/` with a valid minimal manifest
  and a stub `main.pd` copied **verbatim** from Bob's template file. The
  editor never authors `.pd` content. Pick the template's home outside
  catalog listing (it is not a patch), document it in `patches/README.md`,
  and ask Bob for the file when this stitch is claimed — if absent, New
  patch succeeds manifest-only and says so in the UI.
- Verification: Playwright suite covering param add → control appears →
  value reaches the (or a `--no-engine`) instance; invalid edit rejected
  with the file untouched; New patch with and without the template present.
