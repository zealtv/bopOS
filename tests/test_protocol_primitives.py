"""Durable tests for selector-free engine and run-context primitives."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import groups  # noqa: E402
import relay  # noqa: E402
import runcontext  # noqa: E402
from store import Store  # noqa: E402
from sync_node import SyncState  # noqa: E402


class EngineRelayTests(unittest.TestCase):
    def test_patch_tail_and_arguments_survive_selector_removal(self):
        values = [0.5, 7, "tail"]
        for selector in ("all", "12", "g3"):
            with self.subTest(selector=selector):
                self.assertEqual(
                    relay.shape_provided_term(
                        [selector, "p", "track", "fx", "gain"], values
                    ),
                    ("/p/track/fx/gain", values),
                )

    def test_master_is_single_valued_and_strict(self):
        self.assertEqual(
            relay.shape_provided_term(
                ["all", "os", "master"], [0.5, "ignored"]
            ),
            ("/os/master", [0.5]),
        )
        self.assertIsNone(
            relay.shape_provided_term(
                ["all", "os", "master", "nested"], [0.5]
            )
        )
        self.assertIsNone(
            relay.shape_provided_term(["all", "p", "gain"], [])
        )


class GroupRunContextTests(unittest.TestCase):
    def test_group_ids_and_wire_sentinel_are_canonical(self):
        self.assertEqual(groups.group_ids([9, 2]), (2, 9))
        self.assertEqual(groups.wire_groups((2, 9)), (2, 9))
        self.assertEqual(groups.wire_groups(()), (-1,))

        for values in ([1, 1], [-1], [2.0], ["2"], [True]):
            with self.subTest(values=values):
                self.assertIsNone(groups.group_ids(values))

    def test_run_context_reads_persisted_groups(self):
        with tempfile.TemporaryDirectory(prefix="bopos-groups-") as root:
            store = Store(str(Path(root) / "state" / "store"))
            self.assertTrue(store.put("groups", [9, 2]))
            self.assertEqual(runcontext.resolve_groups(root), [2, 9])

            context = runcontext.generate(
                repo_dir=root,
                patches_dir=str(Path(root) / "patches"),
                assets_dir=str(Path(root) / "assets"),
                now=0,
            )
            self.assertEqual(context["groups"], [2, 9])

    def test_missing_or_corrupt_groups_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="bopos-groups-empty-") as root:
            self.assertEqual(runcontext.resolve_groups(root), [-1])
            store = Store(str(Path(root) / "state" / "store"))
            self.assertTrue(store.put("groups", [1, 1]))
            self.assertEqual(runcontext.resolve_groups(root), [-1])


class SyncStateTests(unittest.TestCase):
    def test_offset_is_integer_and_slews_to_the_pushed_target(self):
        now = [1_000]
        state = SyncState(slew_ns=100, now=lambda: now[0])
        self.assertFalse(state.synced())
        self.assertEqual(state.offset(), 0)

        state.push("200")
        self.assertTrue(state.synced())
        self.assertEqual(state.offset(), 0)
        now[0] += 50
        self.assertEqual(state.offset(), 100)
        now[0] += 50
        self.assertEqual(state.offset(), 200)

    def test_zero_slew_applies_full_state_idempotently(self):
        state = SyncState(slew_ns=0, now=lambda: 0)
        state.push(75)
        self.assertEqual(state.offset(), 75)
        state.push(75)
        self.assertEqual(state.offset(), 75)


if __name__ == "__main__":
    unittest.main()
