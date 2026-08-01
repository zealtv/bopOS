#!/usr/bin/env python3
"""Focused Playwright check for terminal patch-switch remediation."""

import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    REPO = os.path.dirname(REPO)

FAILURES = []
RESERVED = set()


def check(label, condition):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}")
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if (kind, port) in RESERVED:
            continue
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        RESERVED.add((kind, port))
        return port
    raise RuntimeError("cannot reserve localhost port")


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before HTTP startup")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not start")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-switch-ui-") as root:
        assets, patches = os.path.join(root, "assets"), os.path.join(root, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        state_path = os.path.join(root, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "switch-ui", "fleet_patch": {
                "name": "alpha", "fingerprint": "a" * 64, "staged_at": 1,
            }, "seats": {"1": {"id": 1, "name": "Seat One",
                "positions": [[1, 1]], "params": {}, "bound": "node-ui"}}}, target)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(root, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        process = None
        try:
            process = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(command_port),
                "--state-file", state_path, "--assets-dir", assets,
                "--patches-dir", patches, "--sim-no-engine",
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, process)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.evaluate("""() => {
                  const uid='node-ui';
                  installation.devices[uid]={uid,id:1,online:true,hostname:'node-ui',
                    patches:[{name:'alpha',active:false,manifest:true,fingerprint:'a'.repeat(64)},
                             {name:'beta',active:true,manifest:true,fingerprint:'b'.repeat(64)}],
                    report:{patch:'beta'},fetch:{},patch_badge:'failed',
                    patch_switch:{patch:'alpha',status:'failed',reason:'Observed beta.'}};
                  installation.seats['1'].bound=uid;
                  selected=uid; selectedSeat=1;
                  window.__sent=[];
                  ws.send=(type,data)=>window.__sent.push({type,data});
                  activateTab('devices'); render();
                }""")
                check("failed badge and reason render in current Devices workspace",
                      page.locator("#detail .patch-badge-failed").inner_text() == "switch failed"
                      and "Observed beta." in page.locator("#patch-diagnostics").inner_text())
                check("failed terminal state exposes one-device Retry",
                      page.locator("#fleet-patch-retry").inner_text() == "Retry")
                page.click("#fleet-patch-retry")
                check("Retry sends the selected device uid",
                      page.evaluate("window.__sent") == [{
                          "type": "retry_fleet_patch", "data": {"uid": "node-ui"}}])
                page.evaluate("""() => {
                  const d=installation.devices['node-ui'];
                  d.patch_badge='timeout';
                  d.patch_switch={patch:'alpha',status:'timeout',reason:'No observation.'};
                  render();
                }""")
                check("timeout has a distinct terminal label and keeps Retry",
                      page.locator("#detail .patch-badge-timeout").inner_text() == "switch timed out"
                      and page.locator("#fleet-patch-retry").count() == 1)
                browser.close()
        finally:
            stop(process)
            log.close()
        server_log = open(log_path, encoding="utf-8").read()
        check("dashboard shuts down cleanly",
              process is not None and process.returncode in (0, -15)
              and "Application shutdown complete" in server_log)
    total = 5
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
