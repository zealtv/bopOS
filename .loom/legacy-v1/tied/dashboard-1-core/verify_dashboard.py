import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright


OUT = Path(__file__).parent
URL = "http://127.0.0.1:8080"
results = []
console_errors = []
page_errors = []


def record(step, passed, observation):
    results.append({"step": step, "passed": bool(passed), "observation": observation})
    print(f"STEP {step}: {'PASS' if passed else 'FAIL'} - {observation}")


async def wait_for_fleet(page):
    await page.wait_for_function(
        "document.querySelectorAll('#assigned .device-row').length >= 4 && "
        "document.querySelectorAll('#unassigned .device-row').length >= 1 && "
        "document.querySelector('#ws-status')?.textContent.trim() === 'connected'",
        timeout=12_000,
    )
    await page.wait_for_timeout(4000)


async def select_sim1(page):
    row = page.locator(".device-row", has_text="sim1")
    await row.click()
    await page.locator("#detail h2", has_text="sim1").wait_for()
    await page.locator('[data-param="gain"]').wait_for(timeout=5000)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            await page.goto(URL, wait_until="domcontentloaded")
            await wait_for_fleet(page)
            count = (await page.locator("#online-count").inner_text()).strip()
            ws = (await page.locator("#ws-status").inner_text()).strip()
            assigned = await page.locator("#assigned .device-row").count()
            unassigned = await page.locator("#unassigned .device-row").count()
            unassigned_text = await page.locator("#unassigned").inner_text()
            # the unassigned device is labeled by uid: /hb carries no name
            ok = bool(re.fullmatch(r"[45] / 5 online", count)) and ws == "connected" and assigned == 4 and unassigned == 1 and "02:53:49:4d:00:05" in unassigned_text
            await page.screenshot(path=OUT / "01-overview.png")
            record(1, ok, f"header={count!r}, WS={ws!r}, assigned rows={assigned}, unassigned rows={unassigned} ({unassigned_text.strip()})")

            await select_sim1(page)
            detail = await page.locator("#detail").inner_text()
            params = set(await page.locator("[data-param]").evaluate_all("els => els.map(e => e.dataset.param)"))
            actions = {t.lower() for t in await page.locator(".actions button").all_inner_texts()}
            required_actions = {"reboot", "shutdown", "update", "get samples", "aloha", "identify"}
            echo_type = await page.locator('[data-param="echo"]').get_attribute("type")
            ok = all(x in detail for x in ["02:53:49:4d:00:01", "ID", "1", "Params", "Report"]) and {"gain", "backing", "echo"} <= params and required_actions <= actions and echo_type == "checkbox" and "UNDECLARED" not in detail
            await page.screenshot(path=OUT / "02-detail.png", full_page=True)
            record(2, ok, f"UID/ID present; params={sorted(params)}; echo type={echo_type}; actions={sorted(actions)}; UNDECLARED={'present' if 'UNDECLARED' in detail else 'absent'}")

            await page.locator("#refresh-report").click()
            await page.wait_for_timeout(2000)
            report_section = page.locator("#detail section").filter(has=page.locator("#refresh-report"))
            report_text = await report_section.inner_text()
            ok = all(x in report_text for x in ["engine", "pd", "contract_version", "1.0", "update_model", "persistent", "uptime"]) and bool(re.search(r"\d+h \d+m \d+s", report_text))
            await page.screenshot(path=OUT / "03-report.png", full_page=True)
            record(3, ok, "report contains engine=pd, contract_version=1.0, update_model=persistent, and formatted uptime")

            gain = page.locator('[data-param="gain"]')
            box = await gain.bounding_box()
            if not box:
                raise RuntimeError("gain slider has no bounding box")
            await page.mouse.move(box["x"] + box["width"] * 0.75, box["y"] + box["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(box["x"] + box["width"] * 0.25, box["y"] + box["height"] / 2, steps=12)
            await page.mouse.up()
            dragged = float(await gain.input_value())
            await page.wait_for_timeout(1000)
            await page.reload(wait_until="domcontentloaded")
            await wait_for_fleet(page)
            await select_sim1(page)
            persisted = float(await page.locator('[data-param="gain"]').input_value())
            ok = abs(dragged - 0.25) <= 0.06 and abs(persisted - dragged) <= 0.03
            await page.screenshot(path=OUT / "04-param-persist.png", full_page=True)
            record(4, ok, f"gain after drag={dragged:.2f}; after reload={persisted:.2f}")

            mute = page.locator("#mute-all")
            if "MUTED" in (await mute.inner_text()).upper():
                await mute.click()
                await page.wait_for_function("document.querySelector('#mute-all').textContent.trim() === 'MUTE ALL'")
            await mute.click()
            await page.wait_for_function("document.querySelector('#mute-all').textContent.includes('MUTED')")
            muted_text = (await mute.inner_text()).strip()
            muted_class = await mute.get_attribute("class") or ""
            ok = muted_text == "MUTED — UNMUTE" and "active" in muted_class.split()
            await page.screenshot(path=OUT / "05-muted.png")
            record(5, ok, f"button={muted_text!r}, class={muted_class!r}")
            await mute.click()
            await page.wait_for_function("document.querySelector('#mute-all').textContent.trim() === 'MUTE ALL'")

            # simfleet flags count from the end: sim5 is the engine-dead one
            sim1_dot = page.locator('.device-row[data-uid="02:53:49:4d:00:01"] .dot')
            sim5_dot = page.locator('.device-row[data-uid="02:53:49:4d:00:05"] .dot')
            class1 = await sim1_dot.get_attribute("class")
            class5 = await sim5_dot.get_attribute("class")
            color1 = await sim1_dot.evaluate("e => getComputedStyle(e).backgroundColor")
            color5 = await sim5_dot.evaluate("e => getComputedStyle(e).backgroundColor")
            ok = class1 == "dot online" and class5 == "dot crashed" and color1 != color5
            await page.locator("aside").screenshot(path=OUT / "06-engine-dead.png")
            record(6, ok, f"sim1: {class1}, {color1}; sim5: {class5}, {color5}")

        finally:
            try:
                mute = page.locator("#mute-all")
                if await mute.count() and "MUTED" in (await mute.inner_text()).upper():
                    await mute.click()
                    await page.wait_for_timeout(500)
            except Exception as exc:
                console_errors.append(f"cleanup error: {exc}")
            record(7, not console_errors and not page_errors, f"console errors={console_errors}; page errors={page_errors}")
            (OUT / "results.json").write_text(json.dumps({"results": results, "console_errors": console_errors, "page_errors": page_errors}, indent=2) + "\n")
            await browser.close()

    if not all(r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
