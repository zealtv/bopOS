"""Real dashboard + simfleet Device IO inventory and scan journey.

BOPOS_DEVICE_IO_SCREENSHOT=<directory> saves the inventory at 1440 and 420px.
The bus and modules are simulated; this is not a physical I2C verification.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright
from verify_patches_tab import REPO, UID_A, free_port, stop, wait_http

sys.dont_write_bytecode = True
SCREENSHOTS = os.environ.get("BOPOS_DEVICE_IO_SCREENSHOT")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-device-io-") as temporary:
        root = Path(temporary)
        for name in ("data", "patches", "assets"):
            (root / name).mkdir()
        config = root / "io.json"
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"name": "IO fixture", "engine": "pd",
                                      "entrypoint": "main.pd", "params": []}))
        http = free_port(socket.SOCK_STREAM)
        report = free_port(socket.SOCK_DGRAM)
        command = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http}"
        server_args = [sys.executable, str(Path(REPO) / "dashboard/server.py"),
            "--host", "127.0.0.1", "--port", str(http), "--listen-port", str(report),
            "--send-port", str(command), "--osc-target", "127.0.0.1",
            "--data-dir", str(root / "data"), "--patches-dir", str(root / "patches"),
            "--assets-dir", str(root / "assets"), "--sim-no-engine"]
        fleet_args = [sys.executable, str(Path(REPO) / "tools/simfleet.py"),
            "--devices", "1", "--unassigned", "1", "--boot-secs", "0",
            "--hb-interval", ".3", "--target", "127.0.0.1", "--report-port", str(report),
            "--cmd-port", str(command), "--io-config", str(config),
            "--manifest", str(manifest), "--patches-dir", str(root / "patches"),
            "--assets-dir", str(root / "assets")]
        server = fleet = None
        with (root / "server.log").open("w") as server_log, (root / "fleet.log").open("w") as fleet_log:
            try:
                server = subprocess.Popen(server_args, cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
                wait_http(base, server)

                def start_fleet(bus, addresses=None, modules=None):
                    nonlocal fleet
                    stop(fleet)
                    config.write_text(json.dumps({"bus": bus, "scanned": False,
                        "addresses": addresses or [], "modules": modules or {}}))
                    fleet = subprocess.Popen(fleet_args, cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        if fleet.poll() is not None:
                            raise RuntimeError("simfleet exited before binding its command port")
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                            try:
                                probe.bind(("127.0.0.1", command))
                            except OSError:
                                return
                        time.sleep(.05)
                    raise RuntimeError("simfleet did not bind its command port")

                start_fleet(None)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.set_default_timeout(12000)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base + "#devices")
                    page.wait_for_function("uid => !!installation.devices[uid]?.report?.io", arg=UID_A)
                    page.locator(f'#device-roster .device-row[data-uid="{UID_A}"] strong').click()
                    card = page.locator("#device-io")
                    scan = card.locator("[data-io-scan]")
                    page.evaluate("""() => {
                        window.ioMessages = [];
                        const original = ws.send.bind(ws);
                        ws.send = (kind, data) => {
                            if (kind === 'io_scan') ioMessages.push({kind, data});
                            original(kind, data);
                        };
                    }""")

                    def state(expected):
                        page.wait_for_function("value => document.querySelector('#device-io')?.dataset.ioState === value", arg=expected)

                    def scan_bus():
                        previous = page.evaluate("uid => installation.devices[uid].io_scan?.at || 0", UID_A)
                        scan.click()
                        page.wait_for_function("args => {const d=installation.devices[args.uid]; return d.io_scan?.status==='ok' && d.io_scan.at>args.previous;}",
                                               arg={"uid": UID_A, "previous": previous})
                        assert scan.is_enabled()

                    state("no-bus")
                    assert card.locator("[data-io-bus-status]").inner_text() == "No bus"
                    assert card.locator("[data-io-last-scan]").inner_text() == "Last scanned: never"
                    page.evaluate("uid => {delete installation.devices[uid].report.io; renderDeviceDetail();}", UID_A)
                    state("unknown")
                    assert "Module status unavailable." in card.inner_text()
                    assert card.locator("[data-io-last-scan]").inner_text() == "Last scanned: time unavailable"
                    page.locator("#refresh-report").click()
                    state("no-bus")
                    scan_bus()
                    state("no-bus")
                    assert "never" not in card.locator("[data-io-last-scan]").inner_text()
                    assert "No modules reported." in card.inner_text()
                    print("PASS no bus is explicit before and after an acknowledged scan", flush=True)

                    start_fleet(1)
                    page.locator("#refresh-report").click()
                    state("not-scanned")
                    assert "Not scanned yet" in card.locator("[data-io-bus-status]").inner_text()
                    scan_bus()
                    state("empty")
                    assert "Bus is empty" in card.locator("[data-io-bus-status]").inner_text()
                    print("PASS usable bus distinguishes not scanned from scanned empty", flush=True)

                    addresses = [{"address": "0x5a", "claimed": False},
                                 {"address": "0x48", "claimed": False},
                                 {"address": "0x1a", "claimed": True},
                                 {"address": "0x19", "claimed": False},
                                 {"address": "0x29", "claimed": False}]
                    modules = {
                        "adc": {"type": "ads1115", "address": "0x48", "state": "running", "error": None},
                        "tilt": {"type": "lis3dh", "address": "0x19", "state": "errored", "error": "create-failed"},
                        "touch": {"type": "mpr121", "address": "0x5a", "state": "missing", "error": None},
                    }
                    start_fleet(1, addresses, modules)
                    page.locator("#refresh-report").click()
                    page.wait_for_function("uid => !!installation.devices[uid]?.report?.io?.modules?.adc", arg=UID_A)
                    state("not-scanned")
                    scan_bus()
                    state("addresses")
                    assert card.locator("[data-io-address] code").all_text_contents() == ["0x19", "0x1a", "0x29", "0x48", "0x5a"]
                    assert " ".join(card.locator('[data-io-address="0x1a"]').inner_text().split()) == "0x1a Kernel claimed (UU)"
                    assert card.locator('[data-io-address="0x48"] .device-io-hint').inner_text() == "ADS1x15?"
                    assert card.locator('[data-io-address="0x19"] .device-io-hint').inner_text() == "LIS3DH?"
                    assert card.locator('[data-io-address="0x5a"] .device-io-hint').inner_text() == "MPR121?"
                    assert card.locator('[data-io-address="0x29"] .device-io-hint').count() == 0
                    assert "Address hints are tentative." in card.inner_text()
                    for name, expected in (("adc", "running"), ("tilt", "errored"), ("touch", "missing")):
                        assert card.locator(f'[data-io-module="{name}"] .device-io-state').get_attribute("data-state") == expected
                    assert card.locator('[data-io-module="tilt"] .device-io-reason').inner_text() == "create-failed"
                    assert card.locator('input[type="checkbox"]').count() == 0
                    assert card.get_by_text("Re-init", exact=True).count() == 0
                    assert card.get_by_text("Show in Monitor", exact=True).count() == 0
                    print("PASS sorted hex addresses, kernel claim, tentative hints and module states/reason", flush=True)

                    page.locator("#performance-toggle").click()
                    page.wait_for_function("uid => installation.performance && installation.devices[uid]?.report?.performance", arg=UID_A)
                    assert scan.is_enabled()
                    scan_bus()
                    state("addresses")
                    print("PASS scan remains usable in Performance", flush=True)

                    if SCREENSHOTS:
                        destination = Path(SCREENSHOTS)
                        destination.mkdir(parents=True, exist_ok=True)
                        for theme in ("light", "dark"):
                            page.locator("#theme-select").select_option(theme)
                            for width in (1440, 420):
                                page.set_viewport_size({"width": width, "height": 1000})
                                card.evaluate("element => window.scrollBy(0, element.getBoundingClientRect().top - 55)")
                                bounds = card.bounding_box()
                                assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
                                assert bounds["y"] >= 40 and bounds["y"] + bounds["height"] < 955
                                assert card.evaluate("element => element.scrollWidth <= element.clientWidth")
                                suffix = "" if theme == "light" else "-dark"
                                page.screenshot(path=str(destination / f"device-io{suffix}-{width}.png"))

                    # A missing reply is a timeout, not an empty-bus assertion.
                    last_scanned = card.locator("[data-io-last-scan]").inner_text()
                    stop(fleet)
                    count = page.evaluate("ioMessages.length")
                    scan.click()
                    assert scan.is_disabled()
                    scan.evaluate("button => button.click()")
                    assert page.evaluate("ioMessages.length") == count + 1
                    page.wait_for_function("() => document.querySelector('.device-io-feedback')?.textContent.includes('timed out')")
                    assert scan.is_enabled()
                    assert card.locator("[data-io-last-scan]").inner_text() == last_scanned
                    state("addresses")
                    print("PASS pending scan prevents duplicate clicks; timeout preserves last observed bus and timestamp", flush=True)

                    page.evaluate("uid => {installation.devices[uid].online=false; renderDeviceDetail();}", UID_A)
                    assert scan.is_disabled()
                    assert card.locator("[data-io-module]").count() == 3
                    scan.evaluate("button => button.click()")
                    assert page.evaluate("ioMessages.length") == count + 1
                    print("PASS offline inventory stays visible with Scan disabled", flush=True)

                    # Valid protocol names can contain markup; display them as text.
                    hostile = '<img src=x onerror=window.__ioInjected=1>'
                    modules[hostile] = {"type": "fixture", "address": "0x29", "state": "running", "error": None}
                    start_fleet(1, addresses, modules)
                    page.wait_for_function("uid => installation.devices[uid].online", arg=UID_A)
                    # The timed-out scan may have left a general report query
                    # pending. An attributed scan receipt refreshes IO directly.
                    scan_bus()
                    page.wait_for_function("args => !!installation.devices[args.uid]?.report?.io?.modules?.[args.name]", arg={"uid": UID_A, "name": hostile})
                    assert card.locator("img").count() == 0
                    assert hostile in card.locator(".device-io-identity strong").all_text_contents()
                    assert page.evaluate("window.__ioInjected || 0") == 0
                    page.locator("#performance-toggle").click()
                    page.wait_for_function("uid => !installation.performance && installation.devices[uid]?.report?.performance===false", arg=UID_A)
                    page.locator("#device-alias").focus()
                    page.evaluate("uid => ws.send('io_write', {uid, config:{name:'unknown', command:'clear', args:[]}})", UID_A)
                    page.wait_for_function("() => document.querySelector('.device-io-error')?.textContent.includes('unknown-command')")
                    assert "Last IO error: unknown · unknown-command" in card.locator(".device-io-error").inner_text()
                    assert page.evaluate("document.activeElement.id") == "device-alias"
                    assert card.locator('[data-io-module="adc"] .device-io-state').get_attribute("data-state") == "running"
                    print("PASS unsolicited IO error appears while an unrelated device form retains focus", flush=True)
                    assert page.evaluate("ioMessages.every(message => message.data.uid === " + json.dumps(UID_A) + ")")
                    assert not errors, errors
                    browser.close()
                    print("PASS exact physical UID scan routing, escaped module names and no browser errors", flush=True)
            except Exception:
                print((root / "server.log").read_text()[-5000:])
                print((root / "fleet.log").read_text()[-3000:])
                raise
            finally:
                stop(fleet)
                stop(server)


if __name__ == "__main__":
    main()
