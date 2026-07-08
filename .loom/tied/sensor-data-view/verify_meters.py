#!/usr/bin/env python3
"""Browser pass for sensor-data-view (Option A, role:"meter", ratified).

Real dashboard + real simfleet (which now emits declared role:meter params as
/<id>/p/<name>), headless Chromium. Checks: declared meters render read-only
and update live; an undeclared inbound /p/ name gets the sec 8 badge, not a
control; meter values stay out of params/presets/installation.json; the
facilitator view is untouched by meters; helper.py's meter sources read.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright
from pythonosc.udp_client import SimpleUDPClient

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def helper_unit_checks():
    # meter_loop itself needs a Pi (ports 7770/6661, amixer, systemd) -- that
    # verification is Bob's. Here: the pure readers and config plumbing only.
    result = subprocess.run(
        [sys.executable, "-c", """
import sys
sys.path.insert(0, %r)
import ast, textwrap
source = open(%r).read()
tree = ast.parse(source)
wanted = {"read_cpu_temp", "meter_loop", "read_node_config"}
found = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
assert wanted <= found, wanted - found
# compile-level sanity for the whole module without importing it (import
# binds port 7770); then exercise read_cpu_temp + config defaults standalone
compile(source, "helper.py", "exec")
namespace = {}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in ("read_node_config", "read_cpu_temp"):
        exec(compile(ast.Module(body=[node], type_ignores=[]), "helper.py", "exec"), namespace)
config = namespace["read_node_config"]("/nonexistent")
assert config["METERS"] == "" and config["METER_INTERVAL"] == "5", config
temp = namespace["read_cpu_temp"]()
assert temp is None or isinstance(temp, float), temp
print("helper units ok")
""" % (os.path.join(REPO, "python"), os.path.join(REPO, "python", "helper.py"))],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check("helper.py meter units", result.returncode == 0,
          result.stdout.decode(errors="replace")[-300:])


def main():
    helper_unit_checks()
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", "18091",
            "--listen-port", "15561", "--send-port", "16671", "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
            "--target", "127.0.0.1", "--report-port", "15561", "--cmd-port", "16671",
            "--hb-interval", "1.0", "--boot-secs", "2.0",
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            time.sleep(4)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(viewport={"width": 1280, "height": 1100})
                page = context.new_page()
                page.on("dialog", lambda d: d.accept("meters-check")
                        if d.type == "prompt" else d.accept())
                page.goto("http://127.0.0.1:18091/")
                page.wait_for_selector("#assigned .device-row", timeout=10000)
                page.locator("#assigned .device-row").first.click()

                # declared role:meter renders as a meter row, not a control
                page.wait_for_selector('[data-meter="level"]', timeout=10000)
                check("declared meter renders",
                      page.locator('[data-meter="level"] .meter-bar').count() == 1)
                check("meter is not an input",
                      page.locator('input[data-param="level"]').count() == 0)

                # live: the value changes between two reads
                first = page.locator('[data-meter="level"] output').inner_text()
                changed = False
                for _ in range(12):
                    page.wait_for_timeout(500)
                    if page.locator('[data-meter="level"] output').inner_text() != first:
                        changed = True
                        break
                check("meter updates live", changed, f"stuck at {first!r}")

                # undeclared inbound name -> badge, not a guess (sec 8)
                SimpleUDPClient("127.0.0.1", 15561).send_message("/1/p/mystery", 7.7)
                page.wait_for_selector('[data-meter="mystery"]', timeout=5000)
                check("undeclared meter is badged",
                      "undeclared" in page.locator('[data-meter="mystery"]').inner_text().lower())
                check("undeclared meter is not an input",
                      page.locator('input[data-param="mystery"]').count() == 0)
                page.screenshot(path=os.path.join(HERE, "01-meters.png"))

                # meters never leak into presets or durable params
                page.click("#preset-save")
                page.wait_for_timeout(1500)  # debounced save
                saved = json.load(open(state_file))
                all_params = [device.get("params", {})
                              for device in saved.get("devices", {}).values()]
                check("meter absent from durable params",
                      all("level" not in params and "mystery" not in params
                          for params in all_params))
                preset = saved.get("presets", {}).get("meters-check", {})
                check("meter absent from preset",
                      preset and all("level" not in params and "mystery" not in params
                                     for params in preset.get("devices", {}).values()),
                      json.dumps(preset)[:200])

                # facilitator untouched: one volume slider per device, no meters
                fac = context.new_page()
                fac.goto("http://127.0.0.1:18091/facilitator")
                fac.wait_for_selector(".card input[type=range]", timeout=10000)
                check("facilitator shows one slider per device, no meters",
                      fac.locator(".card input[type=range]").count() == 3
                      and fac.locator('[data-meter]').count() == 0)
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("sensor-data-view checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
