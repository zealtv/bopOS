#!/usr/bin/env python3
"""Browser-free checks for Control target persistence and derived order."""

import json
import os
import subprocess
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
MODEL = os.path.join(REPO, "dashboard", "static", "js",
                     "control-cards-model.js")


def run_node(body):
    script = """
global.window=global;
const fs=require('fs');
eval(fs.readFileSync(process.argv[1], 'utf8'));
const storeValues=new Map();
const storage={getItem:key=>storeValues.has(key)?storeValues.get(key):null,
 setItem:(key,value)=>storeValues.set(key,value)};
""" + body
    result = subprocess.run(["node", "-e", script, MODEL], check=True,
                            capture_output=True, text=True)
    return json.loads(result.stdout)


class ControlCardsModelTests(unittest.TestCase):
    def test_migrates_unique_targets_without_ids_order_or_open_state(self):
        result = run_node("""
storage.setItem('columns',JSON.stringify([
 {id:'c9',target:['5','g2'],open:true},
 {id:'c1',target:['all'],open:false},
 {id:'duplicate',target:['5'],open:false}
]));
process.stdout.write(JSON.stringify(ControlCardsModel.readTargets(
 storage,'cards','columns','target')));
""")
        self.assertEqual(result, ["5", "g2", "all"])

    def test_versioned_empty_set_does_not_fall_back_to_all(self):
        result = run_node("""
storage.setItem('cards',JSON.stringify({version:1,targets:[]}));
process.stdout.write(JSON.stringify(ControlCardsModel.readTargets(
 storage,'cards','columns','target')));
""")
        self.assertEqual(result, [])

    def test_order_is_all_then_numeric_groups_then_numeric_seats(self):
        result = run_node("""
const values=['10','g9','2','all','g2'];
values.sort(ControlCardsModel.compareSelectors);
process.stdout.write(JSON.stringify(values));
""")
        self.assertEqual(result, ["all", "g2", "g9", "2", "10"])

    def test_malformed_state_uses_safe_first_run_default(self):
        result = run_node("""
storage.setItem('cards','{'); storage.setItem('columns','{}');
process.stdout.write(JSON.stringify(ControlCardsModel.readTargets(
 storage,'cards','columns','target')));
""")
        self.assertEqual(result, ["all"])


if __name__ == "__main__":
    unittest.main()
