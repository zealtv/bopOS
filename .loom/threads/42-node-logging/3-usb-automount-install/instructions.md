# 3-usb-automount-install

USB auto-mount as a provisioning step. Ratified design:
`../1-logging-seed-design` (tied) — this stitch implements the mechanism
exactly as ratified.

## Build

- **udev rule + systemd template unit** (bopOS-owned, e.g.
  `bash/` sources installed to `/etc/udev/rules.d/` +
  `/etc/systemd/system/`):
  - match USB block partitions (`ID_BUS=usb`), start `bopos-usb@.service`;
  - mount the **first partition of one stick** at the stable path
    **`/media/bopos-usb`**; multi-stick is unsupported by design;
  - filesystem auto-detect (vfat/exfat/ext4); FAT-family mounted with the
    bopos user's uid/gid (unprivileged runtime writes) and `flush`-leaning
    options so a yanked stick costs at worst a truncated last line;
  - unmount on removal via the unit's stop path; yank-without-eject is the
    expected user behaviour and must be safe.
- **`install-device.sh` step** — net-new, idempotent, sudo at install time
  only (thread 31 is tied; do not assume it carries this). Existing devices
  need one re-run of the install/provision step — say so in the README
  line you touch.
- **Discovery contract:** consumers (nodelog, stitch 4) find the mount by
  `os.path.ismount("/media/bopos-usb")` — no udev listening in bopos.py.

## Verify

Software-side: rule/unit syntax, install idempotency (run twice, no
change), and a lint-level check the unit mounts to the ratified path.
Real stick insert/remove/yank on a Pi is a **hardware adoption check**
(Ciro Toast is the standalone rig — `finn-ciro-test-rig` memory); state it
in the stitch rather than claiming it verified.
