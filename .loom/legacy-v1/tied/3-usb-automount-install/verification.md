# 3-usb-automount-install — verification

USB auto-mount as a provisioning step, implemented per the ratified design
(`.loom/tied/1-logging-seed-design/` §4). bopOS-owned udev rule + systemd
template unit mounting one stick at the stable path `/media/bopos-usb`;
consumers (nodelog, stitch 4) discover it by `os.path.ismount`.

## What landed

- **`systemd/99-bopos-usb.rules`** — matches USB block partitions
  (`SUBSYSTEM==block`, `ID_BUS==usb`, `KERNEL==sd[a-z][0-9]` — partitions
  carry a trailing digit, whole disks don't) and, via `TAG+="systemd"` +
  `SYSTEMD_WANTS`, starts `bopos-usb@%k.service`. That ties the `.device`
  unit to the service so a **pull** (device node vanishes) stops the unit.
- **`systemd/bopos-usb@.service`** — oneshot, `RemainAfterExit=yes`,
  `BindsTo=dev-%i.device`; `ExecStart` mounts, `ExecStop` unmounts via the
  helper. Removal → device unit inactive → BindsTo stops this → ExecStop
  unmounts, the ratified removal path.
- **`bash/bopos-usb-mount`** — the mount/unmount helper:
  - mounts `/dev/<devname>` at `/media/bopos-usb`;
  - **one stick at a time** — an already-mounted point ignores further
    partitions/sticks (so the first partition wins);
  - filesystem auto-detect (`blkid`): FAT-family (`vfat`/`msdos`/`exfat`)
    mounted with the bopos user's uid/gid + `flush` (unprivileged writes,
    pull safety); native (`ext2/3/4`) with `sync`; unknown/none ignored,
    never fatal;
  - `unmount` is lazy-fallback so a yanked stick still frees the point.
    Yank-without-eject costs at worst a truncated last line, by design.
- **`bash/install-usb-automount.sh`** — installs the rule + unit with
  `install -o root`, **idempotent** (`cmp -s` guards each file; reload only
  `if changed`), reloads udev + systemd only on change. `as_root` no-ops
  when already root (provision.sh runs it as root).
- **`bash/provision.sh`** — now calls `install-usb-automount.sh` alongside
  the hostname helper and power-control install (the one-time privileged
  step; runtime mounting needs no privilege).
- **Docs** — `docs/INSTALL.md` provision section now states the USB
  auto-mount is installed and mounts at `/media/bopos-usb`; the existing-Pi
  note extended: predating Pis need one manual `sudo bash/provision.sh`,
  which is idempotent (installs only missing pieces).

## Verified (software)

`~/.venvs/bopos/bin/python -m unittest tests.test_usb_automount -v` — 8 pass:

- all sources present + helper/installer executable;
- `bash -n` syntax check on both scripts;
- udev rule matches a USB partition and starts the templated unit;
- unit binds its device and mounts to the ratified path via the helper;
- helper targets `/media/bopos-usb`, maps FAT uid/gid + flush, handles
  vfat/exfat/ext4, guards one-stick, has an unmount path;
- installer targets the `/etc` paths, is cmp-guarded idempotent, reloads
  only on change;
- provision.sh invokes the installer;
- the mount path is consistent across helper and docs (the path stitch 4
  discovers by `os.path.ismount`).

Full non-browser suite green: `unittest discover -s tests -p 'test_*.py'`
→ **71 pass** (63 prior + 8 new).

shellcheck is not installed on this host; `bash -n` is the available syntax
gate. `systemd-analyze verify` / `udevadm verify` need a Linux+systemd host.

## Not verified here (hardware adoption check — Ciro Toast)

Real insert / remove / **yank-without-eject** on a Pi: the actual mount at
`/media/bopos-usb`, FAT write permission for the unprivileged node, the
BindsTo-driven unmount on removal, and a true run-twice-no-change of
`sudo bash/provision.sh` on a device (needs udevadm/systemctl + root). Stated
as hardware, not claimed verified.
