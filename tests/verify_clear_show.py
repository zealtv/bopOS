#!/usr/bin/env python3
"""Clear Show (66/9): the Show header's button, its confirm, the cleared show,
and Ctrl+Z bringing it back; off while a step plays and absent without steps.

BOPOS_CLEAR_SHOW_SCREENSHOT=<path> saves the header with the button.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright
from verify_fleet_patch_deploy import REPO, free_port, stop, wait_http
from verify_project_shows import show_tab, step

sys.path.insert(0, str(Path(REPO) / "dashboard"))
from state import InstallationState
import show_model


DIVIDER = {"kind": "divider", "uid": "0000000c", "alias": None}


def button(page):
    return page.locator("#show-root .show-transport-actions [data-show-clear]")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-clear-show-") as temporary:
        root = Path(temporary)
        state = InstallationState(root)
        state.save()
        show_model.save_show(state.show_path, dict(show_model.empty_show("Show"),
            items=[step("0000000a", "Opening"), DIVIDER, step("0000000b", "Bows")]))
        patches, assets = root / "patches", root / "assets"
        patches.mkdir(); assets.mkdir()
        http_port = free_port(socket.SOCK_STREAM)
        url = f"http://127.0.0.1:{http_port}"
        log_path = root / "dashboard.log"
        server = None
        with log_path.open("w") as log:
            try:
                server = subprocess.Popen([sys.executable, str(Path(REPO) / "dashboard/server.py"),
                    "--host", "127.0.0.1", "--port", str(http_port),
                    "--listen-port", str(free_port(socket.SOCK_DGRAM)),
                    "--send-port", str(free_port(socket.SOCK_DGRAM)), "--osc-target", "127.0.0.1",
                    "--data-dir", str(root), "--patches-dir", str(patches), "--assets-dir", str(assets),
                    "--public-url", url], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
                wait_http(url, server)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.set_default_timeout(10000)
                    errors, confirms, answers, alerts = [], [], [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))

                    def on_dialog(dialog):
                        if dialog.type == "confirm":
                            confirms.append(dialog.message)
                            dialog.accept() if answers.pop(0) else dialog.dismiss()
                        else:
                            alerts.append(dialog.message)
                            dialog.accept()
                    page.on("dialog", on_dialog)
                    page.add_init_script("localStorage.setItem('bopos-theme','dark')")
                    page.goto(url)
                    page.click("#tab-button-show")
                    page.wait_for_function("document.querySelectorAll('#show-root .show-step-alias').length === 2")

                    # Beside play, stop and next; styled like the other destructive actions.
                    clear = button(page)
                    assert clear.inner_text() == "Clear Show…"
                    assert "danger" in clear.get_attribute("class")
                    assert page.evaluate("""() => [...document.querySelector('#show-root .show-transport-actions').children]
                      .map(node => node.dataset.showAction || (node.matches('[data-show-clear]') ? 'clear' : '?'))""") == [
                        "step_start", "step_stop", "step_trigger_next", "clear"]
                    shot = os.environ.get("BOPOS_CLEAR_SHOW_SCREENSHOT")
                    if shot: page.screenshot(path=shot, clip={"x": 0, "y": 0, "width": 1440, "height": 320})

                    # Dismissed: nothing changes.
                    answers.append(False)
                    clear.click()
                    page.wait_for_timeout(300)
                    assert show_tab(page)["steps"] == ["Opening", "Bows"]

                    # Accepted: the show empties, keeps its name, and the button goes.
                    answers.append(True)
                    button(page).click()
                    page.wait_for_function("document.querySelectorAll('#show-root .show-step-alias').length === 0")
                    assert confirms == ["Remove all 2 steps from this show? You can undo this."] * 2, confirms
                    assert show_tab(page)["heading"] == "Show"
                    assert page.evaluate("document.querySelectorAll('#show-root [data-show-divider-row]').length") == 0
                    page.wait_for_selector("#show-root [data-show-clear]", state="detached")
                    assert show_model.load_show(state.show_path)[0]["items"] == []

                    # Undo brings every item back.
                    page.locator("body").click(position={"x": 5, "y": 880})
                    page.keyboard.press("Control+z")
                    page.wait_for_function("document.querySelectorAll('#show-root .show-step-alias').length === 2")
                    assert len(show_model.load_show(state.show_path)[0]["items"]) == 3

                    # One step: the singular.
                    page.evaluate("ws.send('remove_item', {uid: '0000000b'})")
                    page.wait_for_function("document.querySelectorAll('#show-root .show-step-alias').length === 1")
                    answers.append(False)
                    button(page).click()
                    page.wait_for_timeout(300)
                    assert confirms[-1] == "Remove all 1 step from this show? You can undo this.", confirms

                    # Off while a step plays; back when it stops.
                    page.evaluate("ws.send('step_start', {uid: '0000000a'})")
                    page.wait_for_selector("#show-root .show-step-playing")
                    assert button(page).is_disabled()
                    page.locator('#show-root .show-transport-strip [data-show-action="step_stop"]').click()
                    page.wait_for_selector("#show-root .show-step-playing", state="detached")
                    assert not button(page).is_disabled()
                    assert not errors, errors
                    assert not alerts, alerts
                    browser.close()
            except Exception:
                print(log_path.read_text()[-6000:])
                raise
            finally:
                stop(server)
    print("PASS: Clear Show button placement and style, confirm (plural and singular), dismiss, clear, "
          "undo, hidden when empty, disabled while playing; no browser errors")
    return 0


if __name__ == "__main__": raise SystemExit(main())
