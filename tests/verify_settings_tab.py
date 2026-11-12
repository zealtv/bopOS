#!/usr/bin/env python3
"""The Settings tab on a real dashboard: read-only facts about the host.

The tab is last in the bar, after OSC. It opens from a click and from a
`#settings` deep link, and its "Dashboard" section shows the release, build
state, commits since the release, git hash, OSC contract version and project
storage schema the server resolved. The host hash shows there and nowhere else
outside tooltips: the Monitor dock's bopOS card carries the short release only,
and the header tooltip points at the tab.
"""
from dashboard_process import launch_dashboard
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
from project_fixture import data_root, project_path
from verify_manifest_param_visibility import FAILURES, ROOT, check, free_port, stop, wait_http

sys.path.insert(0, ROOT)
from python import osc_contract, version_identity  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "dashboard"))
import state as dashboard_state  # noqa: E402

HASH = "abc1234"
FORCED = [  # label, state overrides, facts shown (release, build, ahead, hash)
    ("a tagged release",
     {"host_version": "1.2.3", "host_release": "1.2.3", "host_state": "release",
      "host_ahead": 0, "host_git_rev": HASH},
     ("1.2.3", "release", "0", HASH)),
    ("a development checkout",
     {"host_version": "1.2.3+dev.12.g" + HASH, "host_release": "1.2.3",
      "host_state": "dev", "host_ahead": 12, "host_git_rev": HASH},
     ("1.2.3", "dev", "12", HASH)),
    ("a development checkout with no tag to count from",
     {"host_version": "1.2.3+dev.g" + HASH, "host_release": "1.2.3",
      "host_state": "dev", "host_ahead": None, "host_git_rev": HASH},
     ("1.2.3", "dev", "—", HASH)),
    ("an export without git",
     {"host_version": "1.2.3", "host_release": "1.2.3", "host_state": "export",
      "host_ahead": None, "host_git_rev": None},
     ("1.2.3", "export", "—", "—")),
    ("a host with no VERSION file",
     {"host_version": "unknown", "host_release": None, "host_state": "unknown",
      "host_ahead": None, "host_git_rev": None},
     ("—", "unknown", "—", "—")),
]


def write_fixture(temp):
    os.makedirs(os.path.join(temp, "assets"))
    os.makedirs(os.path.join(temp, "patches"))
    state = str(project_path(temp))
    with open(state, "w", encoding="utf-8") as target:
        json.dump({"schema": 1, "name": "Settings tab rig", "seats": {}}, target)
    return state


