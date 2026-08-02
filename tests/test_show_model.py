#!/usr/bin/env python3
"""Living tests for the Show document model and tolerant persistence."""

import asyncio
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))

import show_model  # noqa: E402
from server import Dashboard  # noqa: E402
from show_engine import ShowEngine  # noqa: E402
from state import InstallationState  # noqa: E402


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

    def test_reference_payload_survives_clean_duplicate_move_and_persistence(self):
        reference = {
            "content": {"name": "alpha", "fingerprint": "a" * 64},
            "schema": "sha256:" + "b" * 64,
        }
        original = show_model.clean_show(document([
            step("a0000001", [
                message("b0000001", kind="reference", reference=reference),
            ]),
            step("a0000002"),
        ]))
        self.assertEqual(
            original["items"][0]["messages"][0]["reference"],
            reference,
        )

        minted = iter(("a0000003", "b0000002"))
        with mock.patch.object(
            show_model, "mint_uid", side_effect=lambda _existing: next(minted)
        ):
            duplicated, clone, error = show_model.duplicate_item(
                original, "a0000001"
            )
        self.assertIsNone(error)
        self.assertEqual(clone["messages"][0]["reference"], reference)
        moved, result, error = show_model.move_message(
            duplicated, "b0000001", "a0000002"
        )
        self.assertIsNone(error)
        self.assertEqual(result["reference"], reference)

        with tempfile.TemporaryDirectory() as temporary:
            show_model.save_show(temporary, moved)
            loaded = show_model.load_show(temporary, moved["name"])
        moved_message = loaded["items"][1]["messages"][0]
        self.assertEqual(moved_message["kind"], "reference")
        self.assertEqual(moved_message["reference"], reference)

    def test_reference_payload_is_explicit_and_strict(self):
        valid_reference = {
            "content": {"name": "alpha", "fingerprint": "a" * 64},
        }
        self.assertIsNotNone(show_model.clean_message(
            message(kind="reference", reference=valid_reference)
        ))
        for bad in (
            message(kind="reference"),
            message(kind="osc", reference=valid_reference),
            message(kind="reference", reference={
                "content": {"name": "../alpha", "fingerprint": "a" * 64},
            }),
            message(kind="reference", reference={
                "content": {"name": "alpha", "fingerprint": "short"},
            }),
            message(kind="reference", reference={
                "content": {"name": "alpha", "fingerprint": "a" * 64},
                "schema": "bad",
            }),
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(show_model.clean_message(bad))

    def test_named_group_targets_resolve_with_non_blocking_warnings(self):
        groups = [
            {"id": 7, "name": "Front"},
            {"id": 9, "name": "Twin"},
            {"id": 10, "name": "Twin"},
        ]
        resolved, warnings = show_model.resolve_targets(
            ["3", "group:Front", "group:Missing", "group:Twin"], groups
        )
        self.assertEqual(resolved, ["3", "g7"])
        self.assertEqual(
            [warning["code"] for warning in warnings],
            ["missing_group", "ambiguous_group"],
        )

    def test_playback_uses_dashboard_resolved_group_wire_selector(self):
        bridge = mock.Mock()
        groups = {"7": {"id": 7, "name": "Front"}}
        engine = ShowEngine(
            bridge,
            mock.AsyncMock(),
            resolve_targets=lambda targets: show_model.resolve_targets(
                targets, groups)[0],
        )
        engine._send_message(show_model.clean_message(
            message(target=["group:Front"])
        ))
        bridge.set_param.assert_called_once_with("g7", "gain", [0.5])

    def test_unhandled_reference_fails_closed_instead_of_sending_raw_osc(self):
        bridge = mock.Mock()
        engine = ShowEngine(bridge, mock.AsyncMock())
        engine._send_message(show_model.clean_message(message(
            kind="reference",
            address="/content/example",
            reference={
                "content": {"name": "alpha", "fingerprint": "a" * 64},
            },
        )))
        bridge.send.assert_not_called()
        bridge.set_param.assert_not_called()

    def test_preset_reference_has_strict_args_and_uses_injected_application(self):
        reference = {
            "content": {"name": "alpha", "fingerprint": "a" * 64},
            "schema": "sha256:" + "b" * 64,
        }
        preset = show_model.clean_message(message(
            kind="reference",
            address="/preset/alpha/Dawn",
            args=[
                {"type": "f", "value": 250},
                {"type": "s", "value": "c:-1"},
            ],
            target=["group:Front", "3"],
            reference=reference,
        ))
        apply = mock.Mock()
        bridge = mock.Mock()
        engine = ShowEngine(bridge, mock.AsyncMock(), apply_preset=apply)

        engine._send_message(preset)

        apply.assert_called_once_with(
            "alpha", "Dawn", ["group:Front", "3"], 250.0, -1.0,
            reference)
        bridge.send.assert_not_called()
        for bad_args in (
            [{"type": "s", "value": "250ms"}],
            [{"type": "f", "value": -1}],
            [{"type": "s", "value": "c:1"}, {"type": "f", "value": 2}],
        ):
            with self.subTest(args=bad_args):
                self.assertIsNone(show_model.clean_message(message(
                    kind="reference", address="/preset/alpha/Dawn",
                    args=bad_args, reference=reference)))

    def test_preset_drift_warnings_cover_patch_and_schema_independently(self):
        reference = {
            "content": {"name": "alpha", "fingerprint": "a" * 64},
            "schema": "sha256:" + "b" * 64,
        }
        show = show_model.clean_show(document([
            step(messages=[message(
                kind="reference", address="/preset/alpha/Dawn",
                args=[], reference=reference,
            )]),
        ]))
        warnings = show_model.show_reference_warnings(
            show, {"alpha": "c" * 64},
            {"alpha": "sha256:" + "d" * 64})
        self.assertEqual(
            [warning["code"] for warning in warnings],
            ["patch_drift", "schema_drift"])
        self.assertTrue(all(
            warning["message_uid"] == "b0000001" for warning in warnings))

    def test_flatten_is_one_atomic_model_mutation(self):
        reference = {
            "content": {"name": "alpha", "fingerprint": "a" * 64},
            "schema": "sha256:" + "b" * 64,
        }
        preset = message(
            kind="reference", address="/preset/alpha/Dawn",
            args=[], reference=reference)
        show = show_model.clean_show(document([step(messages=[preset])]))
        flattened = [
            {"kind": "osc", "alias": None, "address": "/p/gain",
             "args": [{"type": "f", "value": 0.5}], "target": ["all"]},
            {"kind": "osc", "alias": None, "address": "/p/mode",
             "args": [{"type": "i", "value": 1}], "target": ["all"]},
        ]

        next_show, result, error = show_model.flatten_preset_message(
            show, "b0000001", flattened)
        self.assertIsNone(error)
        self.assertEqual(len(result), 2)
        self.assertEqual(
            [item["address"] for item in next_show["items"][0]["messages"]],
            ["/p/gain", "/p/mode"])
        self.assertEqual(
            show["items"][0]["messages"][0]["address"],
            "/preset/alpha/Dawn")


class ShowPlaybackOrderingTests(unittest.IsolatedAsyncioTestCase):
    async def test_preset_reference_finishes_before_following_param_message(self):
        value = {"gain": None}

        async def apply_preset(*_args):
            value["gain"] = 0.25

        bridge = mock.Mock()
        bridge.set_param.side_effect = (
            lambda _selector, _name, args: value.__setitem__("gain", args[0]))
        engine = ShowEngine(
            bridge, mock.AsyncMock(), apply_preset=apply_preset)
        reference = {
            "content": {"name": "alpha", "fingerprint": "a" * 64},
            "schema": "sha256:" + "b" * 64,
        }
        engine.show = show_model.clean_show(document([
            step(messages=[
                message(
                    kind="reference", address="/preset/alpha/Dawn",
                    args=[], reference=reference),
                message(uid="b0000002", args=[{"type": "f", "value": 0.9}]),
            ]),
        ]))

        await engine.step_start("a0000001")
        # Before the fix the reference is a detached task, so let it run and
        # expose the late preset overwrite.
        await asyncio.sleep(0)

        self.assertEqual(value["gain"], 0.9)

class ShowUndoTests(unittest.IsolatedAsyncioTestCase):
    async def test_reference_update_and_undo_restore_one_persisted_snapshot(self):
        reference = {
            "content": {"name": "alpha", "fingerprint": "a" * 64},
        }
        original = show_model.clean_show(document([
            step(messages=[message()]),
        ]))
        dashboard = object.__new__(Dashboard)
        dashboard.show_edit_lock = asyncio.Lock()
        dashboard.show_undo = []
        dashboard.state = SimpleNamespace(
            data={"current_show": original["name"], "groups": {}}
        )
        dashboard.show = original
        dashboard.show_engine = SimpleNamespace(show=original)
        dashboard.broadcast = mock.AsyncMock()

        with tempfile.TemporaryDirectory() as temporary:
            dashboard.shows_dir = temporary
            show_model.save_show(temporary, original)
            await dashboard.apply_show_mutation(
                None, show_model.update_message, "b0000001",
                {"kind": "reference", "reference": reference},
            )
            self.assertEqual(len(dashboard.show_undo), 1)
            self.assertEqual(
                dashboard.show["items"][0]["messages"][0]["reference"],
                reference,
            )
            await dashboard.undo_show(None)
            self.assertEqual(
                dashboard.show["items"][0]["messages"][0]["kind"],
                "osc",
            )
            self.assertNotIn(
                "reference", dashboard.show["items"][0]["messages"][0]
            )


class GroupNameInvariantTests(unittest.TestCase):
    @staticmethod
    def state_document(groups, next_group_id=4):
        return {
            "schema": 1,
            "name": "Legacy room",
            "seats": {},
            "groups": groups,
            "next_group_id": next_group_id,
            "device_registry": {},
        }

    def test_existing_blank_and_duplicate_names_are_repaired_once(self):
        groups = {
            "0": {"id": 0, "name": ""},
            "1": {"id": 1, "name": "Front"},
            "2": {"id": 2, "name": "Front"},
            "3": {"id": 3, "name": "Front-2"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "installation.json"
            path.write_text(json.dumps(self.state_document(groups)))
            state = InstallationState(str(path))
            self.assertEqual(
                [group["name"] for group in state.data["groups"].values()],
                ["group-0", "Front", "Front-3", "Front-2"],
            )
            self.assertIn("repaired for portable Shows", state.data["notices"][0])

            reloaded = InstallationState(str(path))
            self.assertEqual(reloaded.data["notices"], [])
            self.assertEqual(
                [group["name"] for group in reloaded.data["groups"].values()],
                ["group-0", "Front", "Front-3", "Front-2"],
            )

    def test_create_and_rename_enforce_non_empty_unique_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = InstallationState(str(Path(temporary) / "installation.json"))
            front, error = state.create_group("Front")
            self.assertIsNone(error)
            self.assertIsNone(state.create_group(" ")[0])
            self.assertIn("non-empty", state.create_group(" ")[1])
            self.assertIn("unique", state.create_group("Front")[1])
            rear, error = state.create_group("Rear")
            self.assertIsNone(error)
            self.assertIn("unique", state.rename_group(rear["id"], "Front")[1])
            renamed, error = state.rename_group(front["id"], " Front ")
            self.assertIsNone(error)
            self.assertEqual(renamed["name"], "Front")

    def test_saved_venue_is_adopted_and_surfaces_the_renames_on_load(self):
        legacy_groups = {
            "4": {"id": 4, "name": ""},
            "5": {"id": 5, "name": "Side"},
            "6": {"id": 6, "name": "Side"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = InstallationState(str(root / "installation.json"))
            venues = root / "installations"
            venues.mkdir()
            venue_path = venues / "legacy.json"
            venue_path.write_text(json.dumps(
                self.state_document(legacy_groups, next_group_id=7)
            ))

            loaded, seats = state.read_venue("legacy")
            self.assertEqual(
                [group["name"] for group in loaded["groups"].values()],
                ["group-4", "Side", "Side-2"],
            )
            persisted = json.loads(venue_path.read_text())
            self.assertEqual(persisted["groups"], loaded["groups"])
            self.assertTrue(state.load_venue("legacy", (loaded, seats)))
            self.assertIn("g4 (blank) → group-4", state.data["notices"][-1])


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
