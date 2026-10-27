#!/usr/bin/env python3
"""Living tests for Wi-Fi power-save provisioning (79-wifi-power-save).

Whether power save actually reads `off` after a reboot is a hardware check
(see the stitch). What software can hold is the wiring: the NetworkManager
drop-in disables it, the boot unit runs `iw` against wlan0 and tolerates a
node without iw, and provision.sh runs the idempotent installer.
"""

import configparser
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
CONF = REPO / "systemd" / "bopos-wifi-powersave.conf"
UNIT = REPO / "systemd" / "bopos-wifi-powersave.service"
INSTALLER = REPO / "bash" / "install-wifi-powersave.sh"
PROVISION = REPO / "bash" / "provision.sh"


class WifiPowerSaveTest(unittest.TestCase):
    def test_networkmanager_dropin_disables_power_save(self):
        parser = configparser.ConfigParser()
        parser.read_string(CONF.read_text())
        # NetworkManager: 2 = disable (3 = enable, 0/1 = default/ignore).
        self.assertEqual(parser["connection"]["wifi.powersave"].strip(), "2")

    def test_boot_unit_targets_wlan0_and_tolerates_missing_iw(self):
        parser = configparser.ConfigParser(strict=False, interpolation=None)
        parser.read_string(UNIT.read_text())
        self.assertEqual(parser["Unit"]["BindsTo"], "sys-subsystem-net-devices-wlan0.device")
        self.assertEqual(parser["Install"]["WantedBy"], "sys-subsystem-net-devices-wlan0.device")
        start = parser["Service"]["ExecStart"]
        self.assertIn("iw dev wlan0 set power_save off", start)
        self.assertIn("command -v iw", start)

    def test_installer_is_executable_valid_and_installs_both(self):
        self.assertTrue(INSTALLER.stat().st_mode & 0o111)
        result = subprocess.run(["bash", "-n", str(INSTALLER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = INSTALLER.read_text()
        self.assertIn("/etc/NetworkManager/conf.d/bopos-wifi-powersave.conf", text)
        self.assertIn("/etc/systemd/system/bopos-wifi-powersave.service", text)
        self.assertIn("systemctl enable bopos-wifi-powersave.service", text)

    def test_provision_runs_the_installer(self):
        self.assertIn('"$SCRIPT_DIR/install-wifi-powersave.sh"', PROVISION.read_text())


if __name__ == "__main__":
    unittest.main()
