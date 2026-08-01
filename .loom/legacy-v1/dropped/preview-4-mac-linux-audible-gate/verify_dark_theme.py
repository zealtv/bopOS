#!/usr/bin/env python3
"""Verify that both dashboard views remain dark under a light OS theme."""

import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright


def repo_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("repository root not found")


def main():
    static = repo_root() / "dashboard" / "static"
    handler = partial(SimpleHTTPRequestHandler, directory=static)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(color_scheme="light")
            page = context.new_page()
            base = f"http://127.0.0.1:{server.server_port}"
            for path in ("/index.html", "/facilitator.html"):
                page.goto(base + path, wait_until="networkidle")
                scheme = page.evaluate(
                    "getComputedStyle(document.documentElement).colorScheme"
                )
                background = page.evaluate(
                    "getComputedStyle(document.body).backgroundColor"
                )
                foreground = page.evaluate("getComputedStyle(document.body).color")
                assert scheme == "dark only", (path, scheme)
                assert background == "rgb(16, 19, 22)", (path, background)
                assert foreground == "rgb(232, 237, 241)", (path, foreground)
                checks += 3
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    print(f"dark theme verify: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
