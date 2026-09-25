# Patches reach devices only by push

When changing the manifest grammar or debugging a device on an old patch, remember `patches/` is gitignored: devices get patches from dashboard distribution, never from `git pull`.

A manifest hard break therefore reaches the field as fast as patches get pushed, and stale on-device manifests crash-loop the engine (Ciro Toast 2026-08-05, Finn Jet 2026-08-13). Until `58/4-invalid-manifest-lockout` lands, that also takes `bopos.py` off the network, and recovery is SSH.

Manifest facts: parameters declare an explicit `kind` (`float`, `int`, `toggle`, `enum`, `text` — `python/manifest.py`); events are declared separately and have no `labels` (v1.16); `dashboard: true` gates only the Remote view — Control and Device show every parameter. `presets/` is excluded from the patch fingerprint.

`/os/report` is requested on demand, so a device updated under a running dashboard keeps showing its old report.

## Triggers

- bopos.patch.json
- manifest.py
- crash loop
- stale patch
- patch_badge

## Associations

- [[osc-contract]]
- [[test-rig]]
