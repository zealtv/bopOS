#!/usr/bin/env python3
"""Living tests for physical Device audio configuration."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "python") not in sys.path:
    sys.path.insert(0, str(REPO / "python"))
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))

import audio_config  # noqa: E402
import pyOSC3  # noqa: E402


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
import audition  # noqa: E402
import simfleet  # noqa: E402
from store import Store  # noqa: E402
from pythonosc.osc_message import OscMessage  # noqa: E402
sys.argv = ORIGINAL_ARGV


CARDS = [{
    "id": "DigiAMP",
    "index": 1,
    "label": "IQaudIO DigiAMP",
    "mixer_controls": ["Digital"],
}]
CANDIDATE = {
    "card": "DigiAMP",
    "mixer_control": "Digital",
    "sample_rate": 48000,
    "period_size": 256,
    "nperiods": 3,
}


class Result:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class DatagramSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        message = OscMessage(data)
        self.calls.append((message.address, list(message.params), target))


class Node:
    def __init__(self, root, enabled=True, mute_all=False):
        self.uid = "node-a"
        self.id = 0
        self.version = "abc1234"
        self.update_model = "persistent"
        self.config = {
            "SOUNDCARD": "DigiAMP",
            "MIXER_CONTROL": "Digital",
            "JACK_SAMPLE_RATE": "44100",
            "JACK_PERIOD_SIZE": "512",
            "JACK_NPERIODS": "2",
            "AUDIO_CHANNELS": "2",
        }
        self.store = Store(os.path.join(root, "state", "store"))
        self.device_enabled = enabled
        self.mute_all = mute_all
        self.mixer_control = None
        self.groups = ()
        self.elements = []
        self.reports = {}
        self.reports_lock = threading.Lock()
        self.audio_status = "active"
        self.audio_error = None


class AudioConfigTests(unittest.TestCase):
    def test_discovers_playback_cards_and_controls(self):
        def runner(argv, **_kwargs):
            if argv == ["aplay", "-l"]:
                return Result(
                    "card 0: vc4hdmi [vc4-hdmi], device 0: HDMI 0 [HDMI 0]\n"
                    "card 1: DigiAMP [IQaudIO DigiAMP], device 0: "
                    "IQaudIO DAC [IQaudIO DAC]\n")
            if argv == ["amixer", "-c", "vc4hdmi", "scontrols"]:
                return Result("")
            if argv == ["amixer", "-c", "DigiAMP", "scontrols"]:
                return Result("Simple mixer control 'Digital',0\n")
            return Result(returncode=1)

        self.assertEqual(audio_config.discover_cards(runner), [
            {"id": "vc4hdmi", "index": 0, "label": "vc4-hdmi",
             "mixer_controls": []},
            CARDS[0],
        ])

    def test_validation_requires_complete_detected_values(self):
        self.assertEqual(audio_config.validate(CANDIDATE, CARDS), CANDIDATE)
        for mutation in (
                {**CANDIDATE, "card": "Missing"},
                {**CANDIDATE, "sample_rate": 12345},
                {**CANDIDATE, "period_size": True},
                {key: value for key, value in CANDIDATE.items()
                 if key != "nperiods"}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(audio_config.AudioConfigError):
                    audio_config.validate(mutation, CARDS)

    def test_config_update_preserves_unrelated_text_and_is_canonical(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "bopos.config")
            with open(path, "w") as target:
                target.write(
                    "# keep this\nHB_TARGET=example\nSOUNDCARD=Old\n"
                    "MIXER_CONTROL=PCM\n")
            spaced = {**CANDIDATE, "mixer_control": "Line Out"}
            audio_config.update_config_file(path, spaced)
            text = Path(path).read_text()
            self.assertIn("# keep this\nHB_TARGET=example\n", text)
            self.assertEqual(text.count("SOUNDCARD="), 1)
            self.assertIn("SOUNDCARD=DigiAMP", text)
            self.assertIn("JACK_SAMPLE_RATE=48000", text)
            parsed = bopos.read_node_config(path)
            self.assertEqual(audio_config.from_node_config(parsed), spaced)

    def test_success_persists_restarts_and_reapplies_disabled_safety(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "run").mkdir()
            config_path = Path(root, "bopos.config")
            config_path.write_text(
                "# local\nSOUNDCARD=DigiAMP\nMIXER_CONTROL=Digital\n")
            node, reply = Node(root, enabled=False), ReplySocket()
            with (mock.patch.object(bopos, "BOPOS_DIR", root),
                  mock.patch.object(audio_config, "discover_cards",
                                    return_value=CARDS),
                  mock.patch.object(bopos, "_restart_audio_engine",
                                    return_value=True) as restart,
                  mock.patch.object(bopos, "enforce_mute",
                                    return_value=True) as enforce):
                self.assertTrue(bopos.apply_audio_config(
                    json.dumps(CANDIDATE), reply, "10.0.0.8", node))
            self.assertEqual(restart.call_count, 1)
            enforce.assert_called_once_with(True, node)
            self.assertEqual(
                audio_config.from_node_config(node.config), CANDIDATE)
            self.assertEqual(audio_config.read_active(
                os.path.join(root, "run", "audio-config.json")), CANDIDATE)
            self.assertEqual(reply.calls[0][0][0:5], [
                "/os/audio-config", ",ssss", "node-a", "ok", "applied"])

    def test_audio_restart_reapplies_execution_mute_safety(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "run").mkdir()
            Path(root, "bopos.config").write_text(
                "SOUNDCARD=DigiAMP\nMIXER_CONTROL=Digital\n"
            )
            node, reply = Node(root, enabled=True, mute_all=True), ReplySocket()
            with (
                mock.patch.object(bopos, "BOPOS_DIR", root),
                mock.patch.object(
                    audio_config, "discover_cards", return_value=CARDS
                ),
                mock.patch.object(
                    bopos, "_restart_audio_engine", return_value=True
                ),
                mock.patch.object(
                    bopos, "enforce_mute", return_value=True
                ) as enforce,
            ):
                self.assertTrue(bopos.apply_audio_config(
                    json.dumps(CANDIDATE), reply, "10.0.0.8", node
                ))

            enforce.assert_called_once_with(True, node)
            self.assertTrue(node.device_enabled)
            self.assertTrue(node.mute_all)
            self.assertFalse(bopos.output_enabled(node))

    def test_failed_candidate_restores_file_and_old_engine(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "run").mkdir()
            config_path = Path(root, "bopos.config")
            original = (
                "# local\nSOUNDCARD=DigiAMP\nMIXER_CONTROL=Digital\n"
                "JACK_SAMPLE_RATE=44100\nJACK_PERIOD_SIZE=512\nJACK_NPERIODS=2\n")
            config_path.write_text(original)
            node, reply = Node(root), ReplySocket()
            with (mock.patch.object(bopos, "BOPOS_DIR", root),
                  mock.patch.object(audio_config, "discover_cards",
                                    return_value=CARDS),
                  mock.patch.object(bopos, "_restart_audio_engine",
                                    side_effect=(False, True)) as restart,
                  mock.patch.object(bopos, "enforce_mute", return_value=True)):
                self.assertFalse(bopos.apply_audio_config(
                    json.dumps(CANDIDATE), reply, "10.0.0.8", node))
            self.assertEqual(restart.call_count, 2)
            self.assertEqual(config_path.read_text(), original)
            self.assertEqual(node.audio_status, "rolled-back")
            self.assertEqual(reply.calls[0][0][4], "rolled-back")

    def test_rollback_failure_is_attributable(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "run").mkdir()
            Path(root, "bopos.config").write_text("SOUNDCARD=DigiAMP\n")
            node, reply = Node(root), ReplySocket()
            with (mock.patch.object(bopos, "BOPOS_DIR", root),
                  mock.patch.object(audio_config, "discover_cards",
                                    return_value=CARDS),
                  mock.patch.object(bopos, "_restart_audio_engine",
                                    side_effect=(False, False)),
                  mock.patch.object(bopos, "enforce_mute", return_value=True)):
                self.assertFalse(bopos.apply_audio_config(
                    json.dumps(CANDIDATE), reply, "10.0.0.8", node))
            self.assertEqual(node.audio_status, "error")
            self.assertEqual(reply.calls[0][0][4], "rollback-failed")

    def test_start_script_consumes_all_jack_settings(self):
        text = (REPO / "bash" / "start-engine.sh").read_text()
        for name in ("JACK_SAMPLE_RATE", "JACK_PERIOD_SIZE", "JACK_NPERIODS"):
            self.assertIn(name, text)
        self.assertIn("audio-config.json", text)

    def test_simfleet_and_audition_speak_the_same_audio_receipt(self):
        payload = json.dumps({
            "card": "Simulated",
            "mixer_control": "Master",
            "sample_rate": 48000,
            "period_size": 256,
            "nperiods": 3,
        })
        sim = simfleet.SimFleet.__new__(simfleet.SimFleet)
        sim.args = SimpleNamespace(report_port=5550, state_dir=None)
        sim.sock = DatagramSocket()
        device = simfleet.Device("node-a", "Node A", 0, "test")
        sim.uid_admin(device, "audio-config", [payload], ("127.0.0.1", 6000))

        rig = audition.AuditionRig.__new__(audition.AuditionRig)
        rig.args = SimpleNamespace(report_port=5550)
        rig.sock = DatagramSocket()
        node = audition.VirtualNode(0, 0, "audition-0001", 7000)
        rig.uid_admin(node, "audio-config", [payload], ("127.0.0.1", 6000))

        for call in (sim.sock.calls[0], rig.sock.calls[0]):
            self.assertEqual(call[0], "/os/audio-config")
            self.assertEqual(call[1][1:3], ["ok", "applied"])
            reported = json.loads(call[1][3])
            self.assertEqual(reported["configured"]["sample_rate"], 48000)


if __name__ == "__main__":
    unittest.main()
