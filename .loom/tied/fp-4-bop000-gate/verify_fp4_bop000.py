#!/usr/bin/env python3
"""Drive the real-dashboard phases of the fp-4 bop000 hardware gate."""

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def snapshot(page):
    return page.evaluate("""() => {
      const device=Object.values(installation.devices || {}).find(
        item => !item.virtual && item.uid === '2c:cf:67:b3:0a:58');
      const active=(device?.patches || []).find(item => item.active);
      return {
        desired: installation.fleet_patch || null,
        uid: device?.uid || null,
        online: device?.online || false,
        badge: device?.patch_badge || null,
        report_patch: device?.report?.patch || null,
        active: active || null,
        git_managed: (device?.patches || []).filter(item => item.git),
        installed: (device?.patches || []).map(item => ({
          name:item.name, active:item.active, manifest:item.manifest,
          git:item.git, fingerprint:item.fingerprint || null
        }))
      };
    }""")


def wait_device(page):
    page.wait_for_function("""() => {
      const d=installation.devices?.['2c:cf:67:b3:0a:58'];
      return d?.online && Array.isArray(d.patches);
    }""", timeout=20000)


def wait_badge(page, badge, timeout=45000):
    page.wait_for_function(
        "([uid,badge]) => installation.devices?.[uid]?.patch_badge === badge",
        arg=["2c:cf:67:b3:0a:58", badge], timeout=timeout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=(
        "inspect", "set", "stale", "retry", "revert", "git"))
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--patch", default="demo-pd")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1050})
        dialogs = []
        page.on("dialog", lambda dialog: (dialogs.append(
            {"type": dialog.type, "message": dialog.message}), dialog.accept()))
        page.goto(args.url)
        wait_device(page)

        if args.phase == "set":
            page.select_option("#patch-select", args.patch)
            page.click("#patch-switch")
            wait_badge(page, "current")
        elif args.phase == "stale":
            page.evaluate("ws.send('request_patches',{uid:'2c:cf:67:b3:0a:58'})")
            wait_badge(page, "stale")
        elif args.phase == "retry":
            page.locator(".seat-row[data-uid='2c:cf:67:b3:0a:58'] .dot").click()
            page.wait_for_selector("#fleet-patch-retry")
            page.click("#fleet-patch-retry")
            wait_badge(page, "current")
        elif args.phase == "revert":
            previous = page.evaluate("installation.fleet_patch?.previous?.name")
            if not previous:
                raise RuntimeError("fleet patch has no previous value to revert")
            page.click("#fleet-patch-revert")
            page.wait_for_function(
                "name => installation.fleet_patch?.name === name",
                arg=previous, timeout=10000)
            wait_badge(page, "current")
        elif args.phase == "git":
            page.evaluate("ws.send('request_patches',{uid:'2c:cf:67:b3:0a:58'})")
            page.wait_for_function("""() =>
              installation.devices?.['2c:cf:67:b3:0a:58']?.patches
                ?.some(item => item.name === 'demo-sc' && item.git === true)
            """, timeout=10000)

        result = snapshot(page)
        result["phase"] = args.phase
        result["dialogs"] = dialogs
        print(json.dumps(result, indent=2, sort_keys=True))

        if not result["online"]:
            raise RuntimeError("bop000 is not online")
        if args.phase in ("set", "retry", "revert"):
            desired = result["desired"] or {}
            active = result["active"] or {}
            if result["badge"] != "current":
                raise RuntimeError("bop000 did not converge to current")
            if active.get("name") != desired.get("name"):
                raise RuntimeError("active and desired patch names differ")
            if active.get("fingerprint") != desired.get("fingerprint"):
                raise RuntimeError("active and desired patch fingerprints differ")
        if args.phase == "git" and not any(
                item.get("name") == "demo-sc" for item in result["git_managed"]):
            raise RuntimeError("temporary git-managed demo-sc was not reported honestly")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
