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
import os
import subprocess
import sys
import tempfile
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
        self.assertIn("ExecStart=/usr/local/sbin/bopos-usb-mount mount %I", text)
        self.assertIn("ExecStop=/usr/local/sbin/bopos-usb-mount unmount %I", text)
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


class UsbFixturesTest(unittest.TestCase):
    """Execute copied scripts with temporary paths and inert system commands."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-usb-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
        self.mounted = self.root / "mounted"
        self.owner = self.root / "owner"
        self.lock = self.root / "lock"
        self.calls = self.root / "calls"

    def script(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o755)

    def python_stub(self, name, body):
        self.script(self.bin / name, f"#!{sys.executable}\n" + body)

    def helper(self):
        text = HELPER.read_text()
        for original, replacement in (
            ('PATH=/usr/sbin:/usr/bin:/sbin:/bin', f'PATH="{self.env["PATH"]}"'),
            ('MOUNT_POINT="/media/bopos-usb"', f'MOUNT_POINT="{self.root}/mount"'),
            ('OWNER_FILE="/run/bopos-usb.owner"', f'OWNER_FILE="{self.owner}"'),
            ('LOCK_FILE="/run/bopos-usb.lock"', f'LOCK_FILE="{self.lock}"'),
            ('local dev="/dev/${devname}"', f'local dev="{self.root}/${{devname}}"'),
            ('[ ! -b "$dev" ]', '[ ! -f "$dev" ]'),
        ):
            text = text.replace(original, replacement)
        self.script(self.root / "helper", text)
        for dev in ("sda1", "sdb1"):
            (self.root / dev).touch()
        self.python_stub("flock", "import fcntl, sys\nfcntl.flock(int(sys.argv[1]), fcntl.LOCK_EX)\n")
        self.script(self.bin / "mountpoint", f'#!/bin/bash\ntest -f "{self.mounted}"\n')
        self.script(self.bin / "blkid", '#!/bin/bash\necho vfat\n')
        self.script(self.bin / "id", '#!/bin/bash\necho 1000\n')
        # Every mount/unmount must hold the same real advisory lock. macOS has
        # no flock CLI, so the fixture implements that command using fcntl.
        check_lock = (
            "import fcntl, pathlib, sys\n"
            f"lock = open({str(self.lock)!r}, 'a')\n"
            "try:\n    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "except BlockingIOError:\n    pass\n"
            "else:\n    sys.exit('mount operation ran without the lock')\n"
        )
        self.python_stub("mount", check_lock +
                         "import time\ntime.sleep(0.05)\n" +
                         f"with open({str(self.calls)!r}, 'a') as log: log.write('mount\\n')\n" +
                         f"pathlib.Path({str(self.mounted)!r}).write_text(sys.argv[-2])\n")
        self.python_stub("umount", check_lock +
                         f"pathlib.Path({str(self.mounted)!r}).unlink()\n")

    def invoke(self, *args, check=True):
        return subprocess.run(["bash", str(self.root / "helper"), *args],
                              env=self.env, capture_output=True, text=True, check=check)

    def test_ignored_partition_stop_preserves_mount_owner(self):
        self.helper()
        self.invoke("mount", "sda1")
        self.invoke("mount", "sdb1")
        self.invoke("unmount", "sdb1")
        self.assertEqual(self.mounted.read_text(), str(self.root / "sda1"))
        self.assertEqual(self.owner.read_text().strip(), "sda1")
        # A yank removes the device node before ExecStop runs.
        (self.root / "sda1").unlink()
        self.invoke("unmount", "sda1")
        self.assertFalse(self.mounted.exists())
        self.assertFalse(self.owner.exists())

    def test_failed_mount_never_claims_ownership(self):
        self.helper()
        self.script(self.bin / "mount", '#!/bin/bash\nexit 32\n')
        self.assertNotEqual(self.invoke("mount", "sda1", check=False).returncode, 0)
        self.assertFalse(self.owner.exists())

    def test_competing_arrivals_mount_only_once(self):
        self.helper()
        processes = [subprocess.Popen(
            ["bash", str(self.root / "helper"), "mount", dev], env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for dev in ("sda1", "sdb1")]
        for process in processes:
            output, error = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, output + error)
        owner = self.owner.read_text().strip()
        self.assertEqual(self.mounted.read_text(), str(self.root / owner))
        self.assertEqual(self.calls.read_text(), "mount\n")
        ignored = "sdb1" if owner == "sda1" else "sda1"
        self.invoke("unmount", ignored)
        self.assertTrue(self.mounted.exists())
        self.invoke("unmount", owner)
        self.assertFalse(self.mounted.exists())

    def test_failed_unmount_retains_ownership_for_retry(self):
        self.helper()
        self.invoke("mount", "sda1")
        self.script(self.bin / "umount", '#!/bin/bash\nexit 32\n')
        self.assertNotEqual(self.invoke("unmount", "sda1", check=False).returncode, 0)
        self.assertTrue(self.mounted.exists())
        self.assertEqual(self.owner.read_text().strip(), "sda1")

    def test_unmount_requires_instance(self):
        self.helper()
        self.assertEqual(self.invoke("unmount", check=False).returncode, 2)

    def test_installer_copies_root_owned_helper_and_repairs_metadata(self):
        checkout = self.root / "checkout"
        for relative in ("bash/install-usb-automount.sh", "bash/bopos-usb-mount",
                         "systemd/99-bopos-usb.rules", "systemd/bopos-usb@.service"):
            target = checkout / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((REPO / relative).read_text())
        installer = checkout / "bash/install-usb-automount.sh"
        text = installer.read_text()
        for target in ("/etc/udev/rules.d/99-bopos-usb.rules",
                       "/etc/systemd/system/bopos-usb@.service",
                       "/usr/local/sbin/bopos-usb-mount"):
            text = text.replace(target, str(self.root / "installed" / Path(target).name))
        installer.write_text(text)
        self.script(self.bin / "sudo", '#!/bin/bash\nexec "$@"\n')
        self.python_stub("install", "import pathlib, shutil, sys\n"
                         f"with open({str(self.calls)!r}, 'a') as log: log.write(' '.join(sys.argv[1:]) + '\\n')\n"
                         "assert sys.argv[1:5] == ['-o', 'root', '-g', 'root']\n"
                         "src, dst = map(pathlib.Path, sys.argv[-2:])\n"
                         "dst.parent.mkdir(parents=True, exist_ok=True)\n"
                         "shutil.copyfile(src, dst)\n"
                         "dst.chmod(int(sys.argv[6], 8))\n")
        for command in ("udevadm", "systemctl"):
            self.script(self.bin / command, '#!/bin/bash\nexit 0\n')
        def provision():
            subprocess.run(["bash", str(installer)], env=self.env,
                           capture_output=True, text=True, check=True)
        provision()
        installed = self.root / "installed/bopos-usb-mount"
        self.assertTrue(installed.exists(), "helper must be installed outside checkout")
        self.assertEqual(installed.read_text(), HELPER.read_text())
        installed.chmod(0o777)
        provision()
        self.assertEqual(installed.stat().st_mode & 0o777, 0o755)
        self.assertEqual(self.calls.read_text().count(str(installed)), 2)


if __name__ == "__main__":
    unittest.main()
