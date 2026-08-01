#!/usr/bin/env python3
"""Focused browser verification for Bob's light-theme and header feedback."""

import json
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
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
HERE = Path(__file__).resolve().parent
FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    probe = socket.socket(socket.AF_INET, kind)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
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
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def make_fixture(root):
    root = Path(root)
    (root / "patches").mkdir()
    (root / "assets").mkdir()
    (root / "shows").mkdir()
    state = {
        "schema": 1, "name": "Light feedback", "current_show": "feedback",
        "room": {"width": 10, "depth": 8, "origin": [0, 0]},
        "seats": {
            "0": {"id": 0, "name": "Seat Zero", "positions": [[3, 3]],
                  "groups": [0, 1], "bound": None, "patch": None, "params": {}},
        },
        "groups": {
            "0": {"id": 0, "name": "Cyan group"},
            "1": {"id": 1, "name": "Amber group"},
        },
        "next_group_id": 2,
    }
    messages = [{
        "uid": f"aaaa000{index}", "alias": f"message {index + 1}",
        "address": "/test", "target": ["0"],
        "args": [{"type": "i", "value": index}],
    } for index in range(8)]
    show = {
        "schema": 1, "name": "feedback", "items": [{
            "kind": "step", "uid": "11111111", "alias": "Light palette",
            "messages": messages, "duration_s": 5, "play_count": 1,
            "then_actions": [{"type": "stop"}],
        }],
    }
    state_path = root / "installation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (root / "shows" / "feedback.json").write_text(
        json.dumps(show), encoding="utf-8")
    return state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-light-feedback-") as temp:
        state_path = make_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
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
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text)
                        if message.type == "error" else None)
                page.goto(base_url)
                page.wait_for_selector("#initial-loading", state="hidden")
                page.select_option("#theme-select", "light")

                header = page.evaluate("""() => {
                    const box = selector => document.querySelector(selector).getBoundingClientRect();
                    return {
                        copy: document.querySelector('.execution-copy, #mode-status'),
                        groupName: document.querySelector('#execution-target').getAttribute('aria-label'),
                        pressed: [...document.querySelectorAll('[data-execution-target]')]
                            .filter(button => button.getAttribute('aria-pressed') === 'true').length,
                        brand: box('.app-brand'), mode: box('#execution-target'),
                        health: box('.app-health'), mute: box('#mute-all'), theme: box('.theme-control'),
                    };
                }""")
                check("redundant execution copy is removed", header["copy"] is None)
                check("mode group keeps its accessible name and one selection",
                      header["groupName"] == "Execution target" and header["pressed"] == 1,
                      repr(header))
                page.evaluate("installation.supervisor = {mode:'simulate'}; renderHeader()")
                check("mode state still updates without the removed duplicate output",
                      page.get_attribute('[data-execution-target="simulate"]', "aria-pressed") == "true"
                      and page.get_attribute('[data-execution-target="off"]', "aria-pressed") == "false")
                page.evaluate("installation.supervisor = {mode:'off'}; renderHeader()")
                ordered = (header["brand"]["right"] < header["mode"]["left"]
                           < header["health"]["left"] < header["mute"]["left"]
                           < header["theme"]["left"])
                check("desktop header follows identity-mode-health-safety-appearance", ordered,
                      repr(header))

                semantic = page.evaluate(r"""() => {
                    const root = getComputedStyle(document.documentElement);
                    const status = getComputedStyle(document.querySelector('#ws-status'));
                    const panel = getComputedStyle(document.querySelector('header'));
                    const resolve = value => {
                        const node = document.createElement('i'); node.style.color = value;
                        document.body.append(node); const result = getComputedStyle(node).color;
                        node.remove(); return result;
                    };
                    const lum = value => {
                        const rgb = value.match(/\d+/g).slice(0,3).map(Number).map(v => v / 255)
                            .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
                        return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2];
                    };
                    const ratio = (a,b) => { const values=[lum(a),lum(b)].sort((x,y)=>y-x);
                        return (values[0]+.05)/(values[1]+.05); };
                    const green = resolve(root.getPropertyValue('--green'));
                    const auto = resolve(root.getPropertyValue('--auto'));
                    const oldAuto = resolve('#2464a8');
                    const white = resolve('#ffffff');
                    return {green, auto, status:status.color, surface:panel.backgroundColor,
                        greenRatio:ratio(green,panel.backgroundColor), autoRatio:ratio(auto,white),
                        autoLighter:lum(auto)>lum(oldAuto)};
                }""")
                check("connected text uses the darker light-theme green",
                      semantic["green"] == semantic["status"] == "rgb(15, 111, 63)"
                      and semantic["greenRatio"] >= 4.5, repr(semantic))
                check("light LFO sweeper is lighter and remains a 3:1 mark",
                      semantic["auto"] == "rgb(79, 127, 184)"
                      and semantic["autoLighter"] and semantic["autoRatio"] >= 3,
                      repr(semantic))

                page.click("#tab-button-show")
                page.wait_for_selector(".show-pill-7")
                pills = page.locator(".show-message-pill").evaluate_all(r"""elements => {
                    const lum = value => value.match(/\d+/g).slice(0,3).map(Number).map(v=>v/255)
                        .map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4)
                        .reduce((sum,v,index)=>sum+v*[.2126,.7152,.0722][index],0);
                    return elements.slice(0,8).map(element => { const css=getComputedStyle(element);
                        const values=[lum(css.color),lum(css.backgroundColor)].sort((a,b)=>b-a);
                        return {background:css.backgroundColor,color:css.color,
                            contrast:(values[0]+.05)/(values[1]+.05)}; });
                }""")
                check("all coloured message pills use light surfaces",
                      len(pills) == 8 and all(item["contrast"] >= 4.5 for item in pills)
                      and all(item["background"] not in ("rgb(15, 43, 41)", "rgb(51, 38, 15)")
                              for item in pills), repr(pills))
                page.screenshot(path=HERE / "review-light-show.png", full_page=True)

                page.select_option("#theme-select", "dark")
                dark = page.evaluate("""() => {
                    const root=getComputedStyle(document.documentElement);
                    const pill=getComputedStyle(document.querySelector('.show-pill-0'));
                    return {green:root.getPropertyValue('--green').trim(),
                        auto:root.getPropertyValue('--auto').trim(),
                        pill:{border:pill.borderColor,background:pill.backgroundColor,color:pill.color}};
                }""")
                check("dark semantic marks and pill palette remain unchanged", dark == {
                    "green": "#45d483", "auto": "#7fb0e8",
                    "pill": {"border": "rgb(46, 138, 132)",
                             "background": "rgb(15, 43, 41)",
                             "color": "rgb(168, 235, 230)"},
                }, repr(dark))
                page.select_option("#theme-select", "light")

                page.click("#tab-button-seats")
                page.click("#group-sidebar-tab")
                page.click('[data-group-eye="0"]')
                page.click('[data-group-eye="1"]')
                page.wait_for_selector("#spatial .membership-rail.back")
                rails = page.locator("#spatial .membership-rail.back").evaluate_all(
                    "elements => elements.map(element => ({stroke:getComputedStyle(element).stroke,width:getComputedStyle(element).strokeWidth}))")
                check("light Seat-group rails have a canvas halo instead of a dark stroke",
                      rails and all(item == {"stroke": "rgb(236, 232, 241)", "width": "5px"}
                                    for item in rails), repr(rails))
                page.screenshot(path=HERE / "review-light-seats.png", full_page=True)

                page.set_viewport_size({"width": 900, "height": 900})
                responsive = page.evaluate("""() => {
                    const brand=document.querySelector('.app-brand').getBoundingClientRect();
                    const mode=document.querySelector('#execution-target').getBoundingClientRect();
                    const buttons=[...document.querySelectorAll('[data-execution-target]')].map(x=>x.getBoundingClientRect());
                    return {brand,mode,buttons,viewport:innerWidth};
                }""")
                check("compact header gives mode its own full-width row",
                      responsive["mode"]["top"] >= responsive["brand"]["bottom"]
                      and responsive["mode"]["width"] > responsive["viewport"] * .9
                      and all(item["width"] > 100 for item in responsive["buttons"]),
                      repr(responsive))
                page.screenshot(path=HERE / "review-light-header-compact.png", full_page=True)
                page.set_viewport_size({"width": 420, "height": 820})
                phone = page.evaluate("""() => {
                    const header=document.querySelector('header');
                    const mode=document.querySelector('#execution-target').getBoundingClientRect();
                    const top=['.app-brand','.app-health','#mute-all','.theme-control']
                        .map(selector=>document.querySelector(selector).getBoundingClientRect());
                    const buttons=[...document.querySelectorAll('[data-execution-target]')]
                        .map(element=>element.getBoundingClientRect());
                    return {scrollWidth:header.scrollWidth,viewport:innerWidth,mode,top,buttons};
                }""")
                check("phone header stays two rows without horizontal overflow",
                      phone["scrollWidth"] <= phone["viewport"]
                      and max(item["bottom"] for item in phone["top"]) <= phone["mode"]["top"]
                      and all(item["width"] >= 100 for item in phone["buttons"]), repr(phone))
                check("browser emitted no errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(server)
            log.close()

        if FAILURES:
            print("\nserver log tail:\n" + log_path.read_text(encoding="utf-8")[-4000:])
            raise SystemExit(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        print("\nAll light-theme feedback checks passed.")


if __name__ == "__main__":
    main()
