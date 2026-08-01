# Results — dashboard-7-remove-param-roles

Done 2026-07-12. The param `role` concept is removed from contract, validator,
facilitator view, and both shipped manifests.

- Contract §8: role bullet is now a dated removal record; `facilitator: true`
  is the sole facilitator-surface mechanism (labelled control per promoted
  param; no promoted params → status-only card). Header carries the
  2026-07-12 amendment note. §11's stale `role:"meter"` sentence is left for
  `boundary-6-contract-v12-and-renames` (noted in its instructions).
- `python/manifest.py` rejects any `role` key loudly; the advisory now flags
  a manifest with no `facilitator: true` param.
- `facilitator.js` lost `volumeParam` (role lookup + `gain`-name fallback);
  cards render every promoted param through `paramControl`, which labels with
  the param name.
- `patches/default/bopos.patch.json` and the SC starter template swap
  `"role": "volume"` for `"facilitator": true` on `gain`.

Verification: `verify_role_removal.py` — 11/11 PASS (unit validator checks +
Playwright against real `dashboard/server.py` + `tools/simfleet.py` on
non-default ports; wire check `p/gain=0.41` observed in the simfleet log).
Screenshot: `role-removal.png`. Run from `~/.venvs/bopos`.
