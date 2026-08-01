# boundary-6-contract-v12-and-renames

Finalise the ratified engine boundary after every nested migration gate is tied.

- Read `.loom/tied/engine-boundary-ratification/ratification.md`; it is the
  authority over the earlier council judgment.
- Revise `docs/OSC-CONTRACT.md` explicitly to v1.2, including the civil-time
  amendment, removal of `role: "meter"`, and the clean-break policy. Note:
  the whole param `role` concept is already gone (Bob 2026-07-12, tied
  `dashboard-7-remove-param-roles` — facilitator sliders come from
  `facilitator: true`); v1.2 must not reintroduce any `role` wording, and
  §11's residual `role: "meter"` reference still needs excising here.
- Rename `python/helper.py` to `python/bopos.py` as a separate behavior-free
  change and update all references. Do not rename mid-migration.
- Verify at the contract/docs level prescribed by `docs/VERIFICATION.md` and
  record any remaining hardware caveat honestly.
- Do not implement the deferred leased probe, report-presentation schema, or
  generic capability-provider/plugin idea.
