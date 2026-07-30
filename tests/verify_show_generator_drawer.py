#!/usr/bin/env python3
"""Focused Show-inspector journey for the shared generator drawer."""

import json
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
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
    raise RuntimeError("cannot reserve loopback port")


def wait_http(url, process):
    deadline = time.monotonic() + 12
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


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.1)
    return False


def make_fixture(root):
    root = Path(root)
    patch = root / "patches" / "alpha"
    assets = root / "assets"
    shows = root / "shows"
    patch.mkdir(parents=True)
    assets.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"show-generator-drawer")
    (patch / "bopos.patch.json").write_text(json.dumps({
        "engine": "test",
        "entrypoint": "main.bin",
        "params": [{"name": "gain", "kind": "float", "min": 0, "max": 1,
                    "default": .5, "dashboard": True}],
        "events": [], "caps": [], "slots": [],
    }))
    state = {
        "schema": 1, "name": "Generator drawer", "current_show": "forms",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64},
        "params_patch": "alpha", "groups": {}, "seats": {},
        "device_registry": {},
    }
    messages = [
        {"uid": "aaaa0001", "args": [{"type": "f", "value": .25}]},
        {"uid": "aaaa0002", "args": [{"type": "f", "value": .8},
                                      {"type": "s", "value": "1s"}]},
        {"uid": "aaaa0003", "args": [{"type": "s", "value": "loop"},
                                      {"type": "f", "value": .2},
                                      {"type": "s", "value": "1s"},
                                      {"type": "f", "value": .8},
                                      {"type": "s", "value": "1s"}]},
        {"uid": "aaaa0004", "args": [{"type": "s", "value": "lfo"},
                                      {"type": "s", "value": "sine"},
                                      {"type": "f", "value": 0},
                                      {"type": "f", "value": 1},
                                      {"type": "s", "value": "4s"}]},
        {"uid": "aaaa0005", "args": [{"type": "s", "value": "stop"}]},
    ]
    for message in messages:
        message.update({"kind": "osc", "alias": None, "address": "/p/gain",
                        "target": ["all"]})
    show = {
        "schema": 1, "name": "forms",
        "items": [{"kind": "step", "uid": "11111111", "alias": "forms",
                   "messages": messages, "duration_s": 10, "play_count": 1,
                   "then_actions": [{"type": "stop"}]}],
    }
    state_path = root / "installation.json"
    show_path = shows / "forms.json"
    state_path.write_text(json.dumps(state))
    show_path.write_text(json.dumps(show))
    return state_path, show_path, root / "patches", assets


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-generator-") as temporary:
        state_path, show_path, patches, assets = make_fixture(temporary)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = Path(temporary) / "server.log"
        log = log_path.open("w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                for attempt in range(3):
                    page.goto(base_url)
                    page.wait_for_selector("#ws-status.online")
                    page.click("#tab-button-show")
                    try:
                        page.wait_for_selector(
                            '[data-show-message-focus="aaaa0004"]',
                            state="attached", timeout=10000)
                        break
                    except PlaywrightTimeoutError:
                        if attempt == 2:
                            raise
                        page.reload()

                def focus(uid):
                    page.locator(f'[data-show-message-focus="{uid}"]').click()

                def saved(uid):
                    data = json.loads(show_path.read_text())
                    return next(message for message in data["items"][0]["messages"]
                                if message["uid"] == uid)

                focus("aaaa0004")
                drawer = page.locator("[data-show-gen-drawer]")
                check("Show uses the shared three-tab drawer",
                      drawer.count() == 1
                      and drawer.locator("[data-gen-kind-tab]").evaluate_all(
                          "nodes => nodes.map(node => node.dataset.genKindTab)")
                      == ["lfo", "loop", "fade"])
                check("the drawer is the fixed instrument width",
                      drawer.evaluate("node => getComputedStyle(node).width")
                      == "320px")
                check("Show uses the panel waveform body",
                      drawer.locator(".live-gen-wave").count() == 1
                      and drawer.locator(".show-param-preview").count() == 0)
                page.wait_for_timeout(1200)
                check("open state survives timer re-renders",
                      page.locator("[data-show-gen-drawer]").count() == 1)

                page.fill('[data-param-lfo="period"]', "2.5")
                page.locator('[data-param-lfo="period"]').press("Tab")
                check("field draft persists on the focused message",
                      wait_for(lambda: saved("aaaa0004")["args"][4]
                               == {"type": "s", "value": "2.5s"}),
                      repr(saved("aaaa0004")["args"]))

                # One fixture message per kind: switching a kind persists.
                focus("aaaa0002")
                check("fade round-trips into the shared face",
                      page.locator('[data-gen-kind-tab="fade"]')
                      .get_attribute("aria-pressed") == "true")
                page.locator('[data-gen-kind-tab="loop"]').click()
                check("a generator tab persists its canonical default",
                      wait_for(lambda: saved("aaaa0002")["args"][0]
                               == {"type": "s", "value": "loop"}))

                focus("aaaa0001")
                check("value stays an ordinary field, not a generator tab",
                      page.locator("#show-param-value").count() == 1
                      and page.locator("[data-show-gen-drawer]").count() == 0
                      and page.locator("#show-param-generator").count() == 0)
                # design-language §5: the ∿ is "always an 18px circle". This
                # surface used to override it to a borderless transparent glyph;
                # Bob ruled on 2026-07-30 that §5 holds everywhere, so §6's rule
                # is anchored on `.live-param-mod` itself rather than on the two
                # panel hosts. Assert the circle HERE, in the third host, since
                # that is where "always" was previously untrue.
                mod = page.locator("[data-show-gen-toggle]")
                face = mod.evaluate(
                    "el => { const s = getComputedStyle(el); return {"
                    " radius: s.borderRadius, width: s.width,"
                    " height: s.height, border: s.borderTopWidth }; }")
                check("the Show inspector's mod glyph is §5's 18px circle",
                      face["radius"] == "50%" and face["width"] == "18px"
                      and face["height"] == "18px"
                      and face["border"] != "0px", str(face))

                page.locator("[data-show-gen-toggle]").click()
                page.locator("[data-show-param-stop]").click()
                check("the explicit Stop action preserves the stop wire form",
                      wait_for(lambda: saved("aaaa0001")["args"]
                               == [{"type": "s", "value": "stop"}]))

                focus("aaaa0005")
                check("stop is stated explicitly and can return to value",
                      "stopped" in page.locator(".show-param-stop").inner_text().lower())
                page.locator("[data-show-gen-toggle]").click()
                page.locator("[data-show-param-value]").click()
                check("the explicit Value action restores a typed constant",
                      wait_for(lambda: saved("aaaa0005")["args"]
                               == [{"type": "f", "value": .5}]))
                check("browser emitted no page errors", not page_errors,
                      repr(page_errors))
                browser.close()
        finally:
            stop(server)
            log.close()

        if FAILURES:
            print("\nserver log tail:\n", log_path.read_text()[-4000:])

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
