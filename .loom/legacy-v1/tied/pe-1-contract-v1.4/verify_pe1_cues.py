#!/usr/bin/env python3
"""Verify the v1.4 additive cue-manifest amendment."""

import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "python", "manifest.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

import manifest  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def load_fixture(root, cues_marker=False, cues=None):
    with open(os.path.join(root, "main.bin"), "wb") as target:
        target.write(b"entrypoint")
    value = {"engine": "test", "entrypoint": "main.bin", "params": [],
             "caps": [], "slots": []}
    if cues_marker:
        value["cues"] = cues
    with open(os.path.join(root, manifest.MANIFEST_NAME), "w", encoding="utf-8") as target:
        json.dump(value, target)
    return manifest.load(root)


def main():
    with tempfile.TemporaryDirectory() as root:
        loaded, error = load_fixture(root)
        check("absent cues key remains valid", loaded is not None and error is None,
              str(error))

        declared = [
            {"id": "snap"},
            {"id": "scene/a", "label": "Scene A", "description": "Start it"},
        ]
        loaded, error = load_fixture(root, True, declared)
        check("valid cue declarations load unchanged",
              error is None and loaded.get("cues") == declared, str(error))

        invalid = [
            ("non-list cues rejected", {"id": "snap"}, "cues must be a list"),
            ("non-object cue rejected", ["snap"], "must be an object"),
            ("missing cue id rejected", [{"label": "Snap"}], "must be a string"),
            ("non-string label rejected", [{"id": "snap", "label": 1}],
             "label must be a string"),
            ("non-string description rejected",
             [{"id": "snap", "description": False}],
             "description must be a string"),
            ("duplicate cue ids rejected", [{"id": "snap"}, {"id": "snap"}],
             "duplicate cue id"),
        ]
        for label, cues, expected in invalid:
            loaded, error = load_fixture(root, True, cues)
            check(label, loaded is None and expected in (error or ""), str(error))

    demo = os.path.join(REPO, "patches", "demo-pd")
    loaded, error = manifest.load(demo)
    with open(os.path.join(demo, "main.pd"), encoding="utf-8") as source:
        pd_text = source.read()
    check("demo-pd honestly declares its snap cue",
          error is None
          and any(cue.get("id") == "snap" for cue in loaded.get("cues", ()))
          and "route snap" in pd_text,
          str(error))

    tracked = {}
    for name in ("bonks-pd", "demo-pd", "demo-sc"):
        _, tracked[name] = manifest.load(os.path.join(REPO, "patches", name))
    check("all tracked patch manifests remain valid",
          all(error is None for error in tracked.values()), repr(tracked))

    print("\n{}/{} passed".format(10 - len(FAILURES), 10))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
