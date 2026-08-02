#!/usr/bin/env python3
"""Browser-free markup guard for the shared preset menu."""

import json
import os
import subprocess
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE = os.path.join(REPO, "dashboard", "static", "js", "control-surface.js")


def render(reason=None, drift=False, name="A preset name that is deliberately much longer than its closed menu"):
    script = r"""
global.window = global;
global.document = {};
global.OscMessage = {};
const fs = require('fs');
eval(fs.readFileSync(process.argv[1], 'utf8'));
const name = JSON.parse(process.argv[2]);
const reason = JSON.parse(process.argv[3]);
const drift = JSON.parse(process.argv[4]);
const surface = ControlSurface.create({
  presetCatalog: () => [{name, slug:'long-preset', valid:true, drift}],
});
const member = {applied_preset:{patch:'alpha', name}, preset_dirty:reason};
process.stdout.write(surface.presetRow('seat', 1, [member], 'alpha'));
"""
    result = subprocess.run(
        ["node", "-e", script, SOURCE, json.dumps(name), json.dumps(reason),
         json.dumps(drift)], check=True, capture_output=True, text=True)
    return result.stdout


class PresetMenuMarkup(unittest.TestCase):
    def test_dirty_and_drift_marks_lead_the_long_name(self):
        markup = render("deviated", True)
        self.assertIn(">* ⚠ A preset name that is deliberately", markup)

    def test_missing_and_foreign_patch_are_distinct(self):
        missing = render("missing")
        foreign = render("foreign-patch")
        self.assertIn("preset-menu-missing", missing)
        self.assertIn("can no longer be read", missing)
        self.assertIn("preset-menu-foreign-patch", foreign)
        self.assertIn("running a different patch", foreign)
        self.assertIn('data-preset-choice="long-preset" role="menuitemradio" aria-checked="true" disabled', foreign)

    def test_actions_precede_a_real_separator_and_recall_choices(self):
        markup = render()
        self.assertLess(markup.index("preset-menu-actions"),
                        markup.index('role="separator"'))
        self.assertLess(markup.index('role="separator"'),
                        markup.index('data-preset-choice=""'))
        self.assertIn('data-preset-action="new"', markup)
        self.assertIn('data-preset-action="save"', markup)
        self.assertIn('data-preset-action="del"', markup)


if __name__ == "__main__":
    unittest.main()
