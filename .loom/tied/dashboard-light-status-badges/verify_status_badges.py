#!/usr/bin/env python3
"""Focused browser verification for paired operational status surfaces."""

import importlib.util
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


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-status-badges-") as temp:
        state_path = HELPER.make_fixture(temp)
        http_port = HELPER.free_port(__import__("socket").SOCK_STREAM)
        listen_port = HELPER.free_port(__import__("socket").SOCK_DGRAM)
        send_port = HELPER.free_port(__import__("socket").SOCK_DGRAM)
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
                page.select_option("#theme-select", "light")
                page.evaluate("""() => {
                    document.querySelector('.tab-stage').innerHTML = `<section id="status-gallery" style="max-width:940px;margin:24px auto;padding:22px">
                      <h2>Status surfaces</h2>
                      <div style="display:grid;gap:18px;margin-top:18px">
                        <div data-family="patch" style="display:flex;gap:10px;align-items:center"><strong style="width:120px">Patch</strong><span class="patch-badge patch-badge-current">current</span><span class="patch-badge patch-badge-switching">switching</span><span class="patch-badge patch-badge-stale">stale</span><span class="patch-badge patch-badge-unknown">unknown</span></div>
                        <div data-family="asset" style="display:flex;gap:10px;align-items:center"><strong style="width:120px">Asset</strong><span class="asset-state asset-state-current">current</span><span class="asset-state asset-state-stale">stale</span><span class="asset-state asset-state-unknown">unknown</span><span class="asset-state asset-state-failed">failed</span></div>
                        <div data-family="show" style="display:flex;gap:10px;align-items:center"><strong style="width:120px">Show</strong><button class="show-state-playing">playing</button><button class="show-state-paused">paused</button><span class="device-mute-indicator device" style="width:auto;border-radius:999px;padding:5px 9px">device muted</span></div>
                        <p class="asset-inventory-note current">Observed inventory is current.</p>
                        <p class="asset-inventory-note unknown">Inventory is stale or has not replied.</p>
                        <p class="show-field-error">A validation error uses the same danger surface.</p>
                      </div>
                    </section>`;
                }""")

                light = page.evaluate(r"""() => {
                    const selectors = {
                      ok:['.patch-badge-current','.asset-state-current','.show-state-playing','.asset-inventory-note.current'],
                      warn:['.patch-badge-switching','.asset-state-stale','.show-state-paused','.asset-inventory-note.unknown'],
                      danger:['.patch-badge-stale','.asset-state-failed','.device-mute-indicator.device','.show-field-error'],
                      neutral:['.patch-badge-unknown','.asset-state-unknown']
                    };
                    const lum = value => value.match(/\d+/g).slice(0,3).map(Number).map(v=>v/255)
                      .map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4)
                      .reduce((sum,v,index)=>sum+v*[.2126,.7152,.0722][index],0);
                    const ratio = (a,b) => { const values=[lum(a),lum(b)].sort((x,y)=>y-x);
                      return (values[0]+.05)/(values[1]+.05); };
                    return Object.fromEntries(Object.entries(selectors).map(([tone,list]) => [tone,
                      list.map(selector => { const css=getComputedStyle(document.querySelector(selector));
                        return {selector,color:css.color,background:css.backgroundColor,
                          border:css.borderColor,contrast:ratio(css.color,css.backgroundColor)}; })]));
                }""")
                expected_backgrounds = {
                    "ok": "rgb(220, 239, 228)", "warn": "rgb(248, 234, 208)",
                    "danger": "rgb(247, 223, 220)", "neutral": "rgb(240, 237, 244)",
                }
                for tone, specimens in light.items():
                    check(f"light {tone} status family uses one pale surface",
                          all(item["background"] == expected_backgrounds[tone]
                              and item["contrast"] >= 4.5 for item in specimens),
                          repr(specimens))
                page.screenshot(path=HERE / "review-light-status-surfaces.png",
                                full_page=True)

                page.select_option("#theme-select", "dark")
                dark = page.evaluate("""() => {
                    const root=getComputedStyle(document.documentElement);
                    const names=['--status-ok-bg','--status-warn-bg','--status-danger-bg','--status-neutral-bg'];
                    return Object.fromEntries(names.map(name=>[name,root.getPropertyValue(name).trim()]));
                }""")
                check("dark status surfaces retain their established palette", dark == {
                    "--status-ok-bg": "#173323", "--status-warn-bg": "#382a13",
                    "--status-danger-bg": "#3c171b", "--status-neutral-bg": "transparent",
                }, repr(dark))
                check("browser emitted no errors", not errors, repr(errors))
                browser.close()
        finally:
            HELPER.stop(server)
            log.close()

        if FAILURES:
            print("\nserver log tail:\n" + log_path.read_text(encoding="utf-8")[-4000:])
            raise SystemExit(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        print("\nAll operational status surface checks passed.")


if __name__ == "__main__":
    main()