def main():
    identity = version_identity.resolve(ROOT)
    with tempfile.TemporaryDirectory(prefix="bopos-settings-tab-") as temp:
        state = write_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w", encoding="utf-8")
        server = launch_dashboard([
            sys.executable, os.path.join(ROOT, "dashboard", "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(free_port(socket.SOCK_DGRAM)),
            "--stream-port", str(free_port(socket.SOCK_DGRAM)),
            "--send-port", str(free_port(socket.SOCK_DGRAM)),
            "--input-port", str(free_port(socket.SOCK_DGRAM)), "--osc-target", "127.0.0.1",
            "--data-dir", data_root(state), "--assets-dir", os.path.join(temp, "assets"),
            "--patches-dir", os.path.join(temp, "patches"),
            "--public-url", base_url, "--sim-no-engine",
        ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
        try:
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.set_default_timeout(10000)
                problems = []
                page.on("pageerror", lambda error: problems.append(str(error)))
                page.on("console", lambda message: problems.append(message.text)
                        if message.type == "error" else None)
                page.on("dialog", lambda dialog: dialog.accept())

                def fact(name):
                    return page.locator(f"#settings-{name}").inner_text().strip()

                def facts():
                    return (fact("release"), fact("state"), fact("ahead"), fact("hash"))

                # ---- the tab bar -------------------------------------------
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                tabs = page.locator('#primary-tabs[role="tablist"] [role="tab"]')
                names = [name.strip().lower() for name in tabs.all_inner_texts()]
                check("Settings is the last tab, after OSC",
                      names[-2:] == ["osc", "settings"] and len(names) == 8, repr(names))
                check("the panel is hidden until its tab opens",
                      not page.locator("#tab-settings").is_visible())

                # ---- opens from a click ------------------------------------
                page.click("#tab-button-settings")
                page.wait_for_selector("#tab-settings:not([hidden])")
                check("the tab is selected", page.get_attribute(
                    "#tab-button-settings", "aria-selected") == "true")
                check("the URL fragment names the tab",
                      page.evaluate("location.hash") == "#settings")
                check("only the Settings panel shows",
                      page.locator('[data-tab-panel]:not([hidden])').count() == 1)
                check("the Dashboard section is titled and read-only",
                      page.locator("#settings-dashboard-title").inner_text().strip().lower() == "dashboard"
                      and page.locator("#tab-settings input, #tab-settings select, "
                                       "#tab-settings textarea, #tab-settings button").count() == 0)

                # ---- the real host's facts ---------------------------------
                page.wait_for_function(
                    "() => document.querySelector('#settings-contract').textContent !== '—'")
                want_ahead = "—" if identity["ahead"] is None else str(identity["ahead"])
                check("release, build, commits and hash match the resolver",
                      facts() == (identity["release"] or "—", identity["state"], want_ahead,
                                  identity["git_hash"] or "—"),
                      f"{facts()} vs {identity}")
                check("the OSC contract is the one the host speaks",
                      fact("contract") == osc_contract.VERSION, fact("contract"))
                check("the project storage schema is the one the host speaks",
                      fact("schema") == str(dashboard_state.SCHEMA), fact("schema"))
                check("the hash looks like a short git hash",
                      identity["git_hash"] is None or re.fullmatch(r"[0-9a-f]{7}", fact("hash")))

                # ---- the hash lives here, not in the Monitor dock ----------
                page.click('[data-monitor-tab="system"]')
                card = page.locator("[data-monitor-system='version']")
                page.wait_for_function(
                    "() => document.querySelector(\"[data-monitor-system='version']\")"
                    "?.textContent !== '—'")
                card_text = card.locator("xpath=..").inner_text()
                check("the Monitor bopOS card shows the short release",
                      card.inner_text().strip() == version_identity.resolve(ROOT)["version"].split(".g")[0],
                      card.inner_text())
                check("the Monitor bopOS card shows no git hash",
                      (identity["git_hash"] or HASH) not in card_text and "git" not in card_text.lower().replace("github", ""),
                      card_text)
                check("the card points to Settings", "settings" in card_text.lower(), card_text)
                title = page.locator("#host-version").get_attribute("title") or ""
                check("the header tooltip points to the Settings tab", "Settings tab" in title, title)

                # ---- keyboard: the arrow keys reach it ------------------------------
                page.click("#tab-button-osc")
                page.focus("#tab-button-osc")
                page.keyboard.press("ArrowRight")
                page.wait_for_selector("#tab-settings:not([hidden])")
                check("ArrowRight from OSC moves to Settings",
                      page.evaluate("document.activeElement.id") == "tab-button-settings")

                # ---- other host situations ---------------------------------
                for label, override, expected in FORCED:
                    page.evaluate(
                        "(o) => ws.handlers.state.forEach((h) => h({...installation, ...o}))", override)
                    check(f"the facts read right for {label}", facts() == expected, repr(facts()))
                page.evaluate(
                    "() => ws.handlers.state.forEach((h) => h({...installation,"
                    " osc_contract_version: '9.99', storage_schema: 7}))")
                check("contract and schema follow the snapshot",
                      fact("contract") == "9.99" and fact("schema") == "7")

                # ---- the deep link -----------------------------------------
                page.goto(base_url + "#settings")
                page.reload()
                page.wait_for_selector("#tab-settings:not([hidden])")
                check("the #settings deep link opens the tab on load",
                      page.get_attribute("#tab-button-settings", "aria-selected") == "true")
                page.wait_for_function(
                    "() => document.querySelector('#settings-contract').textContent !== '—'")
                check("a deep-linked load fills the facts (the snapshot reaches a late handler)",
                      fact("contract") == osc_contract.VERSION)
                page.evaluate("location.hash = '#osc'")
                page.wait_for_selector("#tab-osc:not([hidden])")
                page.evaluate("location.hash = '#settings'")
                page.wait_for_selector("#tab-settings:not([hidden])")
                check("hashchange moves between OSC and Settings",
                      page.locator("#tab-osc").is_hidden()
                      and page.get_attribute("#tab-button-settings", "aria-selected") == "true")

                # ---- narrow width ------------------------------------------
                page.set_viewport_size({"width": 390, "height": 900})
                time.sleep(.3)
                widths = page.evaluate(
                    "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                check("no horizontal page scroll at phone width", widths[0] <= widths[1], str(widths))
                page.locator("#tab-button-settings").scroll_into_view_if_needed()
                check("the Settings tab stays reachable at phone width",
                      page.locator("#tab-button-settings").is_visible())
                check("no page or console errors", not problems, "; ".join(problems))
                browser.close()
        finally:
            stop(server)
            server_log.close()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("Settings tab checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
