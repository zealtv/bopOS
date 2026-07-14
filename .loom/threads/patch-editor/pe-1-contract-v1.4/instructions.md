# pe-1-contract-v1.4

Land the cues manifest amendment, ratified 2026-07-14 (record:
`.lore/items/2026-07-14-patch-editor-design-ratified/`, proposal §6). v1.4
carries **cues only** — Bob explicitly kept the single-object §4.2 amendment
for its own later revision.

- Amend `docs/OSC-CONTRACT.md` §8 with the ratified wording: optional
  `"cues": [{"id", "label"?, "description"?}]`; `id` is the exact string
  delivered as the bare relative `/cue <id>` (§3.1 unchanged); declarations
  are documentation/UI surface only — the framework never filters undeclared
  ids nor schedules from the manifest; duplicate ids invalid; absent key
  valid. Bump the header to v1.4 with the amendment date.
- `python/manifest.py`: validate `cues` per the wording (reject malformed
  entries and duplicate ids loudly; absent key passes). Keep validation
  additive — every existing manifest stays valid.
- Update `patches/README.md`'s manifest section and add a declared cue to one
  tracked demo's manifest where it honestly matches patch behaviour (check
  what the demos actually respond to; don't declare fiction — skip if
  neither demo has a cue receive, and say so).
- Verification: manifest validator unit checks (valid, malformed entry,
  duplicate id, absent key); browser-free.
