#!/usr/bin/env python3
"""Project menu and New Site journey with real OSC simfleet assignments."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright
from verify_fleet_patch_deploy import REPO, UID_A, UID_B, free_port, stop, wait_http, write_patch

sys.path.insert(0, str(Path(REPO) / "dashboard"))
from state import InstallationState


def menu(page):
    page.click("#project-bar")
    page.wait_for_selector("#project-menu:popover-open [data-action=new-site]")


def menu_rows(page, heading):
    """Row names under one menu heading, and which row is highlighted."""
    return page.evaluate("""heading => {
      const rows = [], marks = [];
      let section = null;
      for (const node of document.querySelector('#project-menu').children) {
        if (node.tagName === 'H3') section = node.textContent.trim();
        else if (section === heading && node.classList.contains('project-menu-row')) {
          rows.push(node.querySelector('strong').textContent);
          marks.push(node.classList.contains('current'));
        }
      }
      return {rows, current: rows.filter((_row, index) => marks[index])};
    }""", heading)


def check_order(page, heading, current, rest):
    """Mockup 4: the current row first and highlighted, the rest by name."""
    menu(page)
    seen = menu_rows(page, heading)
    assert seen == {"rows": [current, *rest], "current": [current]}, (heading, seen)
    page.keyboard.press("Escape")


def action(page, name, selector=""):
    menu(page)
    page.locator(f'#project-menu [data-action="{name}"]{selector}').click()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-project-menu-") as temporary:
        root = Path(temporary)
        state = InstallationState(root)
        for key, uid in (("1",UID_A),("2",UID_B)):
            state.seats[key] = {"id":int(key),"name":"Voice "+key,"bound":uid,"groups":[],"params":{}}
            state.data["positions"][key] = [[int(key),2]]
            state.ensure_device_alias(uid)
        state.save()
        plants = state.create_project("The Plants")
        plants.seats["8"] = {"id":8,"name":"Leaf","bound":UID_A,"groups":[],"params":{}}
        plants.data["positions"] = {"8":[[7,8]]}
        plants.data["patches"] = ["beta"]
        plants.data["fleet_patch"] = {"name":"beta","fingerprint":"b"*64}
        plants.save()
        Path(plants.show_path).write_text(json.dumps({"schema":1,"name":"Show","items":[]}))
        patches, assets = root / "patches", root / "assets"
        patches.mkdir(); assets.mkdir()
        write_patch(str(patches), "demo-pd", b"demo")
        write_patch(str(patches), "beta", b"beta")
        http_port, report_port, command_port = free_port(socket.SOCK_STREAM), free_port(socket.SOCK_DGRAM), free_port(socket.SOCK_DGRAM)
        url = f"http://127.0.0.1:{http_port}"
        log_path = root / "dashboard.log"
        server = fleet = None
        with log_path.open("w") as log:
            try:
                server = subprocess.Popen([sys.executable,str(Path(REPO)/"dashboard/server.py"),
                    "--host","127.0.0.1","--port",str(http_port),"--listen-port",str(report_port),
                    "--send-port",str(command_port),"--osc-target","127.0.0.1","--data-dir",str(root),
                    "--patches-dir",str(patches),"--assets-dir",str(assets),"--public-url",url],
                    cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
                wait_http(url,server)
                fleet = subprocess.Popen([sys.executable,str(Path(REPO)/"tools/simfleet.py"),
                    "--devices","2","--target","127.0.0.1","--report-port",str(report_port),
                    "--cmd-port",str(command_port),"--hb-interval","0.2","--patches-dir",str(patches),
                    "--manifest",str(patches/"demo-pd/bopos.patch.json")],cwd=REPO,
                    stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width":1440,"height":900})
                    errors, alerts = [], []
                    page.on("pageerror",lambda error: errors.append(str(error)))
                    prompts = []
                    page.on("dialog",lambda dialog: dialog.accept(prompts.pop(0)) if dialog.type == "prompt" else (alerts.append(dialog.message),dialog.accept()))
                    page.add_init_script("localStorage.setItem('bopos-theme','dark')")
                    page.goto(url)
                    page.wait_for_function("Object.values(installation.devices).filter(d=>d.online).length === 2")
                    menu(page)
                    assert page.locator('#project-menu [data-action=open][data-project="The Plants"]').is_visible()
                    assert "2 Seats · 2 devices" in page.locator('#project-menu').inner_text()
                    screenshot = os.environ.get("BOPOS_PROJECT_MENU_SCREENSHOT")
                    if screenshot: page.screenshot(path=screenshot)
                    page.keyboard.press("Escape")
                    check_order(page, "Project", "default", ["The Plants"])
                    check_order(page, "Site", "default", [])
                    assert not page.locator("#project-menu").is_visible()
                    action(page,"new-site")
                    page.wait_for_selector("#project-site-dialog[open]")
                    assert page.locator("#project-site-source").input_value() == "default"
                    screenshot = os.environ.get("BOPOS_NEW_SITE_SCREENSHOT")
                    if screenshot: page.screenshot(path=screenshot)
                    page.locator("#project-site-name").fill("Town Hall")
                    page.get_by_role("button",name="Create Site",exact=True).click()
                    page.wait_for_function("installation.current_site === 'Town Hall'")
                    assert page.evaluate("installation.seats['1'].positions") == [[1,2]]
                    action(page,"new-site")
                    page.locator("#project-site-name").fill("Empty")
                    page.locator('#project-site-dialog [name=start][value=empty]').check()
                    assert page.locator("#project-site-source").is_disabled()
                    page.get_by_role("button",name="Create Site",exact=True).click()
                    page.wait_for_function("installation.current_site === 'Empty'")
                    assert page.evaluate("installation.seats['1'].positions") == []
                    check_order(page, "Site", "Empty", ["default", "Town Hall"])
                    action(page,"use",'[data-site="Town Hall"]')
                    page.wait_for_function("installation.current_site === 'Town Hall'")
                    check_order(page, "Site", "Town Hall", ["default", "Empty"])
                    registry = (root / "devices.json").read_bytes()
                    action(page,"open",'[data-project="The Plants"]')
                    page.wait_for_function("installation.project === 'The Plants'")
                    page.wait_for_function("uid => installation.devices[uid].id === -1",arg=UID_B)
                    page.wait_for_function("uid => installation.devices[uid].id === 8",arg=UID_A)
                    assert page.evaluate("installation.seats['8'].positions") == [[7,8]]
                    assert page.evaluate("installation.patches") == ["beta"]
                    check_order(page, "Project", "The Plants", ["default"])
                    assert (root / "devices.json").read_bytes() == registry
                    page.reload()
                    page.wait_for_function("installation.project === 'The Plants'")
                    prompts.append("New Leaves")
                    action(page,"rename",'[data-project="The Plants"]')
                    page.wait_for_function("installation.project === 'New Leaves'")
                    assert (root / "projects/New Leaves/shows/Show.json").exists()
                    prompts.append("Empty Project")
                    action(page,"new-project")
                    page.wait_for_function("installation.project === 'Empty Project'")
                    assert page.evaluate("Object.keys(installation.seats).length") == 0
                    assert page.evaluate("installation.patches") == []
                    assert page.evaluate("installation.fleet_patch") is None
                    assert page.evaluate("installation.shows") == ["Show"]
                    assert (root / "projects/Empty Project/shows/Show.json").exists()
                    assert (root / "devices.json").read_bytes() == registry
                    assert not errors, errors
                    assert not alerts, alerts
                    browser.close()
            except Exception:
                print(log_path.read_text()[-6000:])
                raise
            finally:
                stop(fleet); stop(server)
    print("PASS: menu, copied/empty sites, open, unassign outsiders, rename, new project, reload, registry; no browser errors")
    return 0


if __name__ == "__main__": raise SystemExit(main())
