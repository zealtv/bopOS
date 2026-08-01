#!/usr/bin/env python3
"""Playwright verification for Monitor wide split/snap and persistence."""

import json
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
HERE = Path(__file__).resolve().parent
FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    while True:
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


def fixture(root):
    root = Path(root)
    patch = root / "patches" / "alpha"
    assets = root / "assets"
    state_dir = root / "sim-state"
    shows = root / "shows"
    for directory in (patch, assets, state_dir, shows):
        directory.mkdir(parents=True, exist_ok=True)
    (patch / "main.bin").write_bytes(b"monitor-split")
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps({
        "engine": "test", "entrypoint": "main.bin",
        "params": [], "cues": [], "caps": [], "slots": [],
    }), encoding="utf-8")
    state_path = root / "installation.json"
    state_path.write_text(json.dumps({
        "schema": 1, "name": "Monitor split", "current_show": "monitor",
        "seats": {}, "groups": {}, "next_group_id": 0,
    }), encoding="utf-8")
    (shows / "monitor.json").write_text(json.dumps({
        "schema": 1, "name": "monitor", "items": [],
    }), encoding="utf-8")
    return patch.parent, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-monitor-split-") as root:
        patches, assets, state_dir, manifest_path, state_path = fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = Path(root, "server.log").open("w", encoding="utf-8")
        fleet_log = Path(root, "fleet.log").open("w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1280, "height": 850})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("[data-monitor-collapse]")
                page.wait_for_timeout(500)
                check("Monitor initializes without browser errors",
                      not errors, "; ".join(errors))
                page.wait_for_function(
                    "() => document.querySelector('[data-console=\"out\"] "
                    "[data-console-log]').textContent.includes('/sync/ping')")
                check("traffic rendering survives pane refactor",
                      "/sync/ping" in page.locator(
                          '[data-console="out"] [data-console-log]').inner_text())

                source = page.locator('[data-monitor-tab="reports"]')
                target = page.locator('[data-monitor-pane="right"]')
                source_box = source.bounding_box()
                page.mouse.move(
                    source_box["x"] + source_box["width"] / 2,
                    source_box["y"] + source_box["height"] / 2)
                page.mouse.down()
                page.mouse.move(
                    source_box["x"] + source_box["width"] / 2 + 30,
                    source_box["y"] + source_box["height"] / 2, steps=4)
                page.wait_for_function(
                    "() => !document.querySelector('[data-monitor-pane=\"right\"]').hidden")
                check("drag exposes visible pane drop targets",
                      page.locator("#monitor-dock.monitor-drag-active").count() == 1
                      and target.is_visible())
                page.mouse.move(5, 5, steps=4)
                page.mouse.up()
                page.wait_for_function(
                    "() => !document.querySelector('#monitor-dock').classList.contains('monitor-drag-active')")
                check("aborted drag restores one-pane layout",
                      page.locator("#monitor-dock.monitor-split").count() == 0)

                source_box = source.bounding_box()
                page.mouse.move(
                    source_box["x"] + source_box["width"] / 2,
                    source_box["y"] + source_box["height"] / 2)
                page.mouse.down()
                page.mouse.move(
                    source_box["x"] + source_box["width"] / 2 + 30,
                    source_box["y"] + source_box["height"] / 2, steps=4)
                page.wait_for_function(
                    "() => !document.querySelector('[data-monitor-pane=\"right\"]').hidden")
                target_box = target.bounding_box()
                page.mouse.move(
                    target_box["x"] + target_box["width"] / 2,
                    target_box["y"] + target_box["height"] / 2, steps=8)
                page.mouse.up()
                page.wait_for_function(
                    "() => document.querySelector('#monitor-dock').classList.contains('monitor-split')")
                rects = page.evaluate("""() => {
                  const rect = selector => {
                    const value = document.querySelector(selector).getBoundingClientRect();
                    return {left:value.left,right:value.right,width:value.width};
                  };
                  return {left:rect('[data-monitor-pane="left"]'),
                          right:rect('[data-monitor-pane="right"]')};
                }""")
                check("wide drag creates two non-overlapping panes",
                      rects["left"]["right"] <= rects["right"]["left"]
                      and rects["left"]["width"] > 0 and rects["right"]["width"] > 0,
                      str(rects))
                check("dragged tab occupies the right pane",
                      page.locator(
                          '[data-monitor-pane="right"] [data-monitor-tab="reports"]')
                          .count() == 1)
                splitter = page.locator("[data-monitor-split-resize]")
                splitter.focus()
                splitter.press("ArrowRight")
                resized = page.evaluate("""() => {
                  const left = document.querySelector('[data-monitor-pane="left"]')
                    .getBoundingClientRect().width;
                  const right = document.querySelector('[data-monitor-pane="right"]')
                    .getBoundingClientRect().width;
                  return {left,right};
                }""")
                check("keyboard split resize changes the persisted ratio",
                      resized["left"] > resized["right"], str(resized))
                page.screenshot(path=HERE / "monitor-split.png")

                page.reload()
                page.wait_for_selector("#monitor-dock")
                if "is-collapsed" in (
                        page.locator("#monitor-dock").get_attribute("class") or ""):
                    page.click("[data-monitor-collapse]")
                check("wide split persists across reload",
                      page.locator("#monitor-dock.monitor-split").count() == 1
                      and page.locator(
                          '[data-monitor-pane="right"] [data-monitor-tab="reports"]')
                          .count() == 1)

                page.set_viewport_size({"width": 760, "height": 850})
                page.wait_for_function(
                    "() => !document.querySelector('#monitor-dock').classList.contains('monitor-split')")
                check("narrow view falls back to one canonical tab strip",
                      page.locator('[data-monitor-pane="right"]:visible').count() == 0
                      and page.locator(
                          '[data-monitor-pane="left"] [data-monitor-tab]').count() == 5)
                check("narrow tabs expose no drag affordance",
                      page.locator('[data-monitor-tab="reports"]')
                          .evaluate("tab => !tab.draggable"))
                page.screenshot(path=HERE / "monitor-narrow.png")

                page.set_viewport_size({"width": 1280, "height": 850})
                page.wait_for_function(
                    "() => document.querySelector('#monitor-dock').classList.contains('monitor-split')")
                left_menu = page.locator(
                    '[data-monitor-pane="left"] .monitor-tab-menu summary')
                left_menu.click()
                page.locator(
                    '[data-monitor-pane="left"] [data-monitor-move="single"]').click()
                check("keyboard menu returns tabs to one pane",
                      page.locator("#monitor-dock.monitor-split").count() == 0
                      and page.locator(
                          '[data-monitor-pane="left"] [data-monitor-tab]').count() == 5)
                check("no browser errors after interactions",
                      not errors, "; ".join(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
            return 1
        print("\n12/12 Monitor split checks passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
