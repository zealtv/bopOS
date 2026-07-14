#!/usr/bin/env python3
"""Focused verification for the tracked demo layout and dashboard flow."""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright


HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))
import manifest


HTTP_PORT, OSC_LISTEN, OSC_COMMAND = 18114, 15584, 16694
BASE_URL = f"http://127.0.0.1:{HTTP_PORT}"
FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def wait_http(timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL + "/", timeout=1):
                return True
        except Exception:
            time.sleep(0.1)
    return False


def row(page, name):
    return page.locator(
        f'.distribution-item[data-kind="patch"][data-name="{name}"]')


def wait_status(page, name, status, timeout=10000):
    page.wait_for_function(
        """([name, status]) => [...document.querySelectorAll('.distribution-item')]
          .some(item => item.dataset.kind === 'patch'
            && item.dataset.name === name
            && item.querySelector('.sync-status')?.innerText.trim() === status)""",
        arg=[name, status], timeout=timeout)


def wait_log(page, path, text, timeout=8000):
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        try:
            with open(path, encoding="utf-8") as source:
                value = source.read()
            if text in value:
                return value
        except OSError:
            pass
        page.wait_for_timeout(100)
    return ""


def static_checks():
    patches = os.path.join(REPO, "patches")
    demo_pd = os.path.join(patches, "demo-pd")
    demo_sc = os.path.join(patches, "demo-sc")
    check("demo-pd replaces patches/default",
          os.path.isdir(demo_pd) and not os.path.exists(os.path.join(patches, "default")))
    check("demo-sc replaces templates",
          os.path.isdir(demo_sc) and not os.path.exists(os.path.join(REPO, "templates")))
    check("retired patch-level config is absent",
          not os.path.exists(os.path.join(demo_pd, "bopos.config")))
    with open(os.path.join(patches, "active_patch.txt"), encoding="utf-8") as source:
        check("active patch follows renamed PD demo", source.read().strip() == "demo-pd")

    for name, expected in (("demo-pd", ("pd", "main.pd")),
                           ("demo-sc", ("sclang", "main.scd"))):
        loaded, error = manifest.load(os.path.join(patches, name))
        check(f"{name} manifest validates", error is None, str(error))
        check(f"{name} manifest selects its engine and entrypoint",
              loaded is not None
              and (loaded.get("engine"), loaded.get("entrypoint")) == expected,
              repr(loaded))
        check(f"{name} declares no required asset slots",
              loaded is not None and loaded.get("slots") == [], repr(loaded))


def dashboard_checks():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        nodes = os.path.join(temp, "nodes")
        assets = os.path.join(temp, "assets")
        os.makedirs(nodes)
        os.makedirs(assets)
        fleet_path = os.path.join(temp, "fleet.log")
        server_path = os.path.join(temp, "server.log")
        fleet_log = open(fleet_path, "w", encoding="utf-8")
        server_log = open(server_path, "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", str(HTTP_PORT), "--listen-port", str(OSC_LISTEN),
            "--send-port", str(OSC_COMMAND), "--osc-target", "127.0.0.1",
            "--state-file", state_file, "--assets-dir", assets,
            "--patches-dir", os.path.join(REPO, "patches"),
            "--public-url", BASE_URL,
        ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"),
            "--devices", "1", "--state-dir", nodes, "--target", "127.0.0.1",
            "--report-port", str(OSC_LISTEN), "--cmd-port", str(OSC_COMMAND),
            "--hb-interval", "0.5", "--boot-secs", "1",
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        try:
            check("real dashboard server starts", wait_http())
            served = set()
            for name in ("demo-pd", "demo-sc"):
                with urllib.request.urlopen(
                        BASE_URL + f"/patches/{name}/.manifest.json", timeout=5) as response:
                    transfer = json.load(response)
                if any(item["path"] == "bopos.patch.json" for item in transfer["files"]):
                    served.add(name)
            check("dashboard serves transfer manifests for both demos",
                  served == {"demo-pd", "demo-sc"}, repr(served))

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(BASE_URL + "/")
                device = page.locator("#assigned .device-row").first
                device.wait_for(timeout=10000)
                device.click()
                page.wait_for_selector("#distribution", timeout=5000)
                check("dashboard renders both demo Send cards",
                      row(page, "demo-pd").count() == 1
                      and row(page, "demo-sc").count() == 1)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'demo-pd')", timeout=5000)
                check("simfleet starts on demo-pd",
                      "demo-pd" in page.locator("#patch-select").inner_text())

                row(page, "demo-sc").locator("[data-send]").click()
                wait_status(page, "demo-sc", "in sync")
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'demo-sc')", timeout=5000)
                check("sending demo-sc adds it to the installed-patch dropdown", True)
                page.select_option("#patch-select", "demo-sc")
                page.click("#patch-switch")
                switch_log = wait_log(page, fleet_path, "os/patch demo-sc")
                check("dashboard sends the demo-sc switch to the simulated node",
                      "os/patch demo-sc" in switch_log, switch_log[-1200:])
                page.screenshot(path=os.path.join(HERE, "dist4-demos.png"), full_page=True)
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()
            server_log.close()


def main():
    static_checks()
    dashboard_checks()
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("dist-4 demo layout and dashboard flow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
