"""Durable tests for the patch manifest schema and canonical identities."""

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import manifest  # noqa: E402


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-manifest-")
        self.patch = Path(self.temp.name)
        (self.patch / "main.pd").touch()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def declaration(name="gain", kind="float", path=None, **extra):
        result = {"name": name, "kind": kind, **extra}
        if path is not None:
            result["path"] = path
        return result

    def candidate(self, params=(), **extra):
        return {
            "engine": "pd",
            "entrypoint": "main.pd",
            "params": list(params),
            **extra,
        }

    def validate(self, params=(), **extra):
        return manifest.validate(self.candidate(params, **extra), self.patch)

    def assert_invalid(self, params=(), **extra):
        loaded, error = self.validate(params, **extra)
        self.assertIsNone(loaded)
        self.assertTrue(error)

    def test_flat_and_nested_identities_are_canonical(self):
        self.assertEqual(
            manifest.qualify_param(self.declaration()),
            "gain",
        )
        self.assertEqual(
            manifest.qualify_param(
                self.declaration(path=["instrument", "marimba"])
            ),
            "instrument/marimba/gain",
        )

    def test_identity_segments_and_bounds_are_enforced(self):
        for path in (
            "not-a-list",
            [""],
            ["."],
            [".."],
            ["fx/reverb"],
            ["fx reverb"],
            ["fx*"],
            ["fx%2Freverb"],
        ):
            with self.subTest(path=path):
                self.assert_invalid([self.declaration(path=path)])

        self.assert_invalid([
            self.declaration(path=[str(index) for index in range(8)])
        ])
        self.assert_invalid([
            self.declaration(path=["a" * 40] * 6, name="b" * 40)
        ])

    def test_qualified_identity_must_be_unique_but_leaf_need_not_be(self):
        first = self.declaration(path=["instrument"])
        second = self.declaration(path=["fx"])
        loaded, error = self.validate([first, second])
        self.assertIsNone(error)
        self.assertEqual(len(loaded["params"]), 2)

        self.assert_invalid([first, dict(first)])

    def test_entrypoint_must_exist_and_stay_inside_patch(self):
        outside = self.patch.parent / f"{self.patch.name}-outside.pd"
        outside.touch()
        try:
            for entrypoint in ("missing.pd", "../outside.pd"):
                with self.subTest(entrypoint=entrypoint):
                    loaded, error = manifest.validate(
                        self.candidate(entrypoint=entrypoint), self.patch
                    )
                    self.assertIsNone(loaded)
                    self.assertTrue(error)
        finally:
            outside.unlink()

        nested = self.patch / "engine"
        nested.mkdir()
        (nested / "entry.bin").touch()
        loaded, error = manifest.validate(
            self.candidate(engine="custom", entrypoint="engine/entry.bin"),
            self.patch,
        )
        self.assertIsNone(error)
        self.assertEqual(loaded["engine"], "custom")

    def test_numeric_declarations_are_finite_and_bounded(self):
        for declaration in (
            self.declaration(min=True),
            self.declaration(default=math.nan),
            self.declaration(min=2, max=1),
            self.declaration(min=0, max=1, default=-1),
            self.declaration(min=0, max=1, default=2),
        ):
            with self.subTest(declaration=declaration):
                self.assert_invalid([declaration])

        loaded, error = self.validate([
            self.declaration(min=0, max=1, default=0.5)
        ])
        self.assertIsNone(error)
        self.assertEqual(loaded["params"][0]["default"], 0.5)

    def test_param_kinds_and_legacy_normalization(self):
        declarations = {
            "float": self.declaration(kind="float"),
            "int": self.declaration(kind="int"),
            "toggle": self.declaration(kind="toggle"),
            "enum": self.declaration(kind="enum", options=["dry", "wet"]),
            "text": self.declaration(kind="text"),
        }
        for kind, declaration in declarations.items():
            with self.subTest(kind=kind):
                loaded, error = self.validate([
                    declaration
                ])
                self.assertIsNone(error)
                self.assertEqual(loaded["params"][0]["kind"], kind)
                self.assertEqual(
                    manifest.param_wire_type(loaded["params"][0]),
                    manifest.PARAM_KINDS[kind],
                )

        loaded, error = self.validate([
            self.declaration(facilitator=True, group="legacy-layout")
        ])
        self.assertIsNone(error)
        self.assertTrue(loaded["params"][0]["dashboard"])
        self.assertNotIn("facilitator", loaded["params"][0])
        self.assertNotIn("group", loaded["params"][0])

        self.assert_invalid([
            self.declaration(dashboard=True, facilitator=False)
        ])
        self.assert_invalid([self.declaration(role="volume")])
        self.assert_invalid([self.declaration(dashboard="yes")])
        self.assert_invalid([self.declaration(kind="x")])

    def test_removed_type_and_kind_specific_fields_fail_loudly(self):
        loaded, error = self.validate([{"name": "gain", "type": "f"}])
        self.assertIsNone(loaded)
        self.assertIn("type was removed", error)

        for bound in ({"min": 0}, {"max": 1}, {"min": 0, "max": 1}):
            loaded, error = self.validate([
                self.declaration("gate", "toggle", default=0, **bound)
            ])
            self.assertIsNone(loaded)
            self.assertIn("derived for kind toggle", error)

        loaded, error = self.validate([
            self.declaration("label", "text", default=7)
        ])
        self.assertIsNone(loaded)
        self.assertEqual(error, "param label: text default must be a string")

        loaded, error = self.validate([
            self.declaration("gate", "toggle", default=.5)
        ])
        self.assertIsNone(loaded)
        self.assertEqual(error, "param gate: toggle default must be 0 or 1")

    def test_cues_caps_and_slots_use_the_declared_schema(self):
        loaded, error = self.validate(
            cues=[{"id": "snap", "label": "Snap", "description": "Fire"}],
            caps=["screen"],
            slots=["samples"],
        )
        self.assertIsNone(error)
        self.assertEqual(loaded["cues"][0]["id"], "snap")

        self.assert_invalid(cues=[{"id": "same"}, {"id": "same"}])
        self.assert_invalid(cues=[{"id": "bad\nid"}])
        self.assert_invalid(cues=[{"id": "cue", "label": 7}])
        self.assert_invalid(caps="screen")
        self.assert_invalid(slots=[1])

    def test_enum_options_derive_the_index_range(self):
        loaded, error = self.validate([
            self.declaration("mode", "enum", options=["dry", "hall", "plate"],
                             default=1),
        ])
        self.assertIsNone(error)
        # The wire stays an integer index, so the range is the option indices
        # and is derived rather than authored.
        self.assertEqual(loaded["params"][0]["min"], 0)
        self.assertEqual(loaded["params"][0]["max"], 2)

        # An authored range that agrees survives a save/load round trip.
        agreed, error = self.validate([
            self.declaration("mode", "enum", options=["a", "b"], min=0, max=1),
        ])
        self.assertIsNone(error)
        self.assertEqual(agreed["params"][0]["max"], 1)

        self.assert_invalid([self.declaration("mode", "float", options=["a", "b"])])
        self.assert_invalid([self.declaration("mode", "enum", options=["only"])])
        self.assert_invalid([self.declaration("mode", "enum", options=["a", "a"])])
        self.assert_invalid([self.declaration("mode", "enum", options=["a", "b\n"])])
        self.assert_invalid([
            self.declaration("mode", "enum", options=["a", "b"], max=7)])
        self.assert_invalid([
            self.declaration("mode", "enum", options=["a", "b"], default=.5)])

    def test_event_declarations_are_validated_beside_the_params(self):
        loaded, error = self.validate(
            [self.declaration("gain")],
            events=[{"name": "note", "arity": 2,
                     "labels": ["pitch", "velocity"], "defaults": [64, 127]},
                    {"name": "hit", "path": ["drum"]}],
        )
        self.assertIsNone(error)
        self.assertEqual(loaded["events"][0]["arity"], 2)
        # Arity defaults to a single element, the mockup's `event[1]`.
        self.assertEqual(loaded["events"][1]["arity"], 1)
        self.assertEqual(
            manifest.qualify_param(loaded["events"][1]), "drum/hit")

        self.assert_invalid(events=[{"name": "note", "arity": 4}])
        self.assert_invalid(events=[{"name": "note", "arity": 2,
                                     "labels": ["only"]}])
        self.assert_invalid(events=[{"name": "note", "defaults": ["loud"]}])
        self.assert_invalid(events=[{"name": "note"}, {"name": "note"}])
        self.assert_invalid(events=[{"name": "bad name"}])
        self.assert_invalid(events="note")
        # An event and a param cannot claim the same address.
        self.assert_invalid([self.declaration("note", "int", min=0, max=1)],
                            events=[{"name": "note"}])

    def test_atomic_write_normalizes_without_mutating_the_candidate(self):
        candidate = self.candidate([
            self.declaration(facilitator=True, group="legacy-layout")
        ])
        original = json.loads(json.dumps(candidate))

        written, error = manifest.write_atomic(self.patch, candidate)

        self.assertIsNone(error)
        self.assertEqual(candidate, original)
        self.assertEqual(
            json.loads((self.patch / manifest.MANIFEST_NAME).read_text()),
            written,
        )
        self.assertTrue(written["params"][0]["dashboard"])
        self.assertNotIn("facilitator", written["params"][0])
        self.assertNotIn("group", written["params"][0])


if __name__ == "__main__":
    unittest.main()
