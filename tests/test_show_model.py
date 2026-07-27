#!/usr/bin/env python3
"""Living tests for the Show document model and tolerant persistence."""

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))

import show_model  # noqa: E402


def message(uid="b0000001", target="all", **extra):
    return {
        "uid": uid,
        "alias": None,
        "address": "/p/gain",
        "args": [{"type": "f", "value": 0.5}],
        "target": target,
        **extra,
    }


def step(uid="a0000001", messages=None, **extra):
    return {
        "kind": "step",
        "uid": uid,
        "alias": None,
        "messages": list(messages or []),
        "duration_s": 2,
        "play_count": 1,
        "then_actions": [{"type": "stop"}],
        **extra,
    }


def document(items=None, name="opening-set", **extra):
    return {
        "schema": 1,
        "name": name,
        "items": list(items or []),
        **extra,
    }


class ShowSchemaTests(unittest.TestCase):
    def test_cleaning_normalizes_legacy_targets_and_ignores_additive_fields(self):
        cleaned = show_model.clean_show(document([
            step(messages=[
                message(
                    target="3",
                    future_message_fact={"supported": "later"},
                )
            ], future_step_fact=True),
            {
                "kind": "divider",
                "uid": "d0000001",
                "future_divider_fact": 7,
            },
        ], future_document_fact="ignored"))

        self.assertEqual(
            cleaned["items"][0]["messages"][0]["target"],
            ["3"],
        )
        self.assertEqual(cleaned["items"][1]["alias"], None)
        self.assertNotIn("future_document_fact", cleaned)
        self.assertNotIn("future_step_fact", cleaned["items"][0])

    def test_typed_arguments_and_targets_reject_ambiguous_values(self):
        valid = message(
            target=["g3", "3", "g3"],
            args=[
                {"type": "i", "value": 2},
                {"type": "f", "value": 0.25},
                {"type": "s", "value": "warm"},
            ],
        )
        cleaned = show_model.clean_message(valid)
        self.assertEqual(cleaned["target"], ["g3", "3"])
        self.assertEqual(
            cleaned["args"],
            [
                {"type": "i", "value": 2},
                {"type": "f", "value": 0.25},
                {"type": "s", "value": "warm"},
            ],
        )

        for bad in (
            message(target=[]),
            message(target=["seat3"]),
            message(args=[{"type": "i", "value": True}]),
            message(args=[{"type": "f", "value": float("nan")}]),
            message(address="gain"),
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(show_model.clean_message(bad))

    def test_uids_are_unique_with_separate_item_and_message_namespaces(self):
        shared = "a0000001"
        valid = document([
            step(shared, [message(shared)]),
        ])
        self.assertIsNotNone(show_model.clean_show(valid))

        duplicate_items = document([
            step(shared),
            {"kind": "divider", "uid": shared},
        ])
        self.assertIsNone(show_model.clean_show(duplicate_items))

        duplicate_messages = document([
            step("a0000001", [message("b0000001")]),
            step("a0000002", [message("b0000001")]),
        ])
        self.assertIsNone(show_model.clean_show(duplicate_messages))

    def test_zero_duration_requires_a_finite_play_count(self):
        self.assertIsNotNone(show_model.clean_step(
            step(duration_s=0, play_count=1)
        ))
        self.assertIsNone(show_model.clean_step(
            step(duration_s=0, play_count=None)
        ))
        self.assertIsNotNone(show_model.clean_step(
            step(duration_s=1, play_count=None)
        ))

    def test_sections_are_maximal_step_runs_without_empty_gaps(self):
        first, second = step("a0000001"), step("a0000002")
        third = step("a0000003")
        show = document([
            {"kind": "divider", "uid": "d0000001"},
            first,
            second,
            {"kind": "divider", "uid": "d0000002"},
            {"kind": "divider", "uid": "d0000003"},
            third,
            {"kind": "divider", "uid": "d0000004"},
        ])
        self.assertEqual(
            show_model.sections(show),
            [[first, second], [third]],
        )

    def test_edits_are_copy_on_write_and_duplicate_mints_nested_identities(self):
        original = document([step(messages=[message()])])
        before = deepcopy(original)
        minted = iter(("a0000002", "b0000002"))

        with mock.patch.object(
            show_model, "mint_uid", side_effect=lambda _existing: next(minted)
        ):
            updated, duplicate, error = show_model.duplicate_item(
                original, "a0000001"
            )

        self.assertIsNone(error)
        self.assertEqual(original, before)
        self.assertEqual(
            [item["uid"] for item in updated["items"]],
            ["a0000001", "a0000002"],
        )
        self.assertEqual(duplicate["messages"][0]["uid"], "b0000002")


class ShowPersistenceTests(unittest.TestCase):
    def test_round_trip_preserves_item_and_message_order_without_temp_residue(self):
        show = show_model.clean_show(document([
            step("a0000001", [
                message("b0000001"),
                message("b0000002", address="/p/pan"),
            ]),
            {"kind": "divider", "uid": "d0000001", "alias": "Act II"},
            step("a0000002"),
        ]))
        with tempfile.TemporaryDirectory() as temporary:
            show_model.save_show(temporary, show)
            self.assertEqual(show_model.load_show(temporary, show["name"]), show)
            self.assertFalse(
                any(path.suffix == ".tmp" for path in Path(temporary).iterdir())
            )

    def test_missing_empty_corrupt_and_invalid_documents_load_as_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            expected = show_model.empty_show("broken")
            self.assertEqual(
                show_model.load_show(temporary, "broken"),
                expected,
            )
            path = Path(temporary) / "broken.json"
            for content in (
                "",
                "{not json",
                json.dumps({"schema": 99, "name": "broken", "items": []}),
                json.dumps(document([
                    step("a0000001"),
                    step("a0000001"),
                ], name="broken")),
            ):
                with self.subTest(content=content):
                    path.write_text(content)
                    self.assertEqual(
                        show_model.load_show(temporary, "broken"),
                        expected,
                    )

    def test_create_refuses_to_clobber_and_catalog_is_sorted(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, error = show_model.create_show(temporary, "z-show")
            self.assertIsNone(error)
            self.assertEqual(first, show_model.empty_show("z-show"))
            show_model.create_show(temporary, "a-show")

            duplicate, error = show_model.create_show(temporary, "z-show")
            self.assertIsNone(duplicate)
            self.assertTrue(error)
            self.assertEqual(
                show_model.list_shows(temporary),
                ["a-show", "z-show"],
            )


if __name__ == "__main__":
    unittest.main()
