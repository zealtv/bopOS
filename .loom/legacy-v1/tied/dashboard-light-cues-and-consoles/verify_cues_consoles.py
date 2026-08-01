#!/usr/bin/env python3
"""Browser checks for light cue animation surfaces and OSC console text."""

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


def contrast_script(selector):
    return r"""selector => {
      const css=getComputedStyle(document.querySelector(selector));
      const lum=value=>value.match(/\d+/g).slice(0,3).map(Number).map(v=>v/255)
        .map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4)
        .reduce((sum,v,index)=>sum+v*[.2126,.7152,.0722][index],0);
      const values=[lum(css.color),lum(css.backgroundColor)].sort((a,b)=>b-a);
      return {color:css.color,background:css.backgroundColor,
        backgroundImage:css.backgroundImage,border:css.borderColor,
        ratio:(values[0]+.05)/(values[1]+.05)};
    }"""


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-cues-consoles-") as temp:
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

                dashboard = browser.new_page(viewport={"width": 1180, "height": 820})
                errors = []
                dashboard.on("pageerror", lambda error: errors.append(str(error)))
                dashboard.on("console", lambda message: errors.append(message.text)
                             if message.type == "error" else None)
                dashboard.goto(base_url)
                dashboard.wait_for_selector("#initial-loading", state="hidden")
                dashboard.select_option("#theme-select", "light")
                dashboard.click("#tab-button-show")
                dashboard.locator(".show-console").first.evaluate(
                    "element => element.open = true")
                dashboard.locator(".show-console-log").first.evaluate(
                    "(element, text) => element.textContent = text",
                    "12:34:56.789  /p/gain  0.75\n12:34:57.012  /cue/go")
                console_style = dashboard.evaluate(
                    contrast_script(".show-console-log"), ".show-console-log")
                check("light Show console has explicit readable terminal text",
                      console_style["color"] == "rgb(241, 237, 245)"
                      and console_style["background"] == "rgb(39, 35, 44)"
                      and console_style["ratio"] >= 7, repr(console_style))
                dashboard.screenshot(path=HERE / "review-light-console.png", full_page=True)

                normal = browser.new_page(viewport={"width": 1024, "height": 700})
                normal.goto(base_url + "/facilitator")
                normal.wait_for_selector("#initial-loading", state="hidden")
                normal.select_option("#theme-select", "light")
                normal.evaluate("""() => {
                  const panel=document.querySelector('#cue-panel'); panel.hidden=false;
                  document.querySelector('#declared-cues').innerHTML =
                    '<button class="scheduling" style="--cue-lead-duration:10s;animation-play-state:paused;animation-delay:-5s">progressing cue</button>';
                }""")
                progress = normal.locator("#declared-cues button").evaluate(
                    "element => {const css=getComputedStyle(element);return {image:css.backgroundImage,size:css.backgroundSize,border:css.borderColor}}")
                check("normal-motion cue progress uses the pale light fill",
                      "rgb(220, 239, 228)" in progress["image"]
                      and progress["size"].startswith("50%"), repr(progress))

                reduced_context = browser.new_context(
                    viewport={"width": 1024, "height": 700}, reduced_motion="reduce")
                reduced = reduced_context.new_page()
                reduced.goto(base_url + "/facilitator")
                reduced.wait_for_selector("#initial-loading", state="hidden")
                reduced.select_option("#theme-select", "light")
                reduced.evaluate("""() => {
                  const panel=document.querySelector('#cue-panel'); panel.hidden=false;
                  document.querySelector('#declared-cues').innerHTML =
                    '<button class="scheduling">progress complete</button><button class="scheduling triggered">cue flash</button>';
                }""")
                progress_reduced = reduced.evaluate(
                    contrast_script("#declared-cues .scheduling:not(.triggered)"),
                    "#declared-cues .scheduling:not(.triggered)")
                flash = reduced.evaluate(
                    contrast_script("#declared-cues .triggered"),
                    "#declared-cues .triggered")
                check("reduced-motion progress retains the pale completion state",
                      progress_reduced["background"] == "rgb(220, 239, 228)",
                      repr(progress_reduced))
                check("light cue flash is pale with readable text",
                      flash["background"] == "rgb(191, 232, 208)"
                      and flash["ratio"] >= 4.5, repr(flash))
                reduced.screenshot(path=HERE / "review-light-cues.png", full_page=True)

                reduced.select_option("#theme-select", "dark")
                dark = reduced.evaluate("""() => {
                  const css=getComputedStyle(document.documentElement);
                  return ['--cue-progress-bg','--cue-progress-border','--cue-flash-bg','--cue-flash-text']
                    .map(name=>css.getPropertyValue(name).trim());
                }""")
                check("dark cue palette remains unchanged",
                      dark == ["#2c3b34", "#6fa88a", "#c8ffe0", "#07120c"],
                      repr(dark))
                check("browser emitted no errors", not errors, repr(errors))
                browser.close()
        finally:
            HELPER.stop(server)
            log.close()

        if FAILURES:
            print("\nserver log tail:\n" + log_path.read_text(encoding="utf-8")[-4000:])
            raise SystemExit(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        print("\nAll cue and console theme checks passed.")


if __name__ == "__main__":
    main()
