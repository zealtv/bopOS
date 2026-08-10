#!/usr/bin/env python3
"""Headless verification of the Monitor System transport-error log."""

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
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

FAILURES = []
RESERVED = set()


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
        with socket.socket(socket.AF_INET, kind) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
        RESERVED.add((kind, port))
        return port
    raise RuntimeError("cannot reserve loopback port")


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
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-transport-monitor-") as temp:
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "Transport log", "seats": {}}, target)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(temp, "server.log")
        process = None
        with open(log_path, "w", encoding="utf-8") as server_log:
            try:
                process = subprocess.Popen([
                    sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                    "--host", "127.0.0.1", "--port", str(http_port),
                    "--listen-port", str(listen_port),
                    "--send-port", str(send_port),
                    "--osc-target", "127.0.0.1",
                    "--state-file", state_path,
                    "--assets-dir", assets, "--patches-dir", patches,
                ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
                wait_http(base_url, process)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1280, "height": 900})
                    page.set_default_timeout(10000)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base_url)
                    page.wait_for_selector("#ws-status.online")
                    page.evaluate("""() => ws.emit("osc_transport_error", {
                        ts: 1000.125,
                        address: "/all/os/to",
                        destination: "255.255.255.255",
                        port: 6660,
                        errno: 49,
                        message: "Can't assign requested address"
                    })""")
                    section = page.locator("[data-monitor-transport-errors]")
                    check("transport error reveals the bounded System log",
                          section.get_attribute("hidden") is None)
                    text = page.locator(
                        "[data-monitor-transport-error-log]").inner_text()
                    check("System log names the failed OSC address",
                          "/all/os/to" in text, text)
                    check("System log includes destination and errno",
                          "255.255.255.255:6660" in text
                          and "errno 49" in text, text)
                    check("System log exposes the actionable socket message",
                          "Can't assign requested address" in text, text)

                    # A supervisor death gets the same treatment (61/2): the
                    # editor and simulation supervisors used to die with
                    # `stderr=DEVNULL`, so `stopped unexpectedly` was the whole
                    # story regardless of cause.
                    supervisor = page.locator("[data-monitor-supervisor-errors]")
                    check("supervisor log stays hidden until something dies",
                          supervisor.get_attribute("hidden") is not None)
                    page.evaluate("""() => ws.emit("supervisor_error", {
                        ts: 1000.125,
                        mode: "edit",
                        returncode: 1,
                        cause: "PdBinaryError: no usable Pure Data executable",
                        lines: ["Traceback (most recent call last):",
                                "PdBinaryError: no usable Pure Data executable"]
                    })""")
                    check("supervisor death reveals the bounded System log",
                          supervisor.get_attribute("hidden") is None)
                    supervisor_text = page.locator(
                        "[data-monitor-supervisor-error-log]").inner_text()
                    check("supervisor log names the mode and the cause",
                          "Patch Edit" in supervisor_text
                          and "no usable Pure Data executable" in supervisor_text,
                          supervisor_text)
                    # The System panel must tell the truth about the loaded
                    # show (08/4/4-current-show-broadcast). `set_current_show`
                    # broadcast `shows`, `show` and `show_warnings` but never
                    # `state`, and with NO periodic full-state broadcast
                    # anywhere the panel read `none loaded` while a show was
                    # loaded -- indefinitely, not briefly.
                    #
                    # Deliberately behavioural: it asserts what the operator
                    # reads, not that a particular message fired, so a later
                    # change of mechanism does not have to come and edit it.
                    page.evaluate(
                        "() => ws.send('create_show', {name: 'opening'})")
                    show_row = page.locator('[data-monitor-system="show"]')
                    page.wait_for_function(
                        """() => document.querySelector(
                          '[data-monitor-system="show"]')?.textContent
                          === 'opening'""")
                    check("the System panel names the loaded show",
                          show_row.text_content() == "opening",
                          repr(show_row.text_content()))
                    # And says so again when the show goes away: `delete_show`
                    # clears `current_show` without going through
                    # `set_current_show`, so it needed the same broadcast.
                    page.evaluate(
                        "() => ws.send('delete_show', {name: 'opening'})")
                    page.wait_for_function(
                        """() => document.querySelector(
                          '[data-monitor-system="show"]')?.textContent
                          === 'none loaded'""")
                    check("deleting the loaded show empties the panel again",
                          show_row.text_content() == "none loaded",
                          repr(show_row.text_content()))
                    check("transport log renders without page errors",
                          errors == [], repr(errors))
                    browser.close()
            finally:
                stop(process)

        if process is not None and process.returncode not in (0, -15):
            with open(log_path, encoding="utf-8") as source:
                print(source.read())
            FAILURES.append("dashboard shutdown")

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
