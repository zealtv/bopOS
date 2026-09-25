# 64-pd-edits-owed

**Status:** waiting on Bob — Pd edits are his; agents never edit `.pd`.
**Goal:** land the Pure Data edits the framework still owes, so nothing lives
only in a notes file.

Checked against `pd/` and `patches/` on 2026-09-25. Full specs, exact
spellings and verification steps: `lore:2026-09-25-pd-edits-for-bob-2026-08`
(`content/pd-edits-for-bob.md`). Everything else in that record has landed.

## Owed

- [ ] **`samplepacks` path templates.** The engine no longer creates the
      `bop/samplepacks` link, but `pd/bop/bop.stream~.pd` and
      `pd/bop/bop.sampler~.pd` still use `%s/samplepacks/$1/*/` and
      `%s/samplepacks/bop_samplepack/*/`. Change to `%s/$1/*/` and
      `%s/bop_samplepack/*/` (they live in the `pd/bop` submodule).
- [ ] **demo-pd asset context.** `patches/demo-pd/main.pd` doesn't route the
      launch-delivered `assets` root yet: `[r bopos-context]` →
      `[route seed run-id patch assets id]`, publish the root, show building
      `<assets-root>/<slot>/<file>`. Only when the demo has a real teaching
      asset; no fake paths.
- [ ] **Nested parameter routes — on first use.** `pd/bopos~.pd` already
      preserves nested paths. The first patch that declares a nested param
      changes its consumer from `[route distortion]` to
      `[route track1] → [route fx] → [route distortion]`.

## How agents add to this

When a change needs a Pd edit, add a checklist item here (or a child stitch
if it's large) with exact spellings and how to verify, then verify the
Python/dashboard/simfleet side on its own.
