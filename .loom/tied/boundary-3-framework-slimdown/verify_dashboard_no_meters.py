#!/usr/bin/env python3
"""Browser check that the removed meter surface stays absent."""
import os
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright
from pythonosc.udp_client import SimpleUDPClient

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    REPO = os.path.dirname(REPO)


def main():
    with tempfile.TemporaryDirectory() as temp:
        server_log = open(os.path.join(temp, "server.log"), "w+")
        fleet_log = open(os.path.join(temp, "fleet.log"), "w+")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", "18103", "--listen-port", "15593", "--send-port", "16693",
            "--osc-target", "127.0.0.1", "--state-file", os.path.join(temp, "state.json"),
        ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
            "--target", "127.0.0.1", "--report-port", "15593", "--cmd-port", "16693",
            "--hb-interval", "1", "--boot-secs", "1",
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        try:
            time.sleep(3)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 1280, "height": 1000})
                page = context.new_page()
                page.goto("http://127.0.0.1:18103/")
                page.wait_for_selector("#assigned .device-row", timeout=10000)
                page.locator("#assigned .device-row").first.click()
                page.wait_for_selector('input[data-param="gain"]', timeout=10000)
                assert page.locator('[data-meter]').count() == 0
                assert page.locator('input[data-param="level"]').count() == 0
                assert page.locator('[data-param="backing"]').count() == 1
                assert page.locator('[data-param="echo"]').count() == 1

                SimpleUDPClient("127.0.0.1", 15593).send_message("/1/p/mystery", 7.7)
                page.wait_for_timeout(500)
                assert page.locator('[data-meter], [data-param="mystery"]').count() == 0

                facilitator = context.new_page()
                facilitator.goto("http://127.0.0.1:18103/facilitator")
                facilitator.wait_for_selector(".card", timeout=10000)
                assert facilitator.locator('[data-meter]').count() == 0
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            server_log.flush()
            fleet_log.flush()
            logs = open(server_log.name).read() + open(fleet_log.name).read()
            server_log.close()
            fleet_log.close()
        assert "Traceback" not in logs, logs[-1000:]
    print("[PASS] dashboard renders all declared params as controls")
    print("[PASS] removed declared and undeclared meter UI stays absent")
    print("[PASS] facilitator stays free of meter presentation")
    print("boundary-3 dashboard no-meters checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
