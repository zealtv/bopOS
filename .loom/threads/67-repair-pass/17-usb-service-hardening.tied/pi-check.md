# Pi adoption checks — pending Bob

Software fixtures passed; no Pi, real installer, sudo, systemd, udev or mount
operation was run for this stitch.

- Remove USB sticks before adopting the changed installer/unit; start from a
  clean mount state (reboot after provisioning). An already-active mount from
  the old helper has no ownership record for the new helper.
- Provision on the Pi and confirm `/usr/local/sbin/bopos-usb-mount` and its
  parent directory are root-owned and not writable by pi. The helper must be
  mode 0755; both USB unit commands must use it, with the partition instance
  on both mount and unmount. Reprovision and check ownership/mode again.
- Confirm the Pi has `flock`, and `/run/bopos-usb.lock` and
  `/run/bopos-usb.owner` are root-owned with no pi write permission.
- Insert A: confirm `/media/bopos-usb` mounts, ownership records its partition,
  and node logging writes there. Insert B: confirm it is ignored. Remove B:
  A must stay mounted and logging must continue. Then yank A: the mount and
  ownership record must clear. Insert another stick and confirm it mounts.
- Repeat with a multi-partition stick and near-simultaneous arrivals/removals;
  only the owning partition's removal may unmount the stable path.
- Check supported FAT/exFAT and native filesystem behavior, including the
  existing flush/sync options and pi write access. Review the USB unit journal
  for failures, and confirm lazy unmount recovers a yanked device.
