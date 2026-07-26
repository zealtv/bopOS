#!/usr/bin/env python3
"""Mac installation-LAN adoption check for the Imani Silver incident."""

import json
import os
import random
import shutil
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
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

UID = "b8:27:eb:b4:64:79"
FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""), flush=True)
    if not condition:
        FAILURES.append(label)


def free_tcp_port():
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port
    raise RuntimeError("cannot reserve HTTP port")


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    real_state = os.path.join(REPO, "dashboard", "installation.json")
    if not os.path.isfile(real_state):
        raise SystemExit("dashboard/installation.json is required for the safe binding replay")
    with tempfile.TemporaryDirectory(prefix="bopos-imani-adoption-") as temp:
        state_path = os.path.join(temp, "installation.json")
        shutil.copy2(real_state, state_path)
        http_port = free_tcp_port()
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(temp, "server.log")
        process = None
        with open(log_path, "w", encoding="utf-8") as server_log:
            try:
                # Deliberately omit --osc-target: this is the regression gate.
                process = subprocess.Popen([
                    sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                    "--host", "127.0.0.1", "--port", str(http_port),
                    "--state-file", state_path,
                ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
                wait_http(base_url, process)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_default_timeout(25000)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base_url + "#devices")
                    page.wait_for_selector("#ws-status.online")
                    page.wait_for_function(
                        "uid => installation.devices?.[uid]?.online === true",
                        arg=UID,
                    )
                    page.wait_for_timeout(8000)
                    device = page.evaluate("uid => installation.devices[uid]", UID)
                    seat = page.evaluate(
                        """uid => Object.values(installation.seats || {})
                          .find(item => item.bound === uid)""",
                        UID,
                    )
                    check("Imani is online through the default target",
                          device.get("online") is True, repr(device))
                    check("first-seen report completed",
                          isinstance(device.get("report"), dict), repr(device.get("report")))
                    check("patch inventory completed",
                          isinstance(device.get("patches"), list), repr(device.get("patches")))
                    check("asset inventory completed",
                          isinstance(device.get("assets"), list), repr(device.get("assets")))
                    check("Device enabled state was acknowledged",
                          device.get("enabled_observed") is True
                          and device.get("output_enabled") is True, repr(device))
                    check("assignment converged on the existing safe Seat binding",
                          seat is not None and int(device.get("id", -1)) == int(seat["id"]),
                          repr((seat, device.get("id"))))

                    page.evaluate("""uid => {
                      window.__imaniPatchesReceipt = false;
                      ws.on("patches", data => {
                        if (data?.uid === uid) window.__imaniPatchesReceipt = true;
                      });
                      ws.send("request_patches", {uid});
                    }""", UID)
                    try:
                        page.wait_for_function(
                            "() => window.__imaniPatchesReceipt === true",
                            timeout=10000)
                        patch_receipt = True
                    except Exception:
                        patch_receipt = False
                    check("explicit safe patch-admin request returned a receipt",
                          patch_receipt)
                    check("hardware adoption browser has no page errors",
                          errors == [], repr(errors))
                    browser.close()
            finally:
                stop(process)

        with open(log_path, encoding="utf-8") as source:
            server_output = source.read()
        print(server_output)
        check("Dashboard discovered and logged the en0 source route",
              "OSC LAN sender bound to 192.168.0.100 for peer 192.168.0.103"
              in server_output)
        check("Ctrl-C-equivalent termination reached clean application shutdown",
              "Application shutdown complete" in server_output
              and "Application shutdown failed" not in server_output)

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
