#!/usr/bin/env python3
"""Focused Playwright/capture-socket verification for PE-4."""

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
while not os.path.isfile(os.path.join(REPO, "tools", "audition.py")):
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
    raise RuntimeError("cannot reserve a dynamic non-default loopback port")


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
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def drain(capture):
    capture.setblocking(False)
    try:
        while True:
            capture.recvfrom(65535)
    except BlockingIOError:
        pass
    finally:
        capture.setblocking(True)


def receive(capture, address, predicate=lambda _values: True, timeout=4):
    deadline = time.monotonic() + timeout
    seen = []
    capture.settimeout(.2)
    while time.monotonic() < deadline:
        try:
            packet, _source = capture.recvfrom(65535)
        except socket.timeout:
            continue
        message = osc_message.OscMessage(packet)
        if message.address != address:
            continue
        values = list(message.params)
        seen.append(values)
        if predicate(values):
            return values, seen
    return None, seen


def seed_patch(root):
    patch = os.path.join(root, "alpha")
    os.makedirs(patch)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"PE-4 verifier engine placeholder")
    with open(os.path.join(patch, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin", "params": [],
            "cues": [{"id": "start", "label": "Start sound",
                      "description": "Declared cue"}],
            "caps": [], "slots": [],
        }, target)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-pe4-") as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        os.makedirs(patches)
        os.makedirs(assets)
        seed_patch(patches)
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "pe4", "seats": {}}, target)

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        capture = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        capture.bind(("127.0.0.1", engine_port))
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(temp, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(command_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--sim-no-engine", "--sim-audio-backend", "none",
                "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                browser_errors = []
                page.on("pageerror", lambda error: browser_errors.append(str(error)))

                def handle_dialog(dialog):
                    if dialog.type == "prompt":
                        dialog.accept("")
                    else:
                        dialog.accept()

                page.on("dialog", handle_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.select_option("#editor-patch", "alpha")
                page.click("#editor-launch")
                page.wait_for_function(
                    "() => installation.editor?.active"
                    " && installation.supervisor?.mode === 'edit'")
                page.wait_for_selector("#editor-preview:not([hidden])")
                page.wait_for_function(
                    "() => installation.devices?.['audition-0001']?.editor === true")

                origin = page.evaluate("""() => {
                  const svg=document.querySelector('#editor-spatial');
                  const matrix=svg.getScreenCTM();
                  const p=new DOMPoint(0,0).matrixTransform(matrix);
                  const box=svg.getBoundingClientRect();
                  return {x:p.x,y:p.y,cx:box.x+box.width/2,cy:box.y+box.height/2};
                }""")
                check("edit element origin is centred in the mini-map",
                      abs(origin["x"] - origin["cx"]) < 2
                      and abs(origin["y"] - origin["cy"]) < 2, str(origin))
                check("listener puck is omitted from editor map",
                      page.locator("#editor-spatial .listener-puck").count() == 0)

                drain(capture)
                page.click("#editor-point-add")
                initial_expected = pointfield.falloff(1, 2.0, 3.0)
                initial, initial_seen = receive(
                    capture, "/pt",
                    lambda values: len(values) == 3 and int(values[0]) == 0
                    and int(values[1]) == 0
                    and math.isclose(float(values[2]), initial_expected,
                                     rel_tol=0, abs_tol=1e-5))
                check("scratch point reaches element 0 through /pt", initial is not None,
                      f"expected {initial_expected}, saw {initial_seen}")
                check("scratch point is separate from installation points",
                      page.evaluate("() => Object.keys(installation.points||{}).length") == 0)

                drain(capture)
                page.fill("#editor-point-radius", "4")
                page.select_option("#editor-point-falloff", "0")
                page.dispatch_event("#editor-point-falloff", "change")
                edited, edited_seen = receive(
                    capture, "/pt",
                    lambda values: len(values) == 3
                    and math.isclose(float(values[2]), .5, rel_tol=0, abs_tol=1e-5))
                check("radius and falloff controls update /pt proximity",
                      edited is not None, f"expected 0.5, saw {edited_seen}")

                # Let the radius/falloff state echoes settle before taking a
                # fresh handle. Controls can auto-scroll, so re-scroll and
                # re-read geometry before the spatial drag.
                page.wait_for_timeout(500)
                page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(100)
                handle = page.locator(
                    '#editor-spatial [data-editor-point-id="0"] .editor-point-handle')
                handle.wait_for(state="attached")
                handle_box = handle.bounding_box()
                svg_box = page.locator("#editor-spatial").bounding_box()
                viewport = page.viewport_size
                start_x = handle_box["x"] + handle_box["width"] / 2
                start_y = handle_box["y"] + handle_box["height"] / 2
                target_x = min(max(svg_box["x"] + svg_box["width"] * .72, 8),
                               viewport["width"] - 8)
                target_y = min(max(svg_box["y"] + svg_box["height"] * .38, 8),
                               viewport["height"] - 8)
                drain(capture)
                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(target_x, target_y, steps=8)
                page.mouse.up()
                page.wait_for_function(
                    "() => Math.abs(installation.editor.points?.['0']?.x + 2) > .2")
                point = page.evaluate("() => installation.editor.points['0']")
                expected = pointfield.falloff(
                    point["falloff"], math.hypot(point["x"], point["y"]),
                    point["r"])
                dragged, dragged_seen = receive(
                    capture, "/pt",
                    lambda values: len(values) == 3 and int(values[0]) == 0
                    and int(values[1]) == 0
                    and math.isclose(float(values[2]), expected,
                                     rel_tol=0, abs_tol=1e-5))
                check("drag sends recomputed per-element /pt value",
                      dragged is not None,
                      f"point {point}, expected {expected}, saw {dragged_seen}")

                generation = page.evaluate(
                    "() => installation.editor.generation")
                drain(capture)
                page.click("#editor-restart")
                page.wait_for_function(
                    "old => installation.editor?.generation > old"
                    " && installation.editor?.points?.['0']", arg=generation)
                replayed, replayed_seen = receive(
                    capture, "/pt",
                    lambda values: len(values) == 3 and int(values[0]) == 0
                    and int(values[1]) == 0
                    and math.isclose(float(values[2]), expected,
                                     rel_tol=0, abs_tol=1e-5))
                check("engine restart retains and replays session scratch points",
                      replayed is not None, str(replayed_seen))

                page.wait_for_function(
                    "() => installation.devices?.['audition-0001']?.editor === true")
                page.wait_for_timeout(300)
                drain(capture)
                page.click('[data-editor-cue="start"]')
                declared, declared_seen = receive(
                    capture, "/cue", lambda values: values == ["start"])
                check("declared cue fires bare /cue at the edit engine",
                      declared is not None, str(declared_seen))
                page.fill("#editor-cue-id", "scratch-cue")
                page.click("#editor-cue-fire")
                undeclared, undeclared_seen = receive(
                    capture, "/cue", lambda values: values == ["scratch-cue"])
                check("undeclared cue ID fires through the same /cue path",
                      undeclared is not None, str(undeclared_seen))

                page.click("#editor-stop")
                page.wait_for_function(
                    "() => installation.editor?.active === false"
                    " && installation.supervisor?.mode === 'off'")
                check("scratch controls clear at session end",
                      page.evaluate(
                          "() => Object.keys(installation.editor.points||{}).length") == 0)
                with open(state_path, encoding="utf-8") as source:
                    durable = json.load(source)
                check("scratch points never enter durable installation state",
                      "points" not in durable and "editor" not in durable, str(durable))
                check("browser raised no JavaScript errors", not browser_errors,
                      str(browser_errors))
                browser.close()
        finally:
            capture.close()
            stop(server)
            log.close()
            if server is not None and server.returncode not in (None, 0, -15):
                with open(log_path, encoding="utf-8") as source:
                    print(source.read())

    if FAILURES:
        raise SystemExit(f"{len(FAILURES)} PE-4 checks failed: {', '.join(FAILURES)}")
    print("PE-4 focused verification passed (12/12).")


if __name__ == "__main__":
    main()
