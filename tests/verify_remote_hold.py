#!/usr/bin/env python3
"""Remote destructive commands require an uninterrupted hold on a live card."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
REPO = next(path for path in Path(__file__).resolve().parents
            if (path / "tools/simfleet.py").exists())


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(3000)
        page.route("http://hold.test/**", lambda route: route.fulfill(
            body='<div id="root"></div>', content_type="text/html"))
        page.goto("http://hold.test/")
        page.evaluate("""() => {
          window.installation = {devices: {}, groups: {},
            seats: {0: {id: 0, name: 'Seat 0', params: {}}},
            facilitator_commands: ['reboot', 'shutdown', 'updatebopos']};
          window.sent = []; window.GroupSlots = {palette: []};
        }""")
        for script in ("target-picker.js", "control-surface.js", "control-column.js"):
            page.add_script_tag(content=(REPO / "dashboard/static/js" / script).read_text())
        page.evaluate("""() => {
          window.column = ControlColumn.create({host: document.querySelector('#root'),
            getState: () => installation, isInteracting: () => false,
            sendCommand: payload => sent.push(payload),
            capabilities: {targetPicker: false, deriveAllTargets: true, deviceCommands: true}});
          column.render();
        }""")

        def press(verb):
            page.locator('[data-command-key="all:all"]').evaluate("node => node.open = true")
            button = page.locator(f'[data-live-scope="all"][data-target-command="{verb}"]')
            box = button.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            assert button.evaluate("node => node.classList.contains('holding')")

        for verb in ("reboot", "shutdown", "updatebopos"):
            # Review reproduction: a render mid-hold waits for the hold, so the
            # release reaches the held button and nothing is sent.
            press(verb)
            page.evaluate("window.oldButton = document.querySelector('.holding'); column.render()")
            assert page.evaluate("oldButton.isConnected"), "render replaced the held button"
            page.mouse.up()
            page.wait_for_timeout(1300)
            assert page.evaluate("sent") == [], f"released {verb} hold sent"
            assert page.evaluate("!oldButton.isConnected"), "deferred render never ran"

            # A heartbeat refresh during a hold does not cancel it.
            press(verb)
            page.evaluate("column.refresh(installation)")
            page.wait_for_timeout(1300)
            assert page.evaluate("sent") == [{"scope": "all", "verb": verb}], f"{verb} hold lost to refresh"
            page.mouse.up()
            page.evaluate("sent.length = 0")

            for cancellation in (
                "document.body.dispatchEvent(new PointerEvent('pointerup', {bubbles: true}))",
                "document.body.dispatchEvent(new PointerEvent('pointercancel', {bubbles: true}))",
                "document.querySelector('.holding').dispatchEvent(new PointerEvent('pointerleave'))",
                "window.dispatchEvent(new Event('blur'))",
                "Object.defineProperty(document, 'hidden', {configurable: true, value: true}); "
                "document.dispatchEvent(new Event('visibilitychange'))",
            ):
                press(verb)
                page.evaluate(cancellation)
                # Check cancellation itself, before a physical release can mask it.
                page.wait_for_timeout(1300)
                assert page.evaluate("sent") == [], f"{verb} sent after {cancellation}"
                page.mouse.up()
                page.evaluate("Object.defineProperty(document, 'hidden', {configurable: true, value: false})")

            press(verb)
            page.wait_for_timeout(1300)
            assert page.evaluate("sent") == [{"scope": "all", "verb": verb}]
            page.mouse.up()
            page.wait_for_timeout(1300)
            assert page.evaluate("sent.length") == 1, "completed hold sent twice"
            page.evaluate("sent.length = 0")

        press("reboot")
        page.evaluate("column.destroy()")
        page.wait_for_timeout(1300)
        assert page.evaluate("sent") == [], "destroyed column sent"
        page.mouse.up()
        browser.close()
    print("PASS: Remote render/release, cancellation, completed holds and destroy")


if __name__ == "__main__":
    main()
