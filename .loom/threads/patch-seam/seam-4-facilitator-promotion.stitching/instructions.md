# seam-4-facilitator-promotion

**GATED: requires `seam-1-contract-amendment` tied. Do not claim before.**

Per-patch promotion of controls to `/facilitator` (seam ruling; Bob ratified
the owner split 2026-07-10).

- **Patch params:** optional per-param manifest flag `"facilitator": true`
  (`bopos.patch.json`, additive §8). `dashboard/static/facilitator.html`
  renders promoted params as controls on the device card alongside the volume
  card; values flow as `/<id>/p/<name>` exactly as on the main view. Undeclared
  flag = ignored by old consumers.
- **bopOS commands:** install-level allowlist in `installation.json`
  (e.g. `"facilitator_commands": ["restart-engine"]`), **default empty** — the
  ratified no-admin-verbs scope guard holds until an install opts in. Rendered
  as confirm-gated buttons (destructive convergence verbs —
  update/checkout/reboot/shutdown — hold-to-confirm at minimum). Never
  patch-manifest-promoted (rejected by the council, upheld by Bob).
- `tools/simfleet.py`: example manifest gains a promoted param so the verify
  has a subject.
- Playwright `verify_*.py` (copy the newest tied dashboard verify as template;
  venv + chromium gotchas in CLAUDE.md).
