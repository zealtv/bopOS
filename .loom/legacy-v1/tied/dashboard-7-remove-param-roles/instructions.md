# dashboard-7-remove-param-roles

Remove the manifest param `role` concept entirely (Bob's ruling, 2026-07-12).

Bob's reasoning, verbatim intent: with multiple elements per device, each
element will want its own volume, so anointing one param "the volume" is the
wrong model. Facilitator sliders come from `facilitator: true` alone — one
labelled control per promoted param, labelled with the param's own name.
`role: "meter"` had already fallen with the engine-boundary ratification
(2026-07-12); this removes the concept's last member and the `gain`-name
fallback with it.

Gain staging was never the role's business: the patch owns its internal gain
structure; the framework provides only the `master` term (§4.1). The role was
purely a facilitator-UI discovery hint, now redundant.

Scope:

- `docs/OSC-CONTRACT.md` §8 — role bullet becomes a removal record; the
  `facilitator` bullet describes labelled controls / status-only cards;
  header amendment note. (§11's residual `role:"meter"` text stays for
  `boundary-6-contract-v12-and-renames`, which owns the v1.2 rewrite —
  noted there.)
- `python/manifest.py` — any `role` key fails validation loudly; the
  no-volume advisory becomes a no-facilitator-param advisory.
- `dashboard/static/js/facilitator.js` — volume resolution deleted; every
  `facilitator: true` param renders via `paramControl` (already labelled).
- `patches/default/bopos.patch.json`, `templates/supercollider-bopos/
  bopos.patch.json` — `"role": "volume"` → `"facilitator": true`.
- `CLAUDE.md`, `dashboard/README.md` — wording.

Verify: `verify_role_removal.py` (unit checks + Playwright against the real
server + simfleet, per the dashboard verification convention).
