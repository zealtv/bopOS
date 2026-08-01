#!/usr/bin/env python3
"""Focused live-stack verification for PE-4b editor delivery/targeting."""

import json
import math
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright
from pythonosc import osc_message

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))
import pointfield  # noqa: E402

FAILURES = []
RESERVED_PORTS = set()


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if port in RESERVED_PORTS:
            continue
        sock = socket.socket(socket.AF_INET, kind)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.close()
            continue
        sock.close()
        RESERVED_PORTS.add(port)
        return port
    raise RuntimeError("cannot reserve loopback port")


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
            raise RuntimeError("dashboard exited before HTTP ready")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard HTTP timeout")


def drain(sock):
    sock.setblocking(False)
    try:
        while True:
            sock.recvfrom(65535)
    except BlockingIOError:
        pass
    finally:
        sock.setblocking(True)


def collect(sock, seconds=4):
    deadline = time.monotonic() + seconds
    messages = []
    sock.settimeout(.2)
    while time.monotonic() < deadline:
        try:
            packet, _source = sock.recvfrom(65535)
        except socket.timeout:
            continue
        message = osc_message.OscMessage(packet)
        messages.append((message.address, list(message.params)))
    return messages


def wait_for(sock, predicate, seconds=4):
    deadline = time.monotonic() + seconds
    seen = []
    sock.settimeout(.2)
    while time.monotonic() < deadline:
        try:
            packet, _source = sock.recvfrom(65535)
        except socket.timeout:
            continue
        message = osc_message.OscMessage(packet)
        item = (message.address, list(message.params))
        seen.append(item)
        if predicate(*item):
            return item, seen
    return None, seen


def point_message(address, values, *, element, expected):
    return (address == "/pt" and len(values) == 3
            and int(values[0]) == 0 and int(values[1]) == element
            and math.isclose(float(values[2]), expected,
                             rel_tol=0, abs_tol=1e-5))


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-pe4b-") as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        patch = os.path.join(patches, "alpha")
        os.makedirs(patch)
        os.makedirs(assets)
        with open(os.path.join(patch, "main.bin"), "wb") as target:
            target.write(b"PE-4b placeholder")
        with open(os.path.join(patch, "bopos.patch.json"), "w",
                  encoding="utf-8") as target:
            json.dump({"engine": "test", "entrypoint": "main.bin",
                       "params": [], "cues": [{"id": "start"}],
                       "caps": [], "slots": []}, target)
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "pe4b", "seats": {}}, target)

        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        capture = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        capture.bind(("127.0.0.1", engine_port))
        log_path = os.path.join(temp, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(report_port),
                "--send-port", str(command_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--sim-no-engine", "--sim-audio-backend", "none",
                "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            base_url = f"http://127.0.0.1:{http_port}"
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.select_option("#editor-patch", "alpha")
                page.click("#editor-launch")
                page.wait_for_function(
                    "() => installation.devices?.['audition-0001']?.editor === true")
                check("element 0 is the new-session default",
                      page.locator(
                          'input[name="editor-point-element"][value="0"]').is_checked())

                drain(capture)
                page.click("#editor-point-add")
                expected = pointfield.falloff(1, 2.0, 3.0)
                initial, initial_seen = wait_for(
                    capture, lambda address, values: point_message(
                        address, values, element=0, expected=expected))
                check("point geometry decomposes to element 0", initial is not None,
                      str(initial_seen))

                drain(capture)
                page.check('input[name="editor-point-element"][value="1"]')
                switched = collect(capture, 1.0)
                release0 = any(point_message(address, values, element=0,
                                             expected=0.0)
                               for address, values in switched)
                replay1 = any(point_message(address, values, element=1,
                                            expected=expected)
                              for address, values in switched)
                check("switch releases element 0", release0, str(switched))
                check("switch replays held point to element 1", replay1,
                      str(switched))

                generation = page.evaluate("() => installation.editor.generation")
                drain(capture)
                page.click("#editor-restart")
                page.wait_for_function(
                    "old => installation.editor?.generation > old"
                    " && installation.editor?.point_element === 1", arg=generation)
                replayed, replayed_seen = wait_for(
                    capture, lambda address, values: point_message(
                        address, values, element=1, expected=expected))
                check("restart retains element 1 and replays scratch", replayed is not None,
                      str(replayed_seen))

                page.wait_for_function(
                    "() => installation.devices?.['audition-0001']?.editor === true")
                drain(capture)
                page.click('[data-editor-cue="start"]')
                cue, cue_seen = wait_for(
                    capture, lambda address, values:
                    address == "/cue" and values == ["start"])
                check("declared cue reaches the edit engine", cue is not None,
                      str(cue_seen))
                check("browser raised no errors", not errors, str(errors))
                browser.close()
        finally:
            capture.close()
            stop(server)
            log.close()
            if server is not None and server.returncode not in (None, 0, -15):
                with open(log_path, encoding="utf-8") as source:
                    print(source.read())

    if FAILURES:
        raise SystemExit(f"{len(FAILURES)} PE-4b checks failed: {', '.join(FAILURES)}")
    print("PE-4b focused verification passed (7/7).")


if __name__ == "__main__":
    main()
