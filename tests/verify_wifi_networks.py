"""Real dashboard + two physical-protocol peers: Wi-Fi authoring and redaction."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import uuid

from playwright.sync_api import sync_playwright
from pythonosc.osc_message import OscMessage
from verify_log_destination import (PhysicalPeer, UID, free_port, physical_host,
                                    wait_http, stop, write_fixture, ROOT)
from project_fixture import data_root

sys.path.insert(0, str(ROOT))
from python import wifi_config

UIDS = [UID, "02:53:49:4d:00:02"]
SCRATCH = Path("/private/tmp/claude-502/-Users-bob-repos-bopOS/eb6fbb68-c7f7-4a02-aeed-7744c61ade65/scratchpad")


class WifiPeers(PhysicalPeer):
    def __init__(self, *args):
        super().__init__(*args)
        self.wifi = {uid: {"managed": True, "country": "GB", "active": "imager-net",
                           "networks": [], "unmanaged": ["imager-net"]} for uid in UIDS}

    def heartbeat(self):
        for index, uid in enumerate(UIDS):
            self.send("/hb", uid, index, "physical-test", 1)

    def report(self, uid=UID):
        self.send("/os/report", json.dumps({"uid": uid, "hostname": "wifi-peer",
                                           "patch": "alpha", "wifi": self.wifi[uid]}))

    def handle(self, datagram):
        message = OscMessage(datagram)
        args = message.params
        if message.address == "/all/os/to" and len(args) >= 2 and args[0] in UIDS:
            uid, verb = args[:2]
            if verb == "report":
                self.report(uid); return
            if verb == "wifi-config" and len(args) == 3:
                current = self.wifi[uid]
                known = {row["ssid"] for row in current["networks"] if row["secret"]} | set(current["unmanaged"])
                try:
                    config = wifi_config.validate(json.loads(args[2]), known)
                    metadata = wifi_config.metadata(config)
                    names = {row["ssid"] for row in metadata["networks"]}
                    self.wifi[uid] = {"managed": True, "country": metadata["country"],
                                      "active": next(row["ssid"] for row in metadata["networks"] if row["enabled"]),
                                      "networks": [dict(row, secret=True) for row in metadata["networks"]],
                                      "unmanaged": [name for name in current["unmanaged"] if name not in names]}
                    status, phase = "ok", "applied"
                except ValueError:
                    status, phase = "err", "invalid"
                with self.lock:
                    # Retain only whether each secret travelled, never its value.
                    self.frames.append((uid, [row["psk"] is not None for row in json.loads(args[2])["networks"]]))
                self.send("/os/wifi-config", uid, status, phase, json.dumps(self.wifi[uid]))
                return
        super().handle(datagram)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-wifi-") as root:
        patches, assets, state, manifest = write_fixture(root)
        host = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM, host)
        base = f"http://127.0.0.1:{http_port}"
        log_path = Path(root) / "dashboard.log"
        secret = "wifi-" + uuid.uuid4().hex
        peer = WifiPeers(host, command_port, report_port, manifest)
        with log_path.open("w") as output:
            dashboard = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard/server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(report_port), "--send-port", str(command_port),
                "--osc-target", host, "--data-dir", data_root(str(state)),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base,
            ], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            try:
                peer.start(); wait_http(base, dashboard)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    errors, inbound = [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("websocket", lambda ws: ws.on("framereceived", lambda frame: inbound.append(frame)))
                    page.goto(base + "#devices")
                    page.wait_for_function("uids => uids.every(uid => installation.devices?.[uid]?.online)", arg=UIDS)
                    for uid in UIDS: peer.report(uid)
                    page.wait_for_function("uids => uids.every(uid => installation.devices?.[uid]?.report?.wifi?.managed)", arg=UIDS)
                    assert page.locator("#wifi-send").is_disabled()
                    assert page.locator("#wifi-add").inner_text() == "+ Add network"
                    for uid in UIDS:
                        card = page.locator(f'#device-roster .wifi-device-card:has(.device-row[data-uid="{uid}"])')
                        assert card.locator('[data-wifi-adopt="imager-net"]').count() == 1
                        assert card.locator('button button').count() == 0
                    for name in ("workshop", "fallback"):
                        page.locator("#wifi-add").click()
                        row = page.locator(".wifi-network").last
                        row.locator('[data-field="ssid"]').fill(name)
                        row.locator('[data-field="psk"]').fill(secret)
                        row.locator('[data-field="hidden"]').check()
                    page.locator("#wifi-country").select_option("AU")
                    page.locator("#wifi-send").click()
                    page.wait_for_selector("#wifi-confirm[open]")
                    expected = "⚠ This sends 2 passphrases over the network. Anything on this network right now can read them. Send only on your own network."
                    assert page.locator("#wifi-confirm-warning").inner_text() == expected
                    assert not any(isinstance(frame[1], list) for frame in peer.snapshot() if len(frame) == 2 and frame[0] in UIDS)
                    SCRATCH.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(SCRATCH / "wifi-warning.png"))
                    page.locator('#wifi-confirm button[value="send"]').click()
                    page.wait_for_function("uids => uids.every(uid => installation.devices[uid].wifi_sync === 'in sync')", arg=UIDS)
                    page.wait_for_function("Array.from(document.querySelectorAll('[data-field=psk]')).every(input => input.value === '' && input.placeholder === 'secret set')")
                    page.screenshot(path=str(SCRATCH / "wifi-panel.png"))
                    assert page.locator('#device-roster [data-wifi-sync]').all_text_contents() == ["in sync", "in sync"]
                    # One changed network across both peers uses the singular.
                    page.locator('.wifi-network [data-field="psk"]').first.fill(secret + "2")
                    page.locator("#wifi-send").click()
                    page.wait_for_selector("#wifi-confirm[open]")
                    assert page.locator("#wifi-confirm-warning").inner_text() == expected.replace("2 passphrases", "1 passphrase")
                    page.locator('#wifi-confirm button[value="send"]').click()
                    page.wait_for_function("uids => uids.every(uid => installation.devices[uid].wifi_sync === 'in sync')", arg=UIDS)
                    page.wait_for_function("Array.from(document.querySelectorAll('[data-field=psk]')).every(input => input.value === '')")
                    # Reorder uses keep-secret and requires no warning confirmation.
                    peer.clear()
                    page.locator(".wifi-network").nth(1).locator('[data-move="-1"]').click()
                    assert page.locator('.wifi-network [data-field="ssid"]').first.input_value() == "fallback"
                    page.locator("#wifi-send").click()
                    page.wait_for_function("uids => uids.every(uid => installation.devices[uid].report.wifi.active === 'fallback' && installation.devices[uid].wifi_sync === 'in sync')", arg=UIDS)
                    assert not page.locator("#wifi-confirm").is_visible()
                    # Disable the active SSID: warning, fallback, no passphrases.
                    page.locator(".wifi-network").first.locator('[data-field="enabled"]').uncheck()
                    assert page.locator("#wifi-warning").inner_text() == "⚠ 2 devices are on fallback now; they'll move to the next enabled network they can see"
                    page.locator("#wifi-send").click()
                    page.wait_for_function("uids => uids.every(uid => installation.devices[uid].report.wifi.active === 'workshop' && installation.devices[uid].wifi_sync === 'in sync')", arg=UIDS)
                    secret_frames = [frame for frame in peer.snapshot() if frame[0] in UIDS]
                    assert len(secret_frames) >= 4 and all(not any(frame[1]) for frame in secret_frames)
                    # Adopt an Imager SSID without needing to read its device secret.
                    page.locator('#device-roster [data-wifi-adopt="imager-net"]').first.click()
                    assert page.locator('.wifi-network [data-field="ssid"]').last.input_value() == "imager-net"
                    page.locator("#wifi-send").click()
                    page.wait_for_function("uids => uids.every(uid => installation.devices[uid].report.wifi.unmanaged.length === 0 && installation.devices[uid].wifi_sync === 'in sync')", arg=UIDS)
                    for checkbox in page.locator('.wifi-network [data-field="enabled"]').all(): checkbox.uncheck()
                    assert page.locator("#wifi-send").is_disabled()
                    assert not errors, errors
                    assert all(secret not in str(frame) for frame in inbound)
                    assert secret not in page.evaluate("JSON.stringify(installation)")
                    browser.close()
                secret_file = Path(data_root(str(state))) / "state/wifi-secrets.json"
                assert secret in secret_file.read_text()
                assert secret_file.stat().st_mode & 0o777 == 0o600
                for file in Path(root).rglob("*"):
                    if file.is_file() and file != secret_file:
                        assert secret.encode() not in file.read_bytes(), str(file)
                # Search the repository (including ignored runtime files), not just Git.
                result = subprocess.run(["rg", "--hidden", "--no-ignore", "-l", "-F", "-f", "-", str(ROOT)],
                                        input=secret + "\n", capture_output=True, text=True)
                assert result.returncode == 1, "test passphrase found in repository"
                print("PASS: edit, reorder, disable warning, passphrase confirmation, send, chips, unmanaged adoption, redaction; no browser errors")
                print("Screenshots: " + str(SCRATCH / "wifi-panel.png") + ", " + str(SCRATCH / "wifi-warning.png"))
            finally:
                peer.close(); stop(dashboard)


if __name__ == "__main__":
    main()
