"""Wi-Fi strict validation, stdin helper, redaction and fleet convergence."""
import asyncio
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "python"), str(REPO / "dashboard"), str(REPO / "tools")]
sys.dont_write_bytecode = True
from python import wifi_config as wifi
from server import Dashboard
from osc_bridge import OSCBridge
from state import InstallationState
import simfleet
from pythonosc.osc_message import OscMessage


def request(secret=None):
    return {"country": "GB", "networks": [{"ssid": "show", "hidden": True,
                                          "enabled": True, "psk": secret}]}


def observed(secret=True):
    return {"managed": True, "country": "GB", "active": "show",
            "networks": [{"ssid": "show", "hidden": True, "enabled": True,
                          "secret": secret}], "unmanaged": ["imager-net"]}


class ValidationTests(unittest.TestCase):
    def test_each_whole_request_rejection(self):
        good = request("x" * 8)
        bad = [None, [], {}, {"country": "GB"}, {"networks": good["networks"]}, dict(good, extra=True), dict(good, country="ZZ"),
               dict(good, country=[]), dict(good, country="gb"), dict(good, networks={}),
               dict(good, networks=[]), dict(good, networks=good["networks"] * 2)]
        row = good["networks"][0]
        bad_rows = [{}, None, dict(row, extra=1)]
        for key in row:
            missing = dict(row); missing.pop(key); bad_rows.append(missing)
        for key, values in {"ssid": [None, "", "x" * 33, "é" * 17, "\ud800"],
                            "hidden": [0, 1, None, "true"], "enabled": [0, 1, None, "false", False],
                            "psk": [False, 123, "x" * 7, "x" * 64, "é" * 8, "x" * 7 + "\n", "x" * 7 + "\x7f"]}.items():
            bad_rows.extend(dict(row, **{key: value}) for value in values)
        bad.extend(dict(good, networks=[item]) for item in bad_rows)
        for index, value in enumerate(bad):
            with self.subTest(case=index), self.assertRaises(ValueError):
                wifi.validate(value)

    def test_bounds_and_keep_secret(self):
        for size in (8, 63):
            wifi.validate(request(" " * size))
        wifi.validate(dict(request(), networks=[dict(request()["networks"][0], ssid="é" * 16)]), {"é" * 16})
        self.assertEqual(wifi.validate(request(), {"show"}), request())
        with self.assertRaises(ValueError):
            wifi.validate(request(), set())

    def test_projection_drops_secrets_everywhere(self):
        dirty = observed(); dirty["psk"] = "private"; dirty["networks"][0]["psk"] = "private"
        self.assertEqual(wifi.redacted(dirty), observed())
        self.assertEqual(wifi.redacted({"managed": False, "psk": "private"}), {"managed": False})
        self.assertEqual(wifi.clean_list(request("private")), wifi.metadata(request()))
        self.assertEqual(wifi.clean_list({"country": [], "networks": []}), {"country": "GB", "networks": []})
        secret = "wifi-" + uuid.uuid4().hex
        self.assertNotIn(secret, repr(OSCBridge._safe_wifi_args("/os/report", ['{"wifi":{"psk":"' + secret])))
        args = OSCBridge._safe_wifi_args("/os/wifi-config", ["node-a", "ok", "applied", json.dumps(observed()), secret])
        self.assertEqual(len(args), 5)
        self.assertNotIn(secret, repr(args))


