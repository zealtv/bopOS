#!/usr/bin/env python3
"""Target cards consume the Seats map's one shared identity palette."""

import os
import re
import subprocess
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def read(relative):
    with open(os.path.join(REPO, relative), encoding="utf-8") as source:
        return source.read()


class CardIdentityTests(unittest.TestCase):
    def test_palette_has_one_javascript_authority(self):
        slots = read("dashboard/static/js/group-slots.js")
        colours = re.findall(r'colour:\s*"(#[0-9A-Fa-f]{6})"', slots)
        self.assertEqual(colours, ["#56B4E9", "#E69F00", "#00B98B", "#CC79A7"])
        dashboard = read("dashboard/static/js/dashboard.js")
        self.assertIn("window.GroupSlots.palette", dashboard)
        for colour in colours:
            self.assertNotIn(colour, dashboard)

    def test_both_documents_load_slot_signal_and_card_face(self):
        for document in ("dashboard/static/index.html",
                         "dashboard/static/facilitator.html"):
            html = read(document)
            self.assertIn('/js/group-slots.js', html)
            self.assertIn('/css/card-identity.css', html)

    def test_card_patterns_and_all_keyline_are_explicit(self):
        css = read("dashboard/static/css/card-identity.css")
        self.assertRegex(css, r"\.target-card\.target-card-all\s*\{[^}]*border:3px solid #fff")
        self.assertIn("box-shadow:0 0 0 2px #071015", css)
        self.assertIn(".target-card-group.group-slot-2 { border-style:dashed; }", css)
        self.assertIn(".target-card-group.group-slot-3 { border-style:dotted; }", css)
        self.assertIn(".target-card-group.group-slot-4 { border-style:double; }", css)

    def test_group_slots_follow_sorted_roster_not_map_visibility(self):
        source = read("dashboard/static/js/group-slots.js")
        probe = """
global.document = {documentElement: {style: {setProperty() {}}}};
global.window = {};
%s
const groups = [{id: 9}, {id: 2}, {id: 12}, {id: 5}, {id: 7}];
console.log(JSON.stringify([2, 5, 7, 9, 12, 99].map(
  id => window.GroupSlots.forGroup(id, groups))));
""" % source
        result = subprocess.run(
            ["node", "-e", probe], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "[0,1,2,3,0,-1]")

        for host in ("dashboard/static/js/control-host.js",
                     "dashboard/static/js/facilitator.js"):
            script = read(host)
            self.assertIn("window.GroupSlots.forGroup(", script)
            self.assertIn("Object.values(installation.groups || {})", script)
        self.assertNotIn("GroupSlots.write", read("dashboard/static/js/dashboard.js"))

    def test_unknown_groups_fall_back_to_neutral_face(self):
        renderer = read("dashboard/static/js/control-column.js")
        self.assertIn('groupSlot = capabilities.groupSlot || (() => -1)', renderer)
        self.assertIn('return " target-card";', renderer)
        self.assertIn('host.style.removeProperty("--group-colour")', renderer)


if __name__ == "__main__":
    unittest.main()
