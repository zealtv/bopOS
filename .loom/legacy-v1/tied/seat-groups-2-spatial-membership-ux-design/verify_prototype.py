#!/usr/bin/env python3
"""Focused interaction check for the standalone Seat-group UX study."""

from pathlib import Path
from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1180, "height": 820})
        page.goto((HERE / "prototype.html").as_uri())

        # Seats remain the sidebar's primary object; Groups follows Seat detail.
        assert page.locator("aside.side h2").inner_text() == "Seats"
        hierarchy = page.locator("aside.side > *").evaluate_all(
            "els => els.map(el => el.className || el.id || el.tagName)"
        )
        assert hierarchy.index("seat-study") < hierarchy.index("groups-panel")
        assert page.locator("#groups-panel").get_attribute("open") == ""

        assert page.locator("#mode-note").inner_text() == "Focused: Front row"
        assert page.locator(".rail:not(.back)").count() == 4
        shown = page.locator("[data-eye='1']")
        hidden = page.locator("[data-eye='2']")
        assert shown.get_attribute("aria-pressed") == "true"
        assert shown.get_attribute("aria-label") == "Hide Front row from map"
        assert shown.locator(".visibility-icon path").count() == 1
        assert hidden.get_attribute("aria-pressed") == "false"
        assert hidden.get_attribute("aria-label") == "Show Guitars on map"
        assert hidden.locator(".visibility-icon path").count() == 2

        for group_id in (2, 7, 9):
            page.locator(f"[data-eye='{group_id}']").click()
        assert page.locator("#legend .chip").count() == 4
        assert page.locator("#groups-summary").inner_text() == "4 shown · 5 total"
        assert page.locator("[data-seat='3'] .rail:not(.back)").count() == 4
        assert page.locator("[data-seat='3'] .s1").count() == 2
        assert page.locator("[data-seat='3'] .s2").count() == 2
        assert page.locator("[data-seat='3'] .s3").count() == 2
        assert page.locator("[data-seat='3'] .s4").count() == 2

        page.locator("[data-eye='12']").click()
        assert page.locator("#limit").is_visible()
        assert page.locator("#legend .chip").count() == 4

        page.locator("[data-seat='3']").click()
        assert "Front row" in page.locator("#members").inner_text()
        assert "hidden" in page.locator("#members").inner_text()
        page.screenshot(path=str(HERE / "visual-study.png"), full_page=True)
        page.locator("#groups-panel").evaluate("el => el.open = false")
        assert page.locator("#groups-summary").inner_text() == "4 shown · 5 total"
        page.screenshot(path=str(HERE / "visual-study-collapsed.png"), full_page=True)
        page.locator("#groups-panel").evaluate("el => el.open = true")

        page.locator("#clear").click()
        assert page.locator("#legend .chip").count() == 0
        assert page.locator("#mode-note").inner_text() == "No groups shown"

        page.locator("[data-focus='12']").click()
        assert page.locator("#empty-note").is_visible()
        assert page.locator("#mode-note").inner_text() == "Focused: Empty study"
        page.screenshot(path=str(HERE / "visual-study-empty.png"), full_page=True)
        browser.close()

    print("PASS: 1 focus state")
    print("PASS: 4-group non-blended overlap")
    print("PASS: fifth-group limit feedback")
    print("PASS: complete selected-Seat membership")
    print("PASS: clear and empty-group states")
    print("PASS: Seats-first hierarchy and eye/eye-off semantics")
    print("PASS: collapsed Groups summary preserves overlay state")


if __name__ == "__main__":
    main()
