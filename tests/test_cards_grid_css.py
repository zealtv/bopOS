#!/usr/bin/env python3
"""Browser-free contract for the shared downward cards grid."""

import os
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def read(relative):
    with open(os.path.join(REPO, relative), encoding="utf-8") as source:
        return source.read()


class CardsGridCssTests(unittest.TestCase):
    def test_both_hosts_use_the_same_flexible_track(self):
        track = "repeat(auto-fit,minmax(min(342px,100%),1fr))"
        self.assertIn(track, read("dashboard/static/css/style.css"))
        self.assertIn(track, read("dashboard/static/css/facilitator.css"))

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
