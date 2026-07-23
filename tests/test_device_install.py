#!/usr/bin/env python3
"""Durable checks for the Raspberry Pi device installation surface."""

import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]


class DeviceInstallTests(unittest.TestCase):
    def read(self, relative_path):
        return (REPO / relative_path).read_text()

    def test_install_entry_points_are_explicit_and_parse(self):
        scripts = ("install-dashboard.sh", "install-device.sh")
        self.assertFalse((REPO / "install.sh").exists())
        for script in scripts:
            path = REPO / script
            self.assertTrue(path.exists(), script)
            subprocess.run(["bash", "-n", str(path)], check=True)

    def test_readme_device_command_uses_the_github_script(self):
        readme = self.read("README.md")
        self.assertIn(
            "https://raw.githubusercontent.com/zealtv/bopOS/main/install-device.sh"
            " | env LANG=C LC_ALL=C bash",
            readme,
        )

    def test_device_install_composes_existing_provisioning(self):
        installer = self.read("install-device.sh")
        self.assertIn('sudo "$BOPOS_DIR/bash/provision.sh"', installer)
        self.assertIn('"$VENV/bin/pip" install -r', installer)
        self.assertIn("git clone", installer)
        self.assertIn("git -C \"$BOPOS_DIR\" pull --ff-only", installer)
        self.assertTrue(installer.rstrip().endswith("sudo systemctl reboot"))

    def test_device_install_generates_a_configurable_locale(self):
        installer = self.read("install-device.sh")
        self.assertIn('DEVICE_LOCALE="${BOPOS_LOCALE:-en_AU.UTF-8}"', installer)
        self.assertIn(
            'raspi-config nonint do_change_locale "$DEVICE_LOCALE"', installer
        )
        self.assertIn(
            'update-locale LANG="$DEVICE_LOCALE" LC_ALL LANGUAGE', installer
        )

    def test_provisioning_preserves_config_and_enables_systemd(self):
        provision = self.read("bash/provision.sh")
        self.assertIn('if [ ! -e "$CONFIG_FILE" ]', provision)
        self.assertIn("systemctl enable bopos.service", provision)
        self.assertNotIn(
            'install -o root -g root -m 0755 "$SCRIPT_DIR/rc.local" /etc/rc.local',
            provision,
        )

        service = self.read("systemd/bopos.service")
        self.assertIn("ExecStart=/home/pi/bopOS/bash/start.sh", service)
        self.assertIn("ExecStop=/home/pi/bopOS/bash/stop.sh", service)
        self.assertIn("Restart=on-failure", service)
        self.assertIn("LimitMEMLOCK=infinity", service)
        self.assertIn("LimitRTPRIO=95", service)

    def test_audio_start_reads_device_config_and_waits_for_card(self):
        start = self.read("bash/start-engine.sh")
        self.assertIn('source "$BOPOS_DIR/bopos.config"', start)
        self.assertIn('grep -F "$SOUNDCARD" /proc/asound/cards', start)
        self.assertIn("BOPOS_AUDIO_WAIT_TIMEOUT", start)
        self.assertIn(
            'export JACK_NO_AUDIO_RESERVATION="${JACK_NO_AUDIO_RESERVATION:-1}"',
            start,
        )


if __name__ == "__main__":
    unittest.main()
