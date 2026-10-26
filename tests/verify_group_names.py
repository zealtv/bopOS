#!/usr/bin/env python3
"""Group editor feedback and authoritative server validation, on private ports."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright
from project_fixture import data_root
from verify_control_tab import REPO, make_fixture, free_port, stop_process, wait_http


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-group-names-") as temporary:
        state_path = make_fixture(temporary)
        http_port = free_port(socket.SOCK_STREAM)
        url = f"http://127.0.0.1:{http_port}"
        server = None
        with open(os.path.join(temporary, "server.log"), "w") as log:
            try:
                server = subprocess.Popen([
                    sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                    "--host", "127.0.0.1", "--port", str(http_port),
                    "--listen-port", str(free_port(socket.SOCK_DGRAM)),
                    "--stream-port", str(free_port(socket.SOCK_DGRAM)),
                    "--send-port", str(free_port(socket.SOCK_DGRAM)),
                    "--osc-target", "127.0.0.1", "--data-dir", data_root(state_path),
                    "--assets-dir", os.path.join(temporary, "assets"),
                    "--patches-dir", os.path.join(temporary, "patches"),
                ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
                wait_http(url, server)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.set_default_timeout(10000)
                    errors, sent, answers = [], [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("websocket", lambda ws: ws.on("framesent", lambda payload: sent.append(json.loads(payload))))
                    page.on("dialog", lambda dialog: dialog.dismiss() if not answers else dialog.accept(answers.pop(0)))
                    page.goto(url + "#seats")
                    page.wait_for_selector("#ws-status.online")
                    page.locator("#group-sidebar-tab").click()
                    page.wait_for_function("() => !!document.querySelector('#group-create')?.onclick")

                    def mutations():
                        return [msg for msg in sent if msg.get("type") in {"create_group", "rename_group"}]

                    for name in ["Front", "all", "bop", "g12", "123", "os", "io", "sync", "e", "p", "two words", "a" * 33, ""]:
                        answers.append(name)
                        page.locator("#group-create").click()
                        assert "1–32 lowercase" in page.locator("#group-limit").inner_text()
                        assert not mutations(), name
                    answers.append("front")
                    page.locator("#group-create").click()
                    assert "unique" in page.locator("#group-limit").inner_text()
                    assert not mutations()
                    answers.append("rear_1")
                    page.locator("#group-create").click()
                    page.wait_for_selector('[data-group-rename="1"]', state="attached")
                    assert len(mutations()) == 1
                    page.locator('.group-overflow').last.locator('summary').click()
                    answers.append("all")
                    page.locator('[data-group-rename="1"]').click()
                    assert "Reserved names" in page.locator("#group-limit").inner_text()
                    assert len(mutations()) == 1
                    page.locator('.group-overflow').last.locator('summary').click()
                    answers.append("rear-2")
                    page.locator('[data-group-rename="1"]').click()
                    page.wait_for_function("() => installation.groups['1']?.name === 'rear-2'")
                    # Bypass the editor: a hostile/stale client still cannot write an invalid name.
                    with page.expect_event("dialog") as rejection:
                        page.evaluate("() => ws.send('rename_group', {id: 1, name: 'g12'})")
                    assert "Reserved names:" in rejection.value.message
                    page.reload()
                    page.wait_for_selector("#ws-status.online")
                    page.wait_for_function("() => installation.groups['1']?.name === 'rear-2'")
                    assert json.loads(Path(state_path).read_text())["groups"]["1"]["name"] == "rear-2"
                    assert not errors, errors
                    browser.close()
            finally:
                stop_process(server)
    print("PASS: group create/rename feedback, reserved targets, uniqueness, persistence and server rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
