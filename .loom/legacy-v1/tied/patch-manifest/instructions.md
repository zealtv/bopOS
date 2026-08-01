# patch-manifest

**Do after `hb-identity`/`assign-persistence` — Crux 2's keystone.**
Contract: `docs/OSC-CONTRACT.md` §8. Reasoning: `schema-design-draft` (tied) —
`judgment.md` §3D.

- Add `bopos.patch.json` to `patches/default/`: engine, entrypoint, params
  (name/type/min/max/default/group), optional caps tags and asset slots. Declare the
  legacy three (`gain`, `backing`, `echo`) as params.
- helper.py serves it verbatim: `/<id>/os/params` → unicast `/os/params <json>`.
- Generalise the launcher: `bash/start.sh` reads engine/entrypoint from the manifest
  instead of hardcoding `pd … main.pd`; helper.py `/patch` validates the manifest
  (not `main.pd`, helper.py:111). PD stays the reference engine. Launcher validates
  declared params exist before start (anti-drift).
- Param values flow as `/<id>/p/<name>` / `/all/p/<name>`. The PD-side `route p`
  and the one-release aliases for bare `/gain` `gain2` `backing` `echo` are **Bob's
  .pd edits** — specify them precisely in the stitch, don't make them.
- `/os/report` (contract §6) returns the static facts JSON — implement it here since
  it reads the same manifest + system sources (`io/sys_*` already have most getters).

Verify in simfleet + dashboard-1: dashboard renders sliders purely from the declared
params of a patch it has never seen; a manifest-less patch gets legacy sliders with a
visible "undeclared" badge.
