#!/usr/bin/env python3
"""Helper, simulator, and Dashboard verification for alias-derived hostname."""

import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
MUTE_VERIFY = ROOT / ".loom" / "tied" / "12-dashboard-live-controls"
sys.path.insert(0, str(MUTE_VERIFY))
import verify_device_mute_protocol as protocol  # noqa: E402
import bopos  # noqa: E402
from verify_live_controls_browser import free_port, make_fixture, stop, wait_http  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def helper_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-hostname-helper-") as root:
        node = protocol.Node(root, "node-b")
        original_run = bopos.subprocess.run
        original_hostname = bopos.socket.gethostname
        calls = []
        bopos.socket.gethostname = lambda: "old-host"
        bopos.subprocess.run = lambda command, **kwargs: (
            calls.append((command, kwargs)) or SimpleNamespace(returncode=0))
        try:
            reply = protocol.ReplySocket()
            handled = bopos.set_device_hostname("finn-jet", reply, "10.0.0.8", node)
            check("node uses narrow non-interactive privileged helper",
                  handled and calls[0][0] == [
                      "sudo", "-n", "/usr/local/sbin/bopos-set-hostname", "finn-jet"]
                  and calls[0][1]["stdin"] is subprocess.DEVNULL,
                  repr(calls))
            check("successful node action returns attributable terminal receipt",
                  reply.calls == [(["/os/hostname", ",sss", "node-b", "finn-jet", "ok"],
                                   ("10.0.0.8", 5550))], repr(reply.calls))

            calls.clear()
            invalid = protocol.ReplySocket()
            check("invalid hostname is rejected before privilege boundary",
                  not bopos.set_device_hostname("Finn Jet", invalid, "10.0.0.8", node)
                  and not calls and not invalid.calls)

            bopos.subprocess.run = lambda _command, **_kwargs: SimpleNamespace(returncode=1)
            failed = protocol.ReplySocket()
            handled = bopos.set_device_hostname("finn-jet", failed, "10.0.0.8", node)
            check("missing authorization returns err rather than false success",
                  handled and failed.calls[0][0]
                  == ["/os/hostname", ",sss", "node-b", "finn-jet", "err"],
                  repr(failed.calls))
        finally:
            bopos.subprocess.run = original_run
            bopos.socket.gethostname = original_hostname


def browser_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-hostname-browser-") as root:
        patches, assets, state_dir, manifest_path, state_path, uids = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard" / "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(send_port),
            "--osc-target", "127.0.0.1", "--state-file", str(state_path),
            "--assets-dir", str(assets), "--patches-dir", str(patches),
            "--public-url", base_url,
        ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = None
        try:
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1024, "height": 768})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 2")
                page.click("#tab-button-devices")
                page.locator(f'#device-roster .device-row[data-uid="{uids[0]}"]').click()
                page.wait_for_selector("#device-alias")
                original_other = page.evaluate("uid => installation.devices[uid].hostname", uids[1])
                page.fill("#device-alias", "Finn Jet")
                page.click("#device-alias-save")
                page.wait_for_function(
                    "uid => installation.device_registry[uid]?.alias === 'Finn Jet'", arg=uids[0])
                hostname_button = page.locator("#device-hostname-set")
                check("Set hostname is derived from current alias and enabled online",
                      hostname_button.text_content() == "Set hostname"
                      and not hostname_button.is_disabled(),
                      f"text={hostname_button.text_content()!r}, disabled={hostname_button.is_disabled()}, "
                      f"device={page.evaluate('uid => installation.devices[uid]', uids[0])!r}")
                page.click("#device-hostname-set")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.hostname === 'finn-jet' && "
                    "installation.devices[uid]?.hostname_status === 'ok'", arg=uids[0])
                check("Dashboard exact-UID action applies lowercase hyphenated hostname",
                      hostname_button.text_content() == "Hostname set"
                      and hostname_button.is_disabled(),
                      f"text={hostname_button.text_content()!r}, disabled={hostname_button.is_disabled()}, "
                      f"device={page.evaluate('uid => installation.devices[uid]', uids[0])!r}")
                check("hostname action does not touch another physical device",
                      page.evaluate("uid => installation.devices[uid].hostname", uids[1])
                      == original_other)
                stored = json.loads(Path(state_dir, uids[0].replace(":", "-") + ".json").read_text())
                check("simulator persists hostname independently of Seat identity",
                      stored["name"] == "finn-jet" and stored["id"] == 1,
                      repr(stored))
                page.screenshot(
                    path=str(Path(__file__).resolve().parent / "alias-hostname-action.png"),
                    full_page=True)
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)


def static_provisioning_checks():
    helper = (ROOT / "systemd" / "bopos-set-hostname").read_text(encoding="utf-8")
    sudoers = (ROOT / "systemd" / "bopos-power.sudoers").read_text(encoding="utf-8")
    provision = (ROOT / "bash" / "provision.sh").read_text(encoding="utf-8")
    check("provisioning installs one validating root-owned hostname helper",
          "^[a-z0-9]" in helper and "/usr/bin/hostnamectl set-hostname" in helper
          and "/usr/local/sbin/bopos-set-hostname *" in sudoers
          and "-m 0755" in provision and "bopos-set-hostname" in provision)


def main():
    helper_checks()
    browser_checks()
    static_provisioning_checks()
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
