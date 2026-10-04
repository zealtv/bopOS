#!/usr/bin/env python3
"""Living regression tests for the engine-ready delivery/replay boundary.

Covers 36-engine-startup-delivery-race: a freshly-flashed node was going
unresponsive in the Dashboard (SSH still fine) because a provided-term send to
the not-yet-open engine port raised ConnectionRefusedError, which -- being an
OSError -- propagated up to lan_listener_loop's `except OSError` and tore the
LAN socket down mid-startup. The fix: send_to_engine swallows connection-level
errors so no LAN handler can leak them, and deliver_engine_context redelivers
durable authoritative state (id, groups, latest static params) once the engine
port opens (0 -> 1 engine-alive transition in heartbeat_loop).

Browser-free / node-protocol: imports bopos with pyOSC3's server/client faked,
exactly like tests/test_node_fetch_dispatch.py.
"""

import sys
import types
import unittest
from unittest import mock
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
PYTHON = REPO / "python"
if str(PYTHON) not in sys.path:
    sys.path.insert(0, str(PYTHON))

import pyOSC3  # noqa: E402
import paramgen  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
ORIGINAL_ARGV = sys.argv
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402

sys.argv = ORIGINAL_ARGV


class ControllableClient:
    """Stands in for the bopos->engine OSC client: can refuse (engine down) or
    capture the OSC addresses it is asked to send (engine up)."""

    def __init__(self):
        self.refuse = False
        self.sent = []

    def connect(self, _target):
        pass

    def send(self, message):
        if self.refuse:
            # Faithful to the real library: pyOSC3's OSCClient.send catches the
            # socket error and re-raises it wrapped in OSCClientError, which is
            # NOT an OSError. An earlier fake raised a raw ConnectionRefusedError
            # and so missed that `except OSError` never caught the real refusal.
            raise pyOSC3.OSCClientError("while sending: [Errno 111] Connection refused")
        self.sent.append(str(message.address))


class EngineReadyReplayTests(unittest.TestCase):
    def setUp(self):
        self.client = ControllableClient()
        bopos.client = self.client
        self.io = mock.Mock()
        io_patch = mock.patch.object(bopos, 'node_io', return_value=self.io)
        io_patch.start()
        self.addCleanup(io_patch.stop)
        # Isolate the replay store between tests.
        with bopos.param_replay_lock:
            bopos.latest_static_params.clear()

    # --- responsiveness: a refusing engine must never raise into a handler ---

    def test_send_to_engine_swallows_connection_refused(self):
        self.client.refuse = True
        # Must return False, not raise -- otherwise it reaches lan_listener_loop.
        self.assertIs(bopos.send_to_engine(pyOSC3.OSCMessage("/id")), False)

    def test_send_to_engine_reports_success_when_engine_up(self):
        self.assertIs(bopos.send_to_engine(pyOSC3.OSCMessage("/id")), True)
        self.assertEqual(self.client.sent, ["/id"])

    def test_notify_keeps_string_payload_and_reports_transport_result(self):
        packets = []
        with mock.patch.object(bopos, "send_to_engine", side_effect=lambda msg:
                               packets.append(pyOSC3.decodeOSC(msg.getBinary())) or False):
            self.assertIs(bopos.notify_engine("restart-engine"), False)
        self.assertEqual(packets, [["/notify", ",s", "restart-engine"]])

    def test_transient_traffic_is_handled_even_when_engine_is_down(self):
        self.client.refuse = True
        self.assertTrue(bopos.relay_provided_term("/os/master", [0.5]))
        bopos.send_groups_to_engine(types.SimpleNamespace(groups=(2,)))
        bopos.fire_event_to_engine("go", [])
        state = types.SimpleNamespace(points={}, elements=[[0, 0], [1, 1]])
        self.assertTrue(bopos.apply_points(["pt"], [2, 0.0, 0.0, 1.0, 0], state))
        with mock.patch.object(bopos, "node_state", types.SimpleNamespace(
                store=mock.Mock(get=mock.Mock(return_value=[0.5])))):
            bopos.load_callback(args=["gain"])
        self.assertEqual(self.client.sent, [])

    def test_identity_is_int32_on_assignment_unassignment_ready_and_config(self):
        packets = []
        state = types.SimpleNamespace(
            uid="test-node", id=3, groups=(), elements=[],
            store=mock.Mock(put=mock.Mock(return_value=True),
                            get=mock.Mock(return_value=[4, "Seat 4"])))
        with mock.patch.object(bopos, "send_to_engine", side_effect=lambda msg:
                               packets.append(pyOSC3.decodeOSC(msg.getBinary())) or True):
            self.assertTrue(bopos.apply_assign(["test-node", 4, "Seat 4"], state))
            self.assertTrue(bopos.apply_unassign(state))
            self.assertTrue(bopos.deliver_engine_context(state))
            with mock.patch.object(bopos, "node_state", state):
                bopos.config_callback()
        self.assertEqual([packet[1:] for packet in packets if packet[0] == "/id"],
                         [[",i", 4], [",i", -1], [",i", -1], [",i", -1]])

    def test_unwrapped_engine_send_path_does_not_raise_when_down(self):
        # config_callback sends /id to the engine with no local try/except; when
        # the engine refuses it must still not raise (used to kill the listener).
        self.client.refuse = True
        try:
            bopos.config_callback()
        except OSError as error:  # pragma: no cover - the bug we are fixing
            self.fail("config_callback leaked a connection error: %r" % (error,))

    # --- delivery/replay: durable state redelivered once the engine is ready --

    def test_deliver_engine_context_redelivers_id_and_groups(self):
        state = types.SimpleNamespace(id=7, groups=())
        self.assertIs(bopos.deliver_engine_context(state), True)
        self.assertIn("/id", self.client.sent)
        self.assertIn("/groups", self.client.sent)

    def test_ready_and_config_create_manifest_modules_with_existing_grammar(self):
        rows = [{'name': 'tilt', 'type': 'lis3dh', 'address': '0x19'}]
        state = types.SimpleNamespace(id=7, groups=())
        with mock.patch.object(bopos, 'active_patch_path', return_value='/fixture'), \
                mock.patch.object(bopos.manifest, 'load', return_value=({'io_modules': rows}, None)), \
                mock.patch.object(bopos, 'node_state', state):
            self.assertTrue(bopos.deliver_engine_context(state))
            bopos.config_callback()
        self.assertEqual(self.io.send_bridge.call_args_list, [
            mock.call('/io/create', ['tilt', 'lis3dh', '0x19'])] * 2)
        self.assertEqual(self.io.refresh.call_count, 2)

    def test_bridge_send_failure_retries_readiness_and_does_not_kill_config(self):
        self.io.refresh.side_effect = OSError('bridge unavailable')
        state = types.SimpleNamespace(id=7, groups=())
        self.assertFalse(bopos.deliver_engine_context(state))
        bopos.config_callback()

    def test_deliver_engine_context_reports_failure_when_port_refuses(self):
        # engine_alive() can lead PD binding its port; the redelivery must not
        # raise (that killed the heartbeat thread) and must report False so the
        # caller retries instead of dropping durable context.
        self.client.refuse = True
        state = types.SimpleNamespace(id=7, groups=())
        try:
            delivered = bopos.deliver_engine_context(state)
        except Exception as error:  # pragma: no cover - the bug we are fixing
            self.fail("deliver_engine_context leaked %r" % (error,))
        self.assertIs(delivered, False)
        self.assertEqual(self.client.sent, [])

    def test_static_param_recorded_and_replayed(self):
        state = types.SimpleNamespace(id=3, groups=())
        spec = paramgen.ParamSpec("set", value=0.5)
        bopos.record_static_param("gain", spec, {"kind": "float"})
        with bopos.param_replay_lock:
            self.assertIn("gain", bopos.latest_static_params)
        bopos.deliver_engine_context(state)
        self.assertIn("/p/gain", self.client.sent)

    def test_generator_spec_is_not_buffered_for_replay(self):
        # Automation (lfo/loop/fade/stop) is forgotten by design across restarts;
        # it must not be replayed, and it clears any stale static value.
        bopos.record_static_param("gain", paramgen.ParamSpec("set", value=0.5),
                                  {"kind": "float"})
        bopos.record_static_param("gain", paramgen.ParamSpec("stop"), {"kind": "float"})
        with bopos.param_replay_lock:
            self.assertNotIn("gain", bopos.latest_static_params)


