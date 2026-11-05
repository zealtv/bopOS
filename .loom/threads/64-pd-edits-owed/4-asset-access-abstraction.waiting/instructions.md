# 4-asset-access-abstraction

**Status:** Bob's (glean `never-edit-pd`) · needs `3-asset-access-design`
**Goal:** build the asset utility Bob ratifies in `3`, and adopt it where
patches hand-roll asset paths today.

## Do (after `3` is ratified)

- Build the abstraction(s) in `pd/` with a `-help.pd`, and link it from the
  `bopos~` help patch (`2-live-pd-reference`).
- Replace `kc-test`'s `get-tilt-file` / `get-trigger-file` /
  `get-point-file` subpatches and its hard-coded asset list, fire-button's
  hard-coded `pack ../../../assets/fire-button`, and bonks-pd's dead
  `[r bopos-assets-path]` (nothing sends it).
- **`samplepacks` path templates** (folded in from `64`'s checklist,
  2026-11-05; first recorded by the assets cache repair, `lore:2026-09-25-pd-edits-for-bob-2026-08`).
  The engine no longer creates the `bop/samplepacks` link, but
  `pd/bop/bop.stream~.pd` and `pd/bop/bop.sampler~.pd` still use
  `%s/samplepacks/$1/*/` and `%s/samplepacks/bop_samplepack/*/`. Either
  change them to `%s/$1/*/` and `%s/bop_samplepack/*/`, or have them take a
  folder path from the utility, per `3`'s loader decision. They live in the
  `pd/bop` submodule. As of 2026-11-05, `pd/bop/bop.stream2~.pd` and
  `help-bop.sampler~.pd` also still mention `samplepacks`.
- **demo-pd asset example** (folded in from `64`'s checklist): once the
  demo has a real teaching asset, show the utility there. No fake paths.

## Verify

- In Patch Edit on the laptop and on a Pi, the utility finds the slot, lists
  it, and picks the same file on the same device id.
- `bop.stream~` / `bop.sampler~` play from a sent slot with no `samplepacks`
  link present.
- KC's tilt, trigger and point files still load on the KC Pis (hardware
  claim, recorded separately).
