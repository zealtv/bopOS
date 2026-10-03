# 9-installer-no-os-upgrade

**Status:** ready · small · Bob ruled 2026-10-03 ("yes")
**Goal:** installing bopOS on a device doesn't upgrade the whole OS.

Remove `apt-get upgrade -y` from `install-device.sh` and from the manual
install instructions (`docs/INSTALL.md` and anywhere else it's documented).
Keep `apt-get update` and installing the named packages. Say in
`docs/INSTALL.md` that OS upgrades are deliberate bench maintenance (record
the image and package versions, re-check audio and peripherals after).
Background: `.loom/tied/73-pinned-dependencies/os-upgrade-recommendation.md`.

## Done when

- `git grep -n "apt-get upgrade\|apt upgrade"` finds only history and the
  bench-maintenance note.
- Fast tier green. Not run on a device (no device install is claimed).