class HelperTests(unittest.TestCase):
    def test_actual_fake_executable_stdin_no_arguments_and_node_receipt(self):
        # Use a subprocess, rather than mocking its result, to verify the seam.
        import test_log_config as node_fixture
        node = node_fixture.bopos
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            secret = "wifi-" + uuid.uuid4().hex
            helper = root / "fake-helper"
            capture = root / "stdin.json"
            helper.write_text("#!" + sys.executable + "\nimport sys,json\n"
                              "from pathlib import Path\n"
                              "state=" + repr(observed()) + "\n"
                              "if sys.argv[1:] != ['--status']:\n"
                              " assert sys.argv[1:]==[]\n"
                              " value=json.loads(sys.stdin.read())\n"
                              " Path(" + repr(str(capture)) + ").write_text(json.dumps(value))\n"
                              "print(json.dumps(state))\n")
            helper.chmod(0o755)
            real_run = subprocess.run
            calls = []
            def run(argv, **kwargs):
                calls.append(list(argv))
                return real_run(argv[2:], **kwargs)
            reply = node_fixture.ReplySocket()
            output = io.StringIO()
            with mock.patch.object(node.wifi_config.subprocess, "run", side_effect=run), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                # Node calls its module directly; inject only the executable path.
                apply = node.wifi_config.apply
                with mock.patch.object(node.wifi_config, "apply", side_effect=lambda payload: apply(payload, str(helper))):
                    self.assertTrue(node.apply_wifi_config(json.dumps(request(secret)), reply, "192.0.2.1", SimpleNamespace(uid="node-a")))
            self.assertEqual(calls, [["sudo", "-n", str(helper), "--status"], ["sudo", "-n", str(helper)]])
            self.assertEqual(json.loads(capture.read_text()), request(secret))
            self.assertNotIn(secret, output.getvalue() + repr(reply.calls))
            self.assertEqual(reply.calls[0][0][2:5], ["node-a", "ok", "applied"])
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["fake-helper", "stdin.json"])
            reply = node_fixture.ReplySocket()
            with mock.patch.object(node.wifi_config, "helper_status", return_value=observed()), \
                    mock.patch.object(node, "active_patch_path", return_value=None), \
                    mock.patch.object(node, "audio_report", return_value={}), \
                    mock.patch.object(node, "BOPOS_DIR", str(root)):
                node.report_reply(reply, "192.0.2.1", node_fixture.Node(str(root)))
            report = json.loads(reply.calls[0][0][2])
            self.assertEqual(report["wifi"], observed())
            self.assertNotIn(secret, repr(reply.calls))

    def test_helper_phases_and_no_secret_missing_keep(self):
        for code, phase in ((0, "applied"), (2, "invalid"), (3, "unavailable"), (1, "failed")):
            with mock.patch.object(wifi, "helper_status", return_value=observed()), \
                    mock.patch.object(wifi.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=json.dumps(observed()))):
                result = wifi.apply(json.dumps(request()))
            self.assertEqual(result[:2], ("ok" if code == 0 else "err", phase))
        with mock.patch.object(wifi, "helper_status", return_value=observed(False)), mock.patch.object(wifi.subprocess, "run") as run:
            self.assertEqual(wifi.apply(json.dumps(request()))[:2], ("err", "invalid"))
            run.assert_not_called()
        with mock.patch.object(wifi, "helper_status", return_value={"managed": False}):
            self.assertEqual(wifi.apply(json.dumps(request()))[:2], ("err", "unavailable"))
        with mock.patch.object(wifi.subprocess, "run", side_effect=OSError):
            self.assertEqual(wifi.helper_status(), {"managed": False})

    def test_installed_helper_seam_strict_and_unavailable(self):
        environment = dict(os.environ, PYTHONPATH=str(REPO / "python"))
        for args, payload, code in ((["--status"], "", 0), ([], json.dumps(request("x" * 8)), 3),
                                    ([], "{}", 2), (["secret-arg"], "", 2), ([], " " * 65537, 2)):
            result = subprocess.run([sys.executable, str(REPO / "systemd/bopos-set-wifi"), *args],
                                    input=payload, capture_output=True, text=True, env=environment)
            self.assertEqual(result.returncode, code)
            self.assertEqual(json.loads(result.stdout), {"managed": False})
            self.assertEqual(result.stderr, "")


class FleetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        args = SimpleNamespace(data_dir=self.temp.name, devices_file=None, listen_port=0,
                               send_port=0, osc_target="255.255.255.255", public_url="http://localhost",
                               assets_dir=str(REPO / "assets"), patches_dir=str(REPO / "patches"))
        self.dashboard = Dashboard(args)
        self.events = []
        self.dashboard.osc.broadcast = lambda kind, data=None: self.events.append((kind, copy.deepcopy(data)))
        self.dashboard.osc._sender_for = lambda destination: SimpleNamespace(sendto=lambda packet, target: self.frames.append(packet))
        self.frames = []
        device = self.dashboard.state._runtime_device("node-a")
        device.update(online=True, ip="192.0.2.1", report={"wifi": observed(False)})
        self.dashboard.state.devices["node-a"] = device
        self.messages = []
        async def send_json(message): self.messages.append(message)
        self.ws = SimpleNamespace(send_json=send_json)
        # WebSocket objects are hashable (SimpleNamespace isn't).
        self.ws = type("WS", (), {"send_json": staticmethod(send_json)})()

    async def asyncTearDown(self):
        self.dashboard.osc.close()
        await self.dashboard.state.close()

    async def test_confirmation_redaction_files_and_changed_keep(self):
        dash = self.dashboard
        secret = "wifi-" + uuid.uuid4().hex
        await dash.handle_ws({"type": "set_wifi_networks", "data": {"config": request(secret)}}, self.ws)
        self.assertEqual(self.messages[-1], {"type": "wifi_confirm", "data": {"passphrases": 1}})
        self.assertEqual(self.frames, [])
        self.assertFalse(Path(dash.wifi_secrets.path).exists())
        await dash.handle_ws({"type": "send_wifi_networks", "data": {"confirmed": True}}, self.ws)
        sent = json.loads(OscMessage(self.frames[-1]).params[2])
        self.assertEqual(sent, request(secret))
        self.assertEqual(Path(dash.wifi_secrets.path).stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(Path(dash.wifi_secrets.path).read_text())["secrets"], {"show": secret})
        dash.state.save_venue("test")
        public = await dash.public_state()
        self.assertEqual(public["devices"]["node-a"]["wifi_sync"], "sending…")
        self.assertNotIn(secret, json.dumps(public) + json.dumps(self.messages) + json.dumps(self.events))
        for file in Path(self.temp.name).rglob("*"):
            if file.is_file() and file != Path(dash.wifi_secrets.path):
                self.assertNotIn(secret, file.read_text())
        dirty = observed(); dirty["networks"][0]["psk"] = secret
        dash.osc.handle("/os/wifi-config", ["node-a", "ok", "applied", json.dumps(dirty)], "192.0.2.1")
        self.assertNotIn(secret, json.dumps(self.events))
        self.assertEqual((await dash.public_device(dash.state.devices["node-a"]))["wifi_sync"], "in sync")
        self.messages.clear(); self.frames.clear()
        await dash.handle_ws({"type": "set_wifi_networks", "data": {"config": request()}}, self.ws)
        self.assertNotIn("wifi_confirm", [message["type"] for message in self.messages])
        self.assertIsNone(json.loads(OscMessage(self.frames[-1]).params[2])["networks"][0]["psk"])
        dash.osc.handle("/os/wifi-config", ["node-a", "ok", "applied", json.dumps(observed())], "192.0.2.1")
        await dash.handle_ws({"type": "set_wifi_networks", "data": {"config": request(secret + "2")}}, self.ws)
        self.assertEqual(self.messages[-1]["type"], "wifi_confirm")
        reloaded = InstallationState(self.temp.name)
        self.assertEqual(reloaded.data["wifi"], wifi.metadata(request()))
        await reloaded.close()

    async def test_chips_timeout_and_public_report_redaction(self):
        dash = self.dashboard; device = dash.state.devices["node-a"]
        dash.state.data["wifi"] = wifi.metadata(request())
        self.assertEqual(dash.wifi_sync(device), "needs passphrase")
        device["report"]["wifi"] = {"managed": False}
        self.assertEqual(dash.wifi_sync(device), "no Wi-Fi")
        device["report"]["wifi"] = observed()
        self.assertEqual(dash.wifi_sync(device), "in sync")
        device["report"]["wifi"]["country"] = "AU"
        self.assertEqual(dash.wifi_sync(device), "differs")
        dash.osc.set_wifi_config("node-a", request())
        dash.osc._expire_wifi_apply("node-a")
        self.assertEqual(dash.wifi_sync(device), "error")
        secret = "wifi-" + uuid.uuid4().hex
        report = {"uid": "node-a", "wifi": dict(observed(), psk=secret)}
        dash.osc.handle("/os/report", [json.dumps(report)], "192.0.2.1")
        self.assertNotIn(secret, json.dumps(self.events) + json.dumps(await dash.public_state()))
        dash.state.save_venue("venue")
        dash.state.data["wifi"] = {"country": "AU", "networks": []}
        dash.state.load_venue("venue")
        self.assertEqual(dash.state.data["wifi"], {"country": "AU", "networks": []})

    async def test_changed_secret_survives_restart_until_acknowledged(self):
        dash = self.dashboard
        device = dash.state.devices["node-a"]
        device.update(online=False, report={"wifi": observed()})
        secret = "wifi-" + uuid.uuid4().hex
        # Offline changes save without transmitting; later sends still warn.
        await dash.handle_ws({"type": "set_wifi_networks", "data": {"config": request(secret)}}, self.ws)
        from wifi_secrets import WifiSecrets
        reloaded = WifiSecrets(self.temp.name)
        self.assertEqual(reloaded.pending, {"node-a": {"show"}})
        dash.wifi_secrets = reloaded
        device["online"] = True
        self.assertEqual(dash.wifi_sync(device), "differs")
        await dash.handle_ws({"type": "set_wifi_networks", "data": {"config": request()}}, self.ws)
        self.assertEqual(self.messages[-1]["type"], "wifi_confirm")
        self.assertFalse(self.frames)
        await dash.handle_ws({"type": "send_wifi_networks", "data": {"confirmed": True}}, self.ws)
        self.assertEqual(json.loads(OscMessage(self.frames[-1]).params[2]), request(secret))
        dash.osc.handle("/os/wifi-config", ["node-a", "ok", "applied", json.dumps(observed())], "192.0.2.1")
        self.assertEqual(WifiSecrets(self.temp.name).pending, {})

    async def test_confirmation_cannot_be_bypassed_and_same_network_is_counted_once(self):
        dash = self.dashboard
        await dash.handle_ws({"type": "send_wifi_networks", "data": {"confirmed": True}}, self.ws)
        self.assertFalse(self.frames)
        secret = "wifi-" + uuid.uuid4().hex
        await dash.handle_ws({"type": "set_wifi_networks", "data": {"config": request(secret)}}, self.ws)
        device = copy.deepcopy(dash.state.devices["node-a"])
        device["uid"] = "node-b"
        dash.state.devices["node-b"] = device
        await dash.handle_ws({"type": "send_wifi_networks", "data": {"confirmed": True}}, self.ws)
        confirmations = [message for message in self.messages if message["type"] == "wifi_confirm"]
        self.assertEqual(confirmations, [{"type": "wifi_confirm", "data": {"passphrases": 1}}])
        self.assertEqual(len(self.frames), 2)

    async def test_invalid_secret_file_is_preserved_and_blocks_send(self):
        dash = self.dashboard
        from wifi_secrets import WifiSecrets
        path = Path(dash.wifi_secrets.path)
        path.parent.mkdir()
        path.write_text("broken")
        dash.wifi_secrets = WifiSecrets(self.temp.name)
        secret = "wifi-" + uuid.uuid4().hex
        await dash.handle_ws({"type": "set_wifi_networks", "data": {"config": request(secret)}}, self.ws)
        await dash.handle_ws({"type": "send_wifi_networks", "data": {"confirmed": True}}, self.ws)
        self.assertEqual(path.read_text(), "broken")
        self.assertFalse(self.frames)
        self.assertEqual(self.messages[-1]["type"], "error")


