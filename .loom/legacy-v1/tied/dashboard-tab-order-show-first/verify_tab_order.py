#!/usr/bin/env python3
"""Focused browser verification for the Show-first primary tab order."""

import importlib.util
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
HERE = Path(__file__).resolve().parent
HELPER_PATH = (ROOT / ".loom" / "tied" / "dashboard-light-theme-feedback"
               / "verify_light_feedback.py")
SPEC = importlib.util.spec_from_file_location("light_feedback_helper", HELPER_PATH)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def selected(page):
    return page.locator('#primary-tabs [aria-selected="true"]').get_attribute("data-tab")


def main():
    readme = (ROOT / "dashboard" / "README.md").read_text(encoding="utf-8")
    check("operator README lists the Show-first order",
          "Show, Dashboard, Seats, Devices, Patches,\n  and Assets tabs" in readme)

    with tempfile.TemporaryDirectory(prefix="bopos-tab-order-") as temp:
        state_path = HELPER.make_fixture(temp)
        http_port = HELPER.free_port(socket.SOCK_STREAM)
        listen_port = HELPER.free_port(socket.SOCK_DGRAM)
        send_port = HELPER.free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = Path(temp) / "server.log"
        log = log_path.open("w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard" / "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(send_port),
            "--osc-target", "127.0.0.1", "--state-file", str(state_path),
            "--patches-dir", str(Path(temp) / "patches"),
            "--assets-dir", str(Path(temp) / "assets"), "--public-url", base_url,
        ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            HELPER.wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1180, "height": 820})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text)
                        if message.type == "error" else None)
                page.goto(base_url)
                page.wait_for_selector("#initial-loading", state="hidden")

                labels = page.locator("#primary-tabs [role=tab]").all_inner_texts()
                check("primary tabs render in the accepted order", labels == [
                    "Show", "Dashboard", "Seats", "Devices", "Patches", "Assets",
                ], repr(labels))
                check("Show is the default selected and visible workspace",
                      selected(page) == "show"
                      and page.locator("#tab-show").is_visible()
                      and not page.locator("#tab-dashboard").is_visible())

                page.goto(base_url + "/#dashboard")
                page.wait_for_selector("#initial-loading", state="hidden")
                check("Dashboard remains directly addressable by hash",
                      selected(page) == "dashboard"
                      and page.locator("#tab-dashboard").is_visible())
                page.click("#tab-button-devices")
                check("click navigation retains the existing hash contract",
                      selected(page) == "devices"
                      and page.url.endswith("#devices"))

                page.click("#tab-button-show")
                page.locator("#tab-button-show").press("ArrowRight")
                check("ArrowRight follows Show to Dashboard",
                      selected(page) == "dashboard"
                      and page.locator("#tab-button-dashboard").evaluate(
                          "element => document.activeElement === element"))
                page.locator("#tab-button-dashboard").press("ArrowLeft")
                check("ArrowLeft returns Dashboard to Show", selected(page) == "show")
                page.locator("#tab-button-show").press("End")
                check("End selects the final Assets tab", selected(page) == "assets")
                page.locator("#tab-button-assets").press("Home")
                check("Home selects the first Show tab", selected(page) == "show")

                page.set_viewport_size({"width": 420, "height": 820})
                compact = page.evaluate("""() => {
                  const nav=document.querySelector('#primary-tabs');
                  const first=document.querySelector('#tab-button-show').getBoundingClientRect();
                  return {scrollWidth:nav.scrollWidth,clientWidth:nav.clientWidth,
                    scrollLeft:nav.scrollLeft,firstLeft:first.left};
                }""")
                check("compact navigation exposes Show at the leading edge",
                      compact["scrollLeft"] == 0 and compact["firstLeft"] >= 0,
                      repr(compact))
                page.screenshot(path=HERE / "review-show-first-tabs.png", full_page=True)
                check("browser emitted no errors", not errors, repr(errors))
                browser.close()
        finally:
            HELPER.stop(server)
            log.close()

        if FAILURES:
            print("\nserver log tail:\n" + log_path.read_text(encoding="utf-8")[-4000:])
            raise SystemExit(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        print("\nAll Show-first tab-order checks passed.")


if __name__ == "__main__":
    main()
