#!/usr/bin/env python3
from dashboard_process import launch_dashboard
from project_fixture import project_path, data_root
"""Real-dashboard + simfleet journey for release display (contract 1.26).

A mixed fleet reports `release` in /os/report: one node on a release, one on a
development checkout, one older node that sends none. The Devices roster, the
device detail and the patch-diagnostics line show the short release (the build
hash dropped), with the full string and git hash on hover; an older node shows
its hash, set apart. The header shows the dashboard host's short release.
Outside tooltips, no hash shows next to a release.
"""

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
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

FAILURES = []
RESERVED = set()
HASH = "a1b2c3d"
DEV = "1.0.0+dev.12.gabc1234"
CASES = [  # uid, simfleet --release value, shown text, hover title
    ("02:53:49:4d:00:01", "1.0.0", "1.0.0", "bopOS 1.0.0 (git " + HASH + ")"),
    ("02:53:49:4d:00:02", DEV, "1.0.0+dev.12",
     "bopOS " + DEV + " (git " + HASH + ")"),
    ("02:53:49:4d:00:03", "-", "git " + HASH,
     "Release not reported by this node (git " + HASH + ")"),
]
HEADERS = [  # host_version, host_git_rev, shown in the header
    ("1.0.0", "abc1234", "1.0.0"),
    (DEV, "abc1234", "1.0.0+dev.12"),
    ("1.0.0+dev.gabc1234", "abc1234", "1.0.0+dev"),
    ("10.12.3+dev.123.gabc1234", "abc1234", "10.12.3+dev.123"),
    ("unknown", "", "unknown"),
]

def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""), flush=True)
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
    raise RuntimeError("could not reserve a local port")


def stop_process(process):
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
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-release-line-") as temp:
        state_path = str(project_path(temp))
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(os.path.join(patches, "alpha"))
        with open(os.path.join(patches, "alpha", "main.bin"), "wb") as target:
            target.write(b"alpha")
        with open(os.path.join(patches, "alpha", "bopos.patch.json"), "w",
                  encoding="utf-8") as target:
            json.dump({"engine": "test", "entrypoint": "main.bin",
                       "params": [], "caps": [], "slots": []}, target)
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "Release line rig", "seats": {}}, target)

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w", encoding="utf-8")
        fleet_log = open(os.path.join(temp, "fleet.log"), "w", encoding="utf-8")
        server = fleet = None
        try:
            server = launch_dashboard([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--data-dir", data_root(state_path),
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "3", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.3", "--boot-secs", "0.2",
                "--patches-dir", patches,
                "--manifest", os.path.join(patches, "alpha", "bopos.patch.json"),
                "--assets-dir", assets, "--version", HASH,
                "--release", ",".join(case[1] for case in CASES),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1200})
                page.set_default_timeout(12000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 3")
                page.click("#tab-button-devices")
                page.wait_for_selector("#tab-devices:not([hidden])")
                for uid, flag, shown, title in CASES:
                    reported = shown.startswith("git ")
                    page.wait_for_function(
                        "uid => installation.devices[uid]?.report?.git_rev", arg=uid)
                    row = page.locator(
                        f'#device-roster .device-row[data-uid="{uid}"]')
                    mark = row.locator(".bopos-version")
                    check(f"{uid[-2:]} roster shows {shown!r}",
                          mark.inner_text() == shown, mark.inner_text())
                    check(f"{uid[-2:]} roster hover title is {title!r}",
                          mark.get_attribute("title") == title,
                          repr(mark.get_attribute("title")))
                    check(f"{uid[-2:]} roster marks a missing release set apart",
                          ("unreported" in (mark.get_attribute("class") or ""))
                          == reported, repr(mark.get_attribute("class")))
                    if not reported:
                        check(f"{uid[-2:]} roster row shows no hash",
                              HASH not in row.inner_text().lower()
                              and "abc1234" not in row.inner_text().lower(),
                              row.inner_text())
                    page.click(f'#device-roster .device-row[data-uid="{uid}"]')
                    page.wait_for_selector("#patch-diagnostics .bopos-version")
                    mark = page.locator("#patch-diagnostics .bopos-version")
                    check(f"{uid[-2:]} diagnostics shows {shown!r}",
                          mark.inner_text() == shown, mark.inner_text())
                    check(f"{uid[-2:]} diagnostics hover title is {title!r}",
                          mark.get_attribute("title") == title,
                          repr(mark.get_attribute("title")))
                    detail = page.locator("#detail dl").first
                    facts = detail.inner_text()
                    check(f"{uid[-2:]} device facts show {shown!r}",
                          shown in facts, facts)
                    if not reported:
                        check(f"{uid[-2:]} diagnostics line and facts show no hash",
                              HASH not in page.locator("#patch-diagnostics").inner_text()
                              and HASH not in facts,
                              facts)
                    raw = page.evaluate(
                        "uid => installation.devices[uid].report.release", arg=uid)
                    want = None if flag == "-" else flag
                    check(f"{uid[-2:]} dashboard keeps release on the device report",
                          raw == want, repr(raw))
                    keys = page.locator("#detail dl dt").all_inner_texts()
                    check(f"{uid[-2:]} raw report lists release",
                          "release" in keys, repr(keys))

                # Header: the dashboard host's short release; full string and
                # hash on hover. The real value first, then forced forms.
                host = page.evaluate("installation.host_version")
                head = page.locator("#host-version")
                check("header shows the host's short release",
                      head.inner_text() == host.split(".g")[0]
                      and ".g" not in head.inner_text(), head.inner_text())
                check("header hover keeps the full string",
                      host in (head.get_attribute("title") or ""),
                      repr(head.get_attribute("title")))
                for full, git, shown in HEADERS:
                    page.evaluate(
                        "([v, g]) => { installation.host_version = v;"
                        " installation.host_git_rev = g; renderHeader(); }",
                        [full, git])
                    check(f"header shows {shown!r} for {full!r}",
                          head.inner_text() == shown, head.inner_text())
                    want = ("Dashboard host: bopOS " + full
                            + (f" (git {git})" if git else "")
                            + ". Details in the Settings tab.")
                    check(f"header hover for {full!r} carries string and hash",
                          head.get_attribute("title") == want,
                          repr(head.get_attribute("title")))
                    fits = page.evaluate(
                        "() => { const e = document.querySelector('#host-version');"
                        " return e.scrollWidth <= e.clientWidth; }")
                    check(f"header text for {full!r} is not clipped", fits)
                check("no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop_process(fleet)
            stop_process(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("Device release line checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
