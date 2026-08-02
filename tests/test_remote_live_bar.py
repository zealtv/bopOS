#!/usr/bin/env python3
"""Browser-free contract for Remote's always-visible master/mute bar."""

import os
import re
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def read(relative):
    with open(os.path.join(REPO, relative), encoding="utf-8") as source:
        return source.read()


class RemoteLiveBarTests(unittest.TestCase):
    def test_master_and_mute_share_the_live_bar(self):
        html = read("dashboard/static/facilitator.html")
        footer = re.search(r'<footer id="controls"[^>]*>(.*?)</footer>',
                           html, re.DOTALL)
        self.assertIsNotNone(footer)
        self.assertIn('id="master-row"', footer.group(1))
        self.assertIn('id="silence" class="danger">MUTE</button>',
                      footer.group(1))
        self.assertNotIn("SILENCE ALL", html)
        self.assertLess(html.index('id="facilitator-commands"'),
                        html.index('<footer id="controls"'))

    def test_bar_is_fixed_and_stacks_only_at_narrow_width(self):
        css = read("dashboard/static/css/facilitator.css")
        footer = re.search(r"footer\{([^}]*)\}", css).group(1)
        self.assertIn("position:fixed", footer)
        self.assertIn("bottom:0", footer)
        self.assertIn("grid-template-columns:minmax(0,1fr) auto", footer)
        self.assertIn(
            "@media(max-width:620px){body{padding-bottom:calc(142px + "
            "env(safe-area-inset-bottom))}#control-column-host{margin-inline:8px}"
            "footer{grid-template-columns:1fr",
            css,
        )

    def test_action_and_inverse_use_mute_language(self):
        source = read("dashboard/static/js/facilitator.js")
        self.assertIn('muted ? "UNMUTE" : "MUTE"', source)
        self.assertNotIn('"SILENCE ALL"', source)
        self.assertNotIn('"RESUME"', source)


if __name__ == "__main__":
    unittest.main()
