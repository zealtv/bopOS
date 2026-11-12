"""Durable output-safety tests for the node and protocol simulator."""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "python"), str(ROOT / "tools")]

import pyOSC3  # noqa: E402
from pythonosc import osc_message, osc_message_builder  # noqa: E402


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
import simfleet  # noqa: E402

sys.argv = ORIGINAL_ARGV


class NodeOutputSafetyTests(unittest.TestCase):
    def test_effective_output_is_enabled_and_not_mute_all(self):
        for device_enabled, mute_all, expected in (
            (False, False, False),
            (False, True, False),
            (True, False, True),
            (True, True, False),
        ):
            with self.subTest(
                device_enabled=device_enabled, mute_all=mute_all
            ):
                state = types.SimpleNamespace(
                    device_enabled=device_enabled,
                    mute_all=mute_all,
                )
                self.assertEqual(bopos.output_enabled(state), expected)

    def test_auto_detect_targets_non_hdmi_dac_and_remembers_winner(self):
        state = types.SimpleNamespace(
            config={"SOUNDCARD": None, "MIXER_CONTROL": None},
            mixer_control=None,
        )
        calls = []

        def run(argv, wait_for_start=False):
            calls.append(argv)
            return int(not (
                "-c" in argv
                and argv[argv.index("-c") + 1] == "DigiAMP"
                and "Digital" in argv
            ))

        with (
            mock.patch.object(
                bopos, "_alsa_card_ids",
                return_value=["vc4hdmi", "DigiAMP"],
            ),
            mock.patch.object(bopos, "run_command", side_effect=run),
        ):
            self.assertTrue(bopos.enforce_mute(1, state))
            self.assertEqual(state.mixer_control, ("DigiAMP", "Digital"))
            self.assertFalse(any(
                "-c" in argv
                and argv[argv.index("-c") + 1] == "vc4hdmi"
                for argv in calls
            ))

            calls.clear()
            self.assertTrue(bopos.enforce_mute(0, state))
            self.assertEqual(len(calls), 1)
            self.assertIn("DigiAMP", calls[0])
            self.assertIn("Digital", calls[0])
            self.assertIn("unmute", calls[0])

    def test_configured_target_wins(self):
        state = types.SimpleNamespace(
            config={"SOUNDCARD": "card9", "MIXER_CONTROL": "Line Out"},
            mixer_control=None,
        )
        calls = []

        def run(argv, wait_for_start=False):
            calls.append(argv)
            return 0

        with (
            mock.patch.object(bopos, "_alsa_card_ids", return_value=[]),
            mock.patch.object(bopos, "run_command", side_effect=run),
        ):
            self.assertTrue(bopos.enforce_mute(1, state))

        self.assertIn("card9", calls[0])
        self.assertIn("Line Out", calls[0])
        self.assertIn("mute", calls[0])

    def test_missing_mixer_fails_without_engine_lifecycle_fallback(self):
        state = types.SimpleNamespace(
            config={"SOUNDCARD": None, "MIXER_CONTROL": None},
            mixer_control=None,
        )
        calls = []

        with (
            mock.patch.object(bopos, "_alsa_card_ids", return_value=[]),
            mock.patch.object(
                bopos, "run_command",
                side_effect=lambda argv, wait_for_start=False:
                calls.append(argv) or 1,
            ),
        ):
            self.assertFalse(bopos.enforce_mute(1, state))
            self.assertFalse(bopos.enforce_mute(0, state))

        self.assertTrue(calls)
        self.assertTrue(all(argv[0] == "amixer" for argv in calls))


class CaptureSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        message = osc_message.OscMessage(data)
        self.calls.append((message.address, list(message.params), target))


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


class SimfleetOutputSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-mute-sim-")
        self.device = simfleet.Device(
            "02:00:00:00:00:05", "sim5", 5, "abc1234"
        )
        self.device.state = "running"
        self.fleet = object.__new__(simfleet.SimFleet)
        self.fleet.args = types.SimpleNamespace(
            state_dir=self.temp.name,
            report_port=5550,
            drop=0.0,
        )
        self.fleet.devices = [self.device]
        self.fleet.protocol = simfleet.ContractProtocol()
        self.fleet.sock = CaptureSocket()
        self.fleet.log = lambda *_args: None
        self.source = ("10.0.0.8", 4000)

    def tearDown(self):
        self.temp.cleanup()

    def send(self, address, *args):
        self.fleet.receive_contract(packet(address, *args), self.source)

    def enabled_receipt(self):
        address, args, _target = self.fleet.sock.calls[-1]
        self.assertEqual(address, "/os/enabled")
        return args

    def test_device_intent_stages_under_fleet_safety_then_release_exposes_it(self):
        self.send("/all/os/mute", 1)
        self.assertTrue(self.device.mute_all)
        self.assertFalse(self.device.output_enabled)

        self.send(
            "/all/os/to", self.device.mac, "enabled", 1
        )
        self.assertEqual(
            self.enabled_receipt(),
            [self.device.mac, 1, 0],
        )
        self.assertTrue(self.device.device_enabled)
        self.assertFalse(self.device.output_enabled)

        self.send("/all/os/mute", 0)
        self.assertFalse(self.device.mute_all)
        self.assertTrue(self.device.output_enabled)

    def test_persistent_disable_survives_reconstruction_but_mute_all_does_not(self):
        self.send(
            "/all/os/to", self.device.mac, "enabled", 0
        )
        self.assertEqual(
            self.enabled_receipt(),
            [self.device.mac, 0, 0],
        )
        self.send("/all/os/mute", 1)

        restored = simfleet.Device(
            self.device.mac, "restored", 5, "abc1234"
        )
        restored.load_assignment(self.temp.name)

        self.assertFalse(restored.device_enabled)
        self.assertFalse(restored.mute_all)
        self.assertFalse(restored.output_enabled)

    def test_report_exposes_requested_and_effective_states(self):
        self.send("/all/os/mute", 1)
        self.fleet.start_monotonic = 0
        self.fleet.send_report(self.device, self.source)
        address, args, _target = self.fleet.sock.calls[-1]
        report = json.loads(args[0])

        self.assertEqual(address, "/os/report")
        self.assertEqual(
            {
                "device_enabled": report["device_enabled"],
                "mute_all": report["mute_all"],
                "output_enabled": report["output_enabled"],
            },
            {
                "device_enabled": True,
                "mute_all": True,
                "output_enabled": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
