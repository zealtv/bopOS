#!/usr/bin/env python3
"""The project menu's Show section: open, New Show, rename, delete, and refusal
while a show plays, with the Show tab and the bar following the open show.

Screenshots, when set: BOPOS_SHOW_MENU_SCREENSHOT (the menu),
BOPOS_NEW_SHOW_SCREENSHOT (the dialog) and BOPOS_SHOW_BAR_SCREENSHOT (the
header at 1440, 900 and 420px; the width is added to the file name).
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright
from verify_fleet_patch_deploy import REPO, free_port, stop, wait_http
from verify_project_menu import menu_rows

sys.path.insert(0, str(Path(REPO) / "dashboard"))
from state import InstallationState
import show_model


def step(uid, alias):
    return {"kind": "step", "uid": uid, "alias": alias, "duration_s": 60, "play_count": 1,
            "then_actions": [{"type": "stop"}], "messages": []}


def menu(page):
    page.click("#project-bar")
    page.wait_for_selector("#project-menu:popover-open [data-action=new-show]")


def action(page, name, show=None):
    menu(page)
    selector = f'#project-menu [data-action="{name}"]' + (f'[data-show="{show}"]' if show else "")
    page.locator(selector).click()


def show_tab(page):
    """The open show's heading and step names, as the Show tab draws them."""
    return page.evaluate("""() => ({
      heading: document.querySelector('#show-root h2')?.textContent,
      steps: [...document.querySelectorAll('#show-root .show-step-alias')].map(node => node.textContent)})""")


