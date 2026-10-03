# 2-doc-drift

**Status:** ready · small
**Goal:** docs only reference files that exist.

- [ ] `pd/bopos.pd` → `pd/bopos~.pd` in `docs/OSC-CONTRACT.md` (§4.2, two
      places — editorial, no version bump needed; say so in §15 if the house
      style wants it), `docs/OSC-REFERENCE.md`, `docs/COMPOSING.md`.
- [ ] Add a cheap guard: a fast-tier test that every `` `path/like/this` `` in
      `README.md`, `docs/*.md` and component READMEs exists (the review's
      check, made permanent; allow placeholders like `patches/my-piece/`).
