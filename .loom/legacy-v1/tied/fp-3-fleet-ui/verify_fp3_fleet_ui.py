#!/usr/bin/env python3
"""Playwright verification for the fp-3 fleet-wide patch dashboard surface."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright
from pythonosc.udp_client import SimpleUDPClient

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repo")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    sock = socket.socket(socket.AF_INET, kind)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def write_patch(root, name, payload):
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(payload)
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except Exception:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def main():
    with tempfile.TemporaryDirectory() as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        nodes = os.path.join(temp, "nodes")
        os.makedirs(os.path.join(assets, "samples"))
        with open(os.path.join(assets, "samples", "ping.raw"), "wb") as target:
            target.write(b"asset")
        write_patch(patches, "demo-pd", b"demo")
        write_patch(patches, "alpha", b"alpha")
        write_patch(patches, "beta", b"beta-v1")

        macs = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]
        state = {"schema": 1, "name": "fp3", "seats": {
            str(index): {"id": index, "name": f"seat-{index}",
                         "positions": [[index, 0]], "params": {}, "bound": uid}
            for index, uid in enumerate(macs, 1)}}
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(state, target)

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = os.path.join(temp, "server.log")
        fleet_log_path = os.path.join(temp, "simfleet.log")
        server_log = open(server_log_path, "w", encoding="utf-8")
        fleet_log = open(fleet_log_path, "w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(command_port),
                "--osc-target", "127.0.0.1", "--public-url", base_url,
                "--state-file", state_path, "--assets-dir", assets,
                "--patches-dir", patches, "--sim-no-engine",
                "--sim-audio-backend", "none",
                "--sim-engine-port-base", str(free_port(socket.SOCK_DGRAM)),
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--state-dir", nodes,
                "--target", "127.0.0.1", "--report-port", str(listen_port),
                "--cmd-port", str(command_port), "--hb-interval", "0.25",
                "--boot-secs", "0.2", "--fetch-seconds", "0.5",
                "--patches-dir", patches,
                "--manifest", os.path.join(patches, "demo-pd", "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1050})
                dialogs = []

                def accept_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    dialog.accept()

                page.on("dialog", accept_dialog)
                page.goto(base_url)
                page.wait_for_function(
                    "() => document.querySelectorAll('.seat-row .patch-badge').length === 2",
                    timeout=12000)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'beta')", timeout=8000)

                labels = page.evaluate("""() => {
                    const values=['unknown','switching','missing','mismatch','stale',
                                  'stale_unverified','current'];
                    return Object.fromEntries(values.map(value => {
                      const holder=document.createElement('div');
                      holder.innerHTML=patchBadge(value);
                      return [value, holder.textContent.trim()];
                    }));
                }""")
                check("all ratified badge states render with operator-facing labels",
                      labels == {"unknown": "unknown / last seen", "switching": "switching",
                                 "missing": "missing", "mismatch": "mismatch",
                                 "stale": "stale", "stale_unverified": "stale (unverified)",
                                 "current": "current"}, repr(labels))
                check("fleet selector is global rather than inside device detail",
                      page.locator("#fleet-patch-panel #patch-select").count() == 1
                      and page.locator("#detail #patch-select").count() == 0)

                page.select_option("#patch-select", "beta")
                page.click("#patch-switch")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('2 current')",
                    timeout=15000)
                check("Set fleet patch is confirmation-gated",
                      any(kind == "confirm" and 'Set "beta"' in message
                          for kind, message in dialogs), repr(dialogs))
                check("one selector converges the whole assigned fleet",
                      page.locator(".seat-row .patch-badge-current").count() == 2
                      and page.locator("#patch-select").input_value() == "beta",
                      page.locator("#fleet-patch-summary").inner_text())

                page.locator(".seat-row .dot").first.click()
                page.wait_for_selector("#patch-diagnostics")
                detail = page.locator("#detail").inner_text()
                check("device detail exposes observed patch identity diagnostics",
                      "Desired fleet patch" in detail and "beta" in detail
                      and "Reported content identity" in detail
                      and "Fingerprint / content identity" in detail, detail)
                check("ordinary device detail has no per-device patch authoring controls",
                      page.locator("#detail #patch-select, #detail #patch-switch").count() == 0
                      and "Send patch" not in detail)
                check("asset Send and Sync remain device-addressable",
                      page.locator("#distribution [data-kind='asset'] [data-send]").count() == 1
                      and "sync all assets" in page.locator("#distribution").inner_text().lower())
                page.locator("#distribution [data-kind='asset'] [data-send]").click()
                page.wait_for_function(
                    "() => document.querySelector(\"#distribution [data-kind='asset'] .sync-status\")?.innerText === 'in sync'",
                    timeout=8000)
                check("asset Send still converges independently", True)

                with open(os.path.join(patches, "beta", "main.bin"), "wb") as target:
                    target.write(b"beta-v2-with-different-content")
                page.click("#refresh-distribution")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('2 stale')",
                    timeout=8000)
                detail = page.locator("#patch-diagnostics").inner_text()
                identities = page.locator("#patch-diagnostics dl dd code").all_inner_texts()
                check("host content drift renders stale badges and distinct identities",
                      page.locator(".seat-row .patch-badge-stale").count() == 2
                      and "Retry" in detail and len(identities) >= 2
                      and identities[0] != identities[1],
                      page.locator("#fleet-patch-summary").inner_text()
                      + "\n" + repr(identities) + "\n" + detail)
                page.click("#fleet-patch-retry")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('1 current')",
                    timeout=12000)
                check("row Retry remediates one stale node without a per-device choice",
                      page.locator(".seat-row .patch-badge-current").count() == 1
                      and page.locator(".seat-row .patch-badge-stale").count() == 1)
                page.locator(".seat-row .dot").nth(1).click()
                page.click("#fleet-patch-retry")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('2 current')",
                    timeout=12000)

                SimpleUDPClient("127.0.0.1", command_port).send_message(
                    "/1/os/patch", "demo-pd")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('1 mismatch')",
                    timeout=10000)
                page.locator(".seat-row:has(.patch-badge-mismatch) .dot").click()
                check("wrong active name renders mismatch with Re-switch remediation",
                      page.locator("#fleet-patch-retry").inner_text().lower() == "re-switch")
                page.click("#fleet-patch-retry")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('2 current')",
                    timeout=10000)

                page.select_option("#patch-select", "alpha")
                page.click("#patch-switch")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'alpha'"
                    " && document.querySelector('#fleet-patch-summary')?.innerText.includes('2 current')",
                    timeout=15000)
                check("a second fleet choice enables Revert",
                      not page.locator("#fleet-patch-revert").is_disabled())
                page.click("#fleet-patch-revert")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'beta'"
                    " && document.querySelector('#fleet-patch-summary')?.innerText.includes('2 current')",
                    timeout=15000)
                check("Revert restores the previous fleet patch through convergence",
                      any(kind == "confirm" and "Revert the fleet" in message
                          for kind, message in dialogs), repr(dialogs))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            fleet_log.close()
            server_log.close()
            if server is not None and server.returncode not in (0, -15):
                with open(server_log_path, encoding="utf-8") as source:
                    print("\n--- dashboard log ---\n" + source.read())
            if fleet is not None and fleet.returncode not in (0, -15):
                with open(fleet_log_path, encoding="utf-8") as source:
                    print("\n--- simfleet log ---\n" + source.read())

    total = 13
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
