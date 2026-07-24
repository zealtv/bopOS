#!/usr/bin/env python3
"""Living tests for USB auto-mount provisioning (thread 42-node-logging).

The real insert/remove/yank behaviour is a hardware adoption check (Ciro
Toast). What is durable and checkable in software is the ratified contract
between the udev rule, the systemd template unit, the mount helper, and the
provisioning wiring: the stable mount path `/media/bopos-usb`, the rule that
starts the unit for a USB partition, the unit that binds to its device and
calls the helper, the helper's filesystem handling, and the idempotent
installer that provision.sh invokes.
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
MOUNT_POINT = "/media/bopos-usb"

RULE = REPO / "systemd" / "99-bopos-usb.rules"
UNIT = REPO / "systemd" / "bopos-usb@.service"
HELPER = REPO / "bash" / "bopos-usb-mount"
INSTALLER = REPO / "bash" / "install-usb-automount.sh"
PROVISION = REPO / "bash" / "provision.sh"


class UsbAutomountSourcesTest(unittest.TestCase):
    def test_all_sources_present_and_executable(self):
        for path in (RULE, UNIT, HELPER, INSTALLER, PROVISION):
            self.assertTrue(path.exists(), path)
        # scripts the unit / provision.sh invoke must be executable in the repo
        for path in (HELPER, INSTALLER):
            self.assertTrue(path.stat().st_mode & 0o111, "not executable: " + str(path))

    def test_scripts_pass_bash_syntax_check(self):
        for path in (HELPER, INSTALLER):
            result = subprocess.run(["bash", "-n", str(path)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_udev_rule_matches_usb_partition_and_starts_unit(self):
        text = RULE.read_text()
        self.assertIn('ACTION=="add"', text)
        self.assertIn('SUBSYSTEM=="block"', text)
        self.assertIn('ENV{ID_BUS}=="usb"', text)
        # partitions (trailing digit), not whole disks
        self.assertRegex(text, r'KERNEL=="sd\[a-z\]\[0-9\]"')
        # ties the .device unit to the templated service (removal => stop)
        self.assertIn('TAG+="systemd"', text)
        self.assertIn('ENV{SYSTEMD_WANTS}+="bopos-usb@%k.service"', text)

    def test_unit_binds_device_and_mounts_to_ratified_path(self):
        text = UNIT.read_text()
        self.assertIn("BindsTo=dev-%i.device", text)
        self.assertIn("ExecStart=/home/pi/bopOS/bash/bopos-usb-mount mount %I", text)
        self.assertIn("ExecStop=/home/pi/bopOS/bash/bopos-usb-mount unmount", text)
        self.assertIn("RemainAfterExit=yes", text)

    def test_helper_mounts_ratified_path_and_handles_filesystems(self):
        text = HELPER.read_text()
        self.assertIn('MOUNT_POINT="{}"'.format(MOUNT_POINT), text)
        # FAT-family mapped to the bopos user with flush; native fs sync-leaning
        self.assertIn("uid=${uid},gid=${gid},flush", text)
        for fstype in ("vfat", "exfat", "ext4"):
            self.assertIn(fstype, text)
        # one-stick guard and a removal/unmount path
        self.assertIn('mountpoint -q "$MOUNT_POINT"', text)
        self.assertIn("umount", text)

    def test_installer_is_idempotent_and_targets_system_paths(self):
        text = INSTALLER.read_text()
        self.assertIn("/etc/udev/rules.d/99-bopos-usb.rules", text)
        self.assertIn("/etc/systemd/system/bopos-usb@.service", text)
        # idempotency: install guarded by cmp, reload only when something changed
        self.assertIn("cmp -s", text)
        self.assertIn("udevadm control --reload-rules", text)
        self.assertIn("systemctl daemon-reload", text)
        self.assertRegex(text, r'if \[ "\$changed" -eq 1 \]')

    def test_provision_invokes_the_installer(self):
        self.assertIn("install-usb-automount.sh", PROVISION.read_text())

    def test_ratified_mount_path_is_consistent_everywhere(self):
        # The path the node will discover by os.path.ismount (stitch 4) must be
        # exactly the one the helper mounts and the docs promise.
        self.assertIn(MOUNT_POINT, HELPER.read_text())
        self.assertIn(MOUNT_POINT, (REPO / "docs" / "INSTALL.md").read_text())


if __name__ == "__main__":
    unittest.main()