def wait_show(page, name):
    page.wait_for_function("name => installation.current_show === name"
                           " && document.querySelector('#show-root h2')?.textContent === name"
                           " && document.querySelector('#project-bar-show').textContent === name", arg=name)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-project-shows-") as temporary:
        root = Path(temporary)
        state = InstallationState(root)
        state.data["current_show"] = "Main"
        state.save()
        show_model.save_show(state.show_file("Main"), dict(show_model.empty_show("Main"), items=[step("0000000a", "Opening")]))
        show_model.save_show(state.show_file("Encore"), dict(show_model.empty_show("Encore"), items=[step("0000000b", "Bows")]))
        patches, assets = root / "patches", root / "assets"
        patches.mkdir(); assets.mkdir()
        http_port, report_port, command_port = free_port(socket.SOCK_STREAM), free_port(socket.SOCK_DGRAM), free_port(socket.SOCK_DGRAM)
        url = f"http://127.0.0.1:{http_port}"
        log_path = root / "dashboard.log"
        server = None
        with log_path.open("w") as log:
            try:
                server = subprocess.Popen([sys.executable, str(Path(REPO) / "dashboard/server.py"),
                    "--host", "127.0.0.1", "--port", str(http_port), "--listen-port", str(report_port),
                    "--send-port", str(command_port), "--osc-target", "127.0.0.1", "--data-dir", str(root),
                    "--patches-dir", str(patches), "--assets-dir", str(assets), "--public-url", url],
                    cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
                wait_http(url, server)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.set_default_timeout(10000)
                    errors, alerts, confirms, answers, prompts = [], [], [], [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))

                    def on_dialog(dialog):
                        if dialog.type == "prompt":
                            dialog.accept(prompts.pop(0))
                        elif dialog.type == "confirm":
                            confirms.append(dialog.message)
                            dialog.accept() if answers.pop(0) else dialog.dismiss()
                        else:
                            alerts.append(dialog.message)
                            dialog.accept()
                    page.on("dialog", on_dialog)
                    page.add_init_script("localStorage.setItem('bopos-theme','dark')")
                    page.goto(url)
                    page.click("#tab-button-show")
                    wait_show(page, "Main")
                    assert show_tab(page)["steps"] == ["Opening"]
                    assert page.get_attribute("#project-bar", "aria-label") == "Project · Site · Patch · Show"

                    # Mockup 4: SHOW after SITE, the open show first with Rename,
                    # the others with Open and Delete, then New Show.
                    menu(page)
                    assert menu_rows(page, "Show") == {"rows": ["Main", "Encore"], "current": ["Main"]}
                    labels = page.evaluate("""() => [...document.querySelectorAll('#project-menu .project-menu-actions')]
                      .map(row => [...row.querySelectorAll('button')].map(button => button.textContent))""")
                    assert labels == [["Rename"], ["Open", "Delete"]], labels
                    headings = page.locator("#project-menu h3").all_inner_texts()
                    assert [heading.lower() for heading in headings] == ["project", "site", "show"], headings
                    shot = os.environ.get("BOPOS_SHOW_MENU_SCREENSHOT")
                    if shot: page.screenshot(path=shot)
                    page.keyboard.press("Escape")

                    # Opening another show: the Show tab and the bar follow it.
                    action(page, "open-show", "Encore")
                    wait_show(page, "Encore")
                    assert show_tab(page)["steps"] == ["Bows"]

                    # New Show, a copy of an existing one (the default) or empty.
                    action(page, "new-show")
                    page.wait_for_selector("#project-show-dialog[open]")
                    dialog = page.locator("#project-show-dialog")
                    assert dialog.locator("h2").inner_text() == "New Show"
                    assert dialog.locator("label").first.inner_text().startswith("Name")
                    assert dialog.locator("legend").inner_text() == "Start from"
                    options = page.evaluate("""() => [...document.querySelectorAll('#project-show-dialog fieldset label')]
                      .map(label => [...label.childNodes].filter(node => node.nodeType === 3).map(node => node.textContent).join('').trim())""")
                    assert options == ["An empty show", "An existing show"], options
                    assert page.locator("#project-show-source").input_value() == "Encore"
                    assert dialog.locator("footer button").all_inner_texts() == ["Cancel", "Create Show"]
                    page.locator("#project-show-name").fill("Encore Copy")
                    shot = os.environ.get("BOPOS_NEW_SHOW_SCREENSHOT")
                    if shot: page.screenshot(path=shot)
                    page.get_by_role("button", name="Create Show", exact=True).click()
                    wait_show(page, "Encore Copy")
                    assert show_tab(page)["steps"] == ["Bows"]
                    action(page, "new-show")
                    page.locator("#project-show-name").fill("Blank")
                    page.locator("#project-show-dialog [name=start][value=empty]").check()
                    assert page.locator("#project-show-source").is_disabled()
                    page.get_by_role("button", name="Create Show", exact=True).click()
                    wait_show(page, "Blank")
                    assert show_tab(page)["steps"] == []
                    action(page, "new-show")
                    page.locator("#project-show-name").fill("Never")
                    page.locator("#project-show-cancel").click()
                    page.wait_for_selector("#project-show-dialog:not([open])", state="attached")
                    assert "Never" not in page.evaluate("installation.shows")

                    # Rename the open show.
                    prompts.append("Blank Slate")
                    action(page, "rename-show", "Blank")
                    wait_show(page, "Blank Slate")
                    assert (root / "projects/default/shows/Blank Slate.json").exists()
                    assert not (root / "projects/default/shows/Blank.json").exists()

                    # Delete another show, after confirming.
                    answers.append(False)
                    action(page, "delete-show", "Encore Copy")
                    page.wait_for_timeout(300)
                    assert (root / "projects/default/shows/Encore Copy.json").exists()
                    answers.append(True)
                    action(page, "delete-show", "Encore Copy")
                    page.wait_for_function("!installation.shows.includes('Encore Copy')")
                    assert confirms == ['Delete show "Encore Copy"? This can\'t be undone.'] * 2, confirms
                    assert not (root / "projects/default/shows/Encore Copy.json").exists()
                    menu(page)
                    assert menu_rows(page, "Show") == {"rows": ["Blank Slate", "Encore", "Main"], "current": ["Blank Slate"]}
                    page.keyboard.press("Escape")

                    # While a show plays, every show action is off, and the
                    # server refuses one sent anyway.
                    action(page, "open-show", "Main")
                    wait_show(page, "Main")
                    page.evaluate("ws.send('step_start', {uid: '0000000a'})")
                    page.wait_for_selector("#show-root .show-step-playing")
                    menu(page)
                    disabled = page.evaluate("""() => [...document.querySelectorAll(
                      '#project-menu [data-action$="-show"]')].map(button => [button.dataset.action, button.disabled])""")
                    assert disabled and all(off for _action, off in disabled), disabled
                    assert not page.locator('#project-menu [data-action=new-site]').is_disabled()
                    page.keyboard.press("Escape")
                    # On the Show tab the error lands in its inspector, not an alert.
                    page.evaluate("window.refusals = []; ws.on('error', data => refusals.push(data.message))")
                    page.evaluate("ws.send('open_show', {name: 'Encore'})")
                    page.wait_for_function("refusals.length > 0")
                    assert page.evaluate("refusals") == ["That show could not be opened."]
                    assert page.evaluate("installation.current_show") == "Main"
                    page.evaluate("ws.send('stop_all_steps')")
                    page.wait_for_selector("#show-root .show-step-playing", state="detached")
                    action(page, "open-show", "Encore")
                    wait_show(page, "Encore")
                    page.reload()
                    page.click("#tab-button-show")
                    wait_show(page, "Encore")

                    # The bar at the 66/8 widths: four parts, nothing spilling.
                    for width in (1440, 900, 420):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.wait_for_timeout(100)
                        fits = page.evaluate("""() => {
                          const bar = document.querySelector('#project-bar').getBoundingClientRect();
                          const header = document.querySelector('header');
                          return {right: bar.right, width: innerWidth, scroll: document.documentElement.scrollWidth,
                                  header: header.scrollWidth <= header.clientWidth,
                                  parts: [...document.querySelectorAll('#project-bar strong')].map(node => node.textContent)}
                        }""")
                        assert fits["right"] <= fits["width"] and fits["scroll"] <= fits["width"] and fits["header"], (width, fits)
                        assert fits["parts"] == ["default", "default", "—", "Encore"], fits
                        shot = os.environ.get("BOPOS_SHOW_BAR_SCREENSHOT")
                        if shot:
                            path = Path(shot)
                            page.screenshot(path=str(path.with_name(f"{path.stem}-{width}{path.suffix}")),
                                            clip={"x": 0, "y": 0, "width": width, "height": 130})
                    assert not errors, errors
                    assert not alerts, alerts
                    browser.close()
            except Exception:
                print(log_path.read_text()[-6000:])
                raise
            finally:
                stop(server)
    print("PASS: Show menu section, open, New Show copy/empty/cancel, rename, delete with confirm, "
          "playback refusal, reload, bar at 1440/900/420; no browser errors")
    return 0


if __name__ == "__main__": raise SystemExit(main())