class SimulatorTests(unittest.TestCase):
    def test_simulated_receipts_reports_logs_and_unmanaged_adoption(self):
        fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
        fleet.args = SimpleNamespace(report_port=5550); fleet.start_monotonic = 0; fleet.tty = False
        frames = []
        fleet.sock = SimpleNamespace(sendto=lambda packet, target: frames.append(OscMessage(packet)))
        device = simfleet.Device("node-a", "sim", 0, "abc")
        secret = "wifi-" + uuid.uuid4().hex
        logs = io.StringIO()
        with contextlib.redirect_stdout(logs):
            fleet.uid_admin(device, "wifi-config", [json.dumps(request(secret))], ("127.0.0.1", 5550))
            self.assertEqual(frames[-1].params[:3], ["node-a", "ok", "applied"])
            fleet.uid_admin(device, "wifi-config", [json.dumps(request())], ("127.0.0.1", 5550))
            self.assertEqual(frames[-1].params[:3], ["node-a", "ok", "applied"])
            adopt = request(); adopt["networks"][0]["ssid"] = "imager-net"
            fleet.uid_admin(device, "wifi-config", [json.dumps(adopt)], ("127.0.0.1", 5550))
            self.assertEqual(device.wifi["unmanaged"], [])
            fleet.send_report(device, ("127.0.0.1", 5550))
        self.assertNotIn(secret, logs.getvalue() + repr(vars(device)) + repr([frame.params for frame in frames]))
        fleet.uid_admin(device, "wifi-config", [json.dumps(request())], ("127.0.0.1", 5550))
        self.assertEqual(frames[-1].params[1:3], ["err", "invalid"])
        wired = simfleet.Device("node-b", "wired", 1, "abc", wired=True)
        fleet.uid_admin(wired, "wifi-config", [json.dumps(request(secret))], ("127.0.0.1", 5550))
        self.assertEqual(frames[-1].params[1:3], ["err", "unavailable"])


if __name__ == "__main__":
    unittest.main()
