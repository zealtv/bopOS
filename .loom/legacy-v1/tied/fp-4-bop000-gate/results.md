# fp-4 bop000 hardware gate — 2026-07-15

## Outcome

The fleet-wide patch model passed its real-node gate on bop000
(`2c:cf:67:b3:0a:58`) at repository revision `1f0a5b9` through the real
dashboard on the installation LAN.

- Initial observed state was active `bonks-pd`, desired `demo-pd`, badge
  `mismatch`.
- Confirmation-gated **Set fleet patch** switched to `demo-pd`. Its active
  node fingerprint exactly matched the host fingerprint:
  `dd1c3ad92f004f00f78fe8d45c984dce6191f50561650bba37abcd874f5d68b3`.
- An empty non-PD marker file was added to the node's mirrored `demo-pd`
  directory. The node fingerprint changed to
  `ff4074e97b94981585d228ab7aa2c52fd5a72b4f6d98e12f94e5bc0ab94364c4`;
  a fresh `/os/patches` listing produced the `stale` badge.
- Row-level **Retry** replaced the mirrored content, removed the drift marker,
  restored the host fingerprint, and returned the badge to `current`.
- Confirmation-gated **Revert** returned the fleet to `bonks-pd`, with active
  node and host fingerprints equal at
  `8c4da2e48d4866c00b31d96da8d94e9f164586b538464fab7135e63ece1b38d3`.
- Because the node had no Git-managed patches installed, inactive `demo-sc`
  was temporarily initialized as a valid local Git repository. A fresh listing
  reported `git: true` while retaining the same content fingerprint (dot files
  are excluded). Its `.git` directory was then moved to `/tmp`, and a final
  refresh confirmed every installed patch was restored to `git: false`.
- At Bob's request during the run, fleet master was set to `0.01`; the final
  dashboard state persisted `0.01`.
- Bob confirmed the final reverted `bonks-pd` state was audible on the rig.

No `.pd` file was edited. The drift marker was removed by the real Retry flow;
the temporary Git metadata was removed from the patch tree after observation.

## Final node state

- Desired and active patch: `bonks-pd`
- Badge: `current`
- Master: `0.01`
- Helper, JACK, and PD running; PD launch context names `bonks-pd`
- Tracked runtime `patches/active_patch.txt` remains the expected dirty file
- Pre-existing untracked `patches/demo-pd/bop/` and `systemd.local-copy/`
  remain untouched

## Verification commands

The stitch-local phased Playwright driver exercised the real dashboard:

```sh
~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-4-bop000-gate.stitching/verify_fp4_bop000.py inspect
~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-4-bop000-gate.stitching/verify_fp4_bop000.py set --patch demo-pd
~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-4-bop000-gate.stitching/verify_fp4_bop000.py stale
~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-4-bop000-gate.stitching/verify_fp4_bop000.py retry
~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-4-bop000-gate.stitching/verify_fp4_bop000.py revert
~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-4-bop000-gate.stitching/verify_fp4_bop000.py git
```

The first Set action completed on the product while the new driver exposed a
Playwright `wait_for_function` argument-signature error. The driver was fixed,
compiled, and the resulting live state was inspected before continuing; Set
had reached `current` with equal identities.

Adjacent identity regression: all checks passed.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/fp-1-identity-module/verify_fp1_identity.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/fleet-patch/fp-4-bop000-gate.stitching/verify_fp4_bop000.py
git diff --check
```

## Boundaries

Bob supplied audible confirmation for the final `bonks-pd` state. Audible
output was not separately recorded or measured during the intermediate
`demo-pd` Set/Retry state. Browser behavior was checked in headless Chromium,
not on iPad/touch.
