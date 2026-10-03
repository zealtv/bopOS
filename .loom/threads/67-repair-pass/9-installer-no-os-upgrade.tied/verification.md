# Installer OS-upgrade removal — verification

2026-10-03. Bob's ruling in `75-bob-rulings` authorizes removal of the
installer-wide OS upgrade. Applied only that ruling; no other queued work was
claimed. Reread updated glean `decision-gates` and `test-rig` before working.

Removed the upgrade command from `install-device.sh` and the manual fallback
in `docs/INSTALL.md`. Installer diff is one deleted line: package-index refresh,
both named-package install commands, locale setup, Python dependencies,
provisioning and reboot remain unchanged. Replaced the obsolete
awaiting-approval paragraph in the Python pin documentation with the approved
policy. Documented whole-OS upgrades as separate bench maintenance: record the
image/package versions and re-check audio/peripherals on the device used.

## Checks

```sh
bash -n install-device.sh
~/.venvs/bopos/bin/python -B tests/test_device_install.py
git grep -n "apt-get upgrade\|apt upgrade"
./tools/run-tests.sh fast
git diff --check
```

- Shell syntax: pass.
- Existing focused installer tests: **6 passed**.
- Search: no upgrade command remains in executable installation steps. The
  only public installation-guide match is the deliberate bench-maintenance
  note. Remaining dotdir matches are preserved historical records or current
  bench-access guidance prohibiting unapproved OS upgrades; those prohibitions
  remain in force.
- Fast tier: **375 tests passed**, exit 0. Log:
  `/tmp/bopos-installer-no-os-upgrade-fast.log`.
- Whitespace check: pass.

No device contacted, installer executed, packages changed or hardware check
claimed. Browser verification is not needed for this installer/docs change.
