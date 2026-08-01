#!/usr/bin/env python3
"""Dashboard-to-simfleet verification for spatial-2 synced named cues."""
import os
import re
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright


HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def main():
    with tempfile.TemporaryDirectory() as temp:
        log_path = os.path.join(temp, "fleet.log")
        state_path = os.path.join(temp, "installation.json")
        log = open(log_path, "w", encoding="utf-8")
        environment = dict(os.environ, PYTHONUNBUFFERED="1")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", "18097", "--listen-port", "15567", "--send-port", "16677",
            "--osc-target", "127.0.0.1", "--state-file", state_path,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, env=environment)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"),
            "--devices", "5", "--protocol", "v1", "--target", "127.0.0.1",
            "--report-port", "15567", "--cmd-port", "16677", "--hb-interval", "1",
            "--boot-secs", "1", "--meter-interval", "0", "--sync-skew-ms", "40",
            "--sync-jitter-ms", "2",
        ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT, env=environment)
        try:
            time.sleep(5)  # boot plus leader estimator settlement
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.goto("http://127.0.0.1:18097/")
                page.wait_for_selector("#cue-fire", timeout=10000)
                page.fill("#cue-id", "sample-start")
                page.fill("#cue-lead", "700")
                clicked_ns = time.monotonic_ns()
                page.click("#cue-fire")
                page.wait_for_function(
                    "() => document.querySelector('#cue-status').value.includes('sample-start fires in 700 ms')",
                    timeout=5000)
                check("dashboard confirms named cue and lead time", True)
                check("fire button locks against accidental duplicate",
                      page.locator("#cue-fire").is_disabled())
                page.screenshot(path=os.path.join(HERE, "synced-start.png"))
                page.wait_for_timeout(1200)
                check("fire button unlocks after cue window",
                      not page.locator("#cue-fire").is_disabled())
                browser.close()
            time.sleep(0.8)
        finally:
            fleet.terminate(); server.terminate()
            fleet.wait(timeout=5); server.wait(timeout=5); log.close()

        text = open(log_path, encoding="utf-8").read()
        pattern = re.compile(
            r"id=(-?\d+).*cue sample-start fired dev_deadline=(\d+) fire_mono=(\d+)")
        fires = {}
        deadlines = {}
        for device_id, deadline, fired in pattern.findall(text):
            fires[int(device_id)] = int(fired)
            deadlines[int(device_id)] = int(deadline)
        check("every simulated device fires the dashboard cue",
              len(fires) == 5, repr(fires))
        if fires:
            spread_ms = (max(fires.values()) - min(fires.values())) / 1e6
            check("cross-device loopback spread is within 20 ms",
                  spread_ms <= 20, f"spread={spread_ms:.3f}ms")
            check("nodes applied distinct device-clock deadlines",
                  len(set(deadlines.values())) >= 4, repr(deadlines))
            earliest_delay_ms = (min(fires.values()) - clicked_ns) / 1e6
            check("cue is scheduled ahead rather than fired immediately",
                  earliest_delay_ms >= 550, f"delay={earliest_delay_ms:.1f}ms")
        check("cue remains a bare named event, not a patch parameter",
              "p/sample-start" not in text and "p/cue" not in text)

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("synced start checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
