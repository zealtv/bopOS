#!/usr/bin/env python3
"""Browser-free contract for the shared downward cards layout."""

import os
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def read(relative):
    with open(os.path.join(REPO, relative), encoding="utf-8") as source:
        return source.read()


class CardsGridCssTests(unittest.TestCase):
    def test_both_hosts_left_pack_flexible_340_to_560_cards(self):
        for stylesheet in ("dashboard/static/css/style.css",
                           "dashboard/static/css/facilitator.css"):
            css = "".join(read(stylesheet).split())
            self.assertIn("display:flex", css)
            self.assertIn("flex-wrap:wrap", css)
            self.assertIn("justify-content:flex-start", css)

    def test_target_card_component_owns_the_shared_bounds(self):
        css = "".join(read(
            "dashboard/static/css/card-identity.css").split())
        self.assertIn(".target-card.target-card{min-width:0;"
                      "flex:11min(340px,100%);"
                      "max-width:min(560px,100%)", css)

    def test_remote_cards_region_is_an_explicit_flex_context(self):
        css = "".join(read("dashboard/static/css/facilitator.css").split())
        self.assertIn(
            "#control-column-host.control-column.control-column-derived"
            "{display:block;width:auto;max-width:none;"
            "border:0;border-radius:0;padding:0;background:transparent;"
            "box-shadow:none}",
            css,
        )
        self.assertIn(
            "#control-column-host.control-column-derived>"
            ".control-column-cards{display:flex;flex-wrap:wrap;"
            "justify-content:flex-start",
            css,
        )
        self.assertNotIn(
            "#control-column-host>.control-column.control-column-derived",
            css,
        )

    def test_component_cards_region_is_not_a_nested_scrollport(self):
        css = read("dashboard/static/css/control-column.css")
        block = css.split("\n.control-column-cards {", 1)[1].split("}", 1)[0]
        self.assertIn("overflow: visible", block)
        self.assertNotIn("overflow-y: auto", block)
        self.assertNotIn("max-height", css.split(".control-column {", 1)[1]
                         .split("}", 1)[0])

    def test_remote_derivation_has_no_picker_or_preset_capability(self):
        source = read("dashboard/static/js/facilitator.js")
        self.assertIn("targetPicker: false", source)
        self.assertIn("deriveAllTargets: true", source)
        self.assertIn("presetMenu: false", source)

    def test_control_keeps_authored_picker_and_presets(self):
        source = read("dashboard/static/js/control-host.js")
        self.assertIn("targetPicker: true", source)
        self.assertIn("deriveAllTargets: false", source)
        self.assertIn("presetMenu: true", source)


if __name__ == "__main__":
    unittest.main()