class FingerprintCacheWarmerTests(unittest.TestCase):
    def test_each_inventory_coalesces_its_own_warm_and_can_restart(self):
        assets = bopos.FingerprintCacheWarmer("asset")
        patches = bopos.FingerprintCacheWarmer("patch")
        with mock.patch.object(bopos.threading, "Thread") as thread_factory:
            asset_thread, patch_thread, next_thread = (mock.Mock() for _ in range(3))
            thread_factory.side_effect = [asset_thread, patch_thread, next_thread]
            self.assertIs(assets.warm("assets"), asset_thread)
            self.assertIs(assets.warm("assets"), asset_thread)
            self.assertIs(patches.warm("patches"), patch_thread)
            asset_thread.start.assert_called_once_with()
            patch_thread.start.assert_called_once_with()
            asset_thread.is_alive.return_value = False
            self.assertIs(assets.warm("assets"), next_thread)
            self.assertEqual(thread_factory.call_count, 3)
            self.assertTrue(all(call.kwargs["daemon"] for call in thread_factory.call_args_list))

    def test_initialise_loads_cache_before_warming_even_if_load_fails(self):
        warmer = bopos.FingerprintCacheWarmer("patch")
        events = []
        def load(root):
            events.append(("load", root))
            raise OSError("unreadable")
        with mock.patch.object(bopos.identity, "load_hash_cache", side_effect=load), \
                mock.patch.object(warmer, "warm", side_effect=lambda root:
                                  events.append(("warm", root)) or "thread"), \
                mock.patch("builtins.print"):
            self.assertEqual(warmer.initialise("patches"), "thread")
        self.assertEqual(events, [("load", "patches"), ("warm", "patches")])

    def test_rejected_priority_does_not_skip_warming_and_warm_error_is_caught(self):
        for kind in ("asset", "patch"):
            with self.subTest(kind=kind), \
                    mock.patch.object(bopos.os, "nice", side_effect=OSError("unsupported")), \
                    mock.patch.object(bopos.identity, "warm_hash_cache",
                                      side_effect=OSError("unreadable")) as warm, \
                    mock.patch("builtins.print") as warning:
                bopos.FingerprintCacheWarmer(kind)._run("root")
                warm.assert_called_once_with("root")
                self.assertEqual(warning.call_args.args[0],
                                 f"WARNING: {kind} fingerprint warm failed:")


if __name__ == "__main__":
    unittest.main()
