#!/usr/bin/env python3
"""Browser journey for portable Show targets and reference preservation."""

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
    patches = root / "patches"
    assets = root / "assets"
    patch = patches / "alpha"
    shows = root / "shows"
    patch.mkdir(parents=True)
    assets.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"show-reference-foundation")
    (patch / "bopos.patch.json").write_text(json.dumps({
        "engine": "test",
        "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "kind": "float", "min": 0, "max": 1,
             "default": .5, "dashboard": True},
        ],
        "events": [],
        "caps": [],
        "slots": [],
    }))
    state = {
        "schema": 1,
        "name": "Portable room",
        "current_show": "opening-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64},
        "params_patch": "alpha",
        "groups": {"7": {"id": 7, "name": "Front"}},
        "next_group_id": 8,
        "seats": {},
        "device_registry": {},
    }
    reference = {
        "content": {"name": "alpha", "fingerprint": "a" * 64},
        "schema": "sha256:" + "b" * 64,
    }
    show = {
        "schema": 1,
        "name": "opening-set",
        "items": [{
            "kind": "step",
            "uid": "11111111",
            "alias": "opening",
            "messages": [{
                "kind": "reference",
                "uid": "aaaaaaaa",
                "alias": "content reference",
                "address": "/content/example",
                "args": [],
                "target": ["group:Missing"],
                "reference": reference,
            }],
            "duration_s": 1,
            "play_count": 1,
            "then_actions": [{"type": "stop"}],
        }],
    }
    state_path = root / "installation.json"
    show_path = shows / "opening-set.json"
    state_path.write_text(json.dumps(state))
    show_path.write_text(json.dumps(show))
    return state_path, show_path, patches, assets, reference


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-reference-") as temporary:
        state_path, show_path, patches, assets, reference = make_fixture(temporary)
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
                "--osc-target", "127.0.0.1",
                "--state-file", str(state_path),
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
                            '[data-show-message-focus="aaaaaaaa"]',
                            state="attached",
                            timeout=10000,
                        )
                        break
                    except PlaywrightTimeoutError:
                        if attempt == 2:
                            raise
                        # Initial full-state can beat show.js listener binding
                        # under full-suite load. A reconnect is a documented
                        # full-state convergence edge.
                        page.reload()
                pill = page.locator('[data-show-message-focus="aaaaaaaa"]')
                pill.click()
                page.wait_for_selector(".show-target-picker")
                page.locator(".show-target-picker summary").click()
                load_warning = page.locator(".show-warning-list").inner_text().lower()
                author_warning = page.locator(".show-target-warning").inner_text().lower()
                check("a missing named target warns at Show load and authoring time",
                      "does not exist" in load_warning
                      and "does not exist" in author_warning,
                      repr((load_warning, author_warning)))
                named_chip = page.locator('[data-target-toggle="group:Front"]')
                check("group picker stores a portable name selector",
                      named_chip.count() == 1
                      and named_chip.get_attribute("data-target-legacy") == "g7")
                page.locator(
                    '[data-target-remove="group:Missing"]').click()
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === 'all'")
                named_chip.click()
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === 'Front'")

                def saved_messages():
                    try:
                        return json.loads(show_path.read_text())["items"][0]["messages"]
                    except (OSError, ValueError, KeyError, IndexError):
                        return []

                check("saved Show carries the group name, not the venue id",
                      wait_for(lambda: saved_messages()[0]["target"] == ["group:Front"]
                               if saved_messages() else False),
                      repr(saved_messages()))
                check("picker renders the portable name and current wire id",
                      "Front" in page.locator(
                          '.show-target-summary '
                          '[data-target-remove="group:Front"]').inner_text()
                      and "g7" in named_chip.inner_text()
                      and "-> g7" in page.locator(
                          "#show-wire-preview").inner_text(),
                      page.locator(".show-target-picker").inner_text())

                pill = page.locator('[data-show-message-focus="aaaaaaaa"]')
                pill.focus()
                page.keyboard.press("Control+c")
                page.locator('[data-show-step-row="11111111"]').focus()
                page.keyboard.press("Control+v")
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-message-focus]').length === 2")
                check("copy/paste preserves the validated reference payload",
                      wait_for(lambda: len(saved_messages()) == 2
                               and saved_messages()[1].get("reference") == reference
                               and saved_messages()[1].get("kind") == "reference"),
                      repr(saved_messages()))

                page.keyboard.press("Control+z")
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-message-focus]').length === 1")
                check("one undo removes the paste and leaves the original reference",
                      wait_for(lambda: len(saved_messages()) == 1
                               and saved_messages()[0].get("reference") == reference),
                      repr(saved_messages()))
                # 05g, Bob 2026-07-30: the step list is a spreadsheet. Rows butt
                # against each other, a divider is the same height as a step
                # whatever it contains, and a divider selects exactly like a
                # step. The selection detail is load-bearing: an `outline` with a
                # positive offset paints outside the row, so with rows butted and
                # the list box clipping its scroll area, the ring was cut off on
                # every shared edge. An inset ring cannot be clipped.
                page.click('[data-edit-bar-action="add-divider"]')
                page.wait_for_selector(".show-divider-row")
                geometry = page.evaluate(
                    """() => {
                      const h = s => [...document.querySelectorAll(s)].map(
                        e => getComputedStyle(e).height);
                      return {steps: h('.show-step-row'),
                              dividers: h('.show-divider-row')};
                    }""")
                heights = set(geometry["steps"]) | set(geometry["dividers"])
                check("dividers are the same height as steps",
                      len(heights) == 1 and geometry["dividers"], str(geometry))

                page.click(".show-divider-row")
                page.wait_for_selector(".show-divider-row.focused")
                ring = page.evaluate(
                    """() => { const e =
                        document.querySelector('.show-divider-row.focused');
                      const s = getComputedStyle(e);
                      return {inset: s.boxShadow.includes('inset'),
                              outline: s.outlineStyle, z: s.zIndex}; }""")
                check("a selected divider rings like a step, un-clippable",
                      ring["inset"] and ring["outline"] == "none"
                      and ring["z"] == "2", str(ring))

                check("browser emitted no page errors", not page_errors,
                      repr(page_errors))
                browser.close()
        finally:
            stop(server)
            log.close()

        if FAILURES:
            print("\nserver log tail:\n", log_path.read_text(encoding="utf-8")[-4000:])

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
