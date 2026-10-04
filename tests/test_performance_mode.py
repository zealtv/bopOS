"""Remembered mode, node refusals, host convergence and RAM log boundaries."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in ("python", "dashboard", "tools"):
    sys.path.insert(0, str(ROOT / directory))

import performance_mode as mode
from nodelog import NodeLog
from logpipe import PerformanceSink
from test_log_config import bopos, ReplySocket
from store import Store
from server import Dashboard
from state import InstallationState
from osc_bridge import OSCBridge
import simfleet
from pythonosc.osc_message import OscMessage


def node(root, active=False):
    return SimpleNamespace(uid="node-a", id=0, version="test", update_model="persistent",
        config={}, performance=active, performance_path=str(Path(root)/"state/performance.json"),
        store=Store(str(Path(root)/"store")), groups=(), device_enabled=True,
        mute_all=False, reports={"sensor": (1,)}, reports_lock=threading.Lock())


def packet(address, args):
    message = bopos.OSCMessage(address)
    for arg in args:
        message.append(arg)
    return message.getBinary()


class RememberedModeTests(unittest.TestCase):
    def test_only_changes_write_and_both_modes_survive_reload(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"performance.json"
            self.assertFalse(mode.load(path))
            self.assertFalse(mode.save(path, False))
            self.assertFalse(path.exists())
            self.assertTrue(mode.save(path, True))
            self.assertTrue(mode.load(path))
            with mock.patch.object(mode.os, "replace") as replace:
                self.assertFalse(mode.save(path, True))
                replace.assert_not_called()
            self.assertTrue(mode.save(path, False))
            self.assertFalse(mode.load(path))

    def test_node_boot_remembers_even_with_ephemeral_engine_store(self):
        with tempfile.TemporaryDirectory() as root:
            mode.save(Path(root)/"state/performance.json", True)
            with mock.patch.object(bopos, "BOPOS_DIR", root), \
                 mock.patch.object(bopos, "read_node_config", return_value={"UPDATE_MODEL": "ephemeral"}), \
                 mock.patch.object(bopos, "resolve_uid", return_value="node-a"), \
                 mock.patch.object(bopos, "resolve_id", return_value=-1), \
                 mock.patch.object(bopos, "resolve_version", return_value="test"):
                restarted = bopos.NodeState()
            self.assertTrue(restarted.performance)
            self.assertFalse(restarted.store.persistent)

    def test_gate_locks_every_development_operation_and_keeps_exit_and_audio(self):
        for operation in mode.LOCKED:
            self.assertFalse(mode.allows(True, operation), operation)
            self.assertTrue(mode.allows(False, operation), operation)
        for operation in ("performance", "report", "mute", "master", "enabled", "restart-engine"):
            self.assertTrue(mode.allows(True, operation), operation)


class NodeModeTests(unittest.TestCase):
    def test_toggle_is_never_locked_and_report_confirms_persistence(self):
        with tempfile.TemporaryDirectory() as root:
            state, reply = node(root), ReplySocket()
            with mock.patch.object(bopos, "report_reply", return_value=True), \
                 mock.patch.object(bopos.nodelog, "close"):
                for active in (1, 1, 0, 1, 0):
                    self.assertTrue(bopos.handle_lan_datagram(packet("/all/os/performance", [active]),
                        ("127.0.0.1", 9999), reply, state))
                    self.assertEqual(state.performance, bool(active))
                    self.assertEqual(mode.load(state.performance_path), bool(active))
                for bad in ("1", 2, -1, .5):
                    self.assertFalse(bopos.set_performance(bad, reply, "127.0.0.1", state))

    def test_failed_persistence_reports_old_mode_and_can_be_retried(self):
        with tempfile.TemporaryDirectory() as root:
            state = node(root)
            with mock.patch.object(bopos.performance_mode, "save", side_effect=OSError("fixture")), \
                 mock.patch.object(bopos.nodelog, "close"), \
                 mock.patch.object(bopos, "report_reply", return_value=True) as report:
                bopos.set_performance(1, ReplySocket(), "127.0.0.1", state)
            self.assertFalse(state.performance)
            report.assert_called_once()

    def test_wire_refusals_do_not_run_patch_wifi_probe_or_io(self):
        with tempfile.TemporaryDirectory() as root:
            state, reply = node(root, True), ReplySocket()
            with mock.patch.object(bopos, "queue_fetch") as fetch, \
                 mock.patch.object(bopos.threading, "Thread") as thread, \
                 mock.patch.object(bopos.wifi_config, "helper_status", return_value={"managed": False}):
                for address, args in (
                    ("/all/os/patch", ["next"]), ("/0/os/droppatch", ["old"]),
                    ("/0/os/fetch", ["http://fixture/manifest", "patch:next"]),
                    ("/all/os/probe", ["sensor"]),
                    ("/all/os/to", [state.uid, "wifi-config", "{}"]),
                    ("/all/os/to", [state.uid, "io-write", json.dumps(
                        {"name":"adc", "command":"threshold", "args":[1]})]),
                    ("/all/os/to", [state.uid, "io-stream", 1]),
                ):
                    self.assertTrue(bopos.handle_lan_datagram(packet(address,args),
                        ("127.0.0.1",9999),reply,state), address)
                fetch.assert_not_called(); thread.assert_not_called()
            frames = [decoded for decoded, _target in reply.calls]
            self.assertFalse(any(frame[0]=="/os/probe" for frame in frames))
            self.assertIn("/os/fetched", [frame[0] for frame in frames])
            self.assertIn("/os/wifi-config", [frame[0] for frame in frames])
            io_reply = next(frame for frame in frames if frame[0] == "/os/io-write")
            self.assertEqual(io_reply[2:4], [state.uid, "err"])
            self.assertEqual(json.loads(io_reply[4]),
                {"name":"adc", "command":"threshold", "error":"performance"})
            self.assertTrue(all("performance" in frame for frame in frames if frame[0]=="/os/rev"))

    def test_queued_patch_work_rechecks_gate_but_assets_can_fetch(self):
        with tempfile.TemporaryDirectory() as root:
            state = node(root, True)
            with mock.patch.object(bopos.fetcher, "fetch", return_value=(True,"fixture")) as fetch:
                self.assertEqual(bopos._execute_fetch("uri","patch:next",state),(False,"performance"))
                fetch.assert_not_called()
                self.assertTrue(bopos._execute_fetch("uri","sounds",state)[0])
            with mock.patch.dict(bopos.PROVISION_VERBS, {"patch": mock.Mock()}):
                callback = bopos.PROVISION_VERBS["patch"]
                bopos.run_admin_verb(callback,["next"],state,ReplySocket(),"127.0.0.1")
                callback.assert_not_called()

    def test_report_carries_mode_and_effective_ram(self):
        with tempfile.TemporaryDirectory() as root:
            state, reply = node(root, True), ReplySocket()
            with mock.patch.object(bopos, "active_patch_path", return_value=None), \
                 mock.patch.object(bopos, "audio_report", return_value={}), \
                 mock.patch.object(bopos.wifi_config, "helper_status", return_value={"managed":False}):
                bopos.report_reply(reply,"127.0.0.1",state)
            report=json.loads(reply.calls[-1][0][2])
            self.assertTrue(report["performance"])
            self.assertEqual(report["log"]["effective"],"ram")
            self.assertEqual(report["log"]["destination"],"internal")


class RamLoggingTests(unittest.TestCase):
    def test_ram_sink_failure_keeps_the_service_pipe_alive(self):
        with tempfile.TemporaryDirectory() as root:
            sink=PerformanceSink(str(Path(root)/"io.log"),root)
            mode.save(sink.mode_path,True)
            with mock.patch.object(mode,"ram_directory",return_value="/unavailable/tmpfs"), \
                 mock.patch("logpipe.os.makedirs",side_effect=OSError("fixture full")):
                sink.write("still alive\n")
                sink.write("still in RAM\n")
            self.assertEqual(list(sink.memory),["still alive\n","still in RAM\n"])
            self.assertFalse(Path(sink.path).exists())

    def test_mode_transition_excludes_concurrent_disk_appends(self):
        with tempfile.TemporaryDirectory() as root:
            disk=Path(root)/"disk"
            active=[False]
            log=NodeLog(lambda:None if active[0] else disk)
            log.append("sensor",["before"])
            entered=threading.Event(); attempted=threading.Event(); done=threading.Event()
            def update():
                entered.set()
                self.assertTrue(attempted.wait(2))
                self.assertFalse(done.is_set())
                active[0]=True
            def append():
                self.assertTrue(entered.wait(2)); attempted.set()
                log.append("sensor",["after"]); done.set()
            worker=threading.Thread(target=append)
            worker.start(); log.change_destination(update); worker.join(2)
            self.assertTrue(done.is_set())
            self.assertIn("after",log.memory[-1])
            self.assertFalse(any("after" in path.read_text() for path in disk.glob("*.log")))

    def test_stdout_sink_switches_without_touching_disk_in_performance(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"run/io.log"
            sink = PerformanceSink(str(path),root)
            sink.write("development\n")
            before=path.read_bytes()
            mode.save(sink.mode_path, True)
            with mock.patch.object(mode,"ram_directory",return_value=None):
                sink.write("performance\n")
                self.assertIn("performance\n",sink.memory)
                self.assertEqual(path.read_bytes(),before)
                fresh=PerformanceSink(str(path),root)
                fresh.write("boot in Performance\n"); fresh.close()
                self.assertEqual(path.read_bytes(),before)
                self.assertFalse(Path(str(path)+".prev").exists())
            mode.save(sink.mode_path,False)
            sink.write("development again\n"); sink.close()
            self.assertIn("development again",path.read_text())
            self.assertNotIn("performance",path.read_text())

    def test_both_log_facilities_use_ram_destination_and_never_copy_back(self):
        # A scratch directory stands in for tmpfs here; its filesystem is not
        # a claim about a Pi. Verify actual routing and bytes, not source text.
        with tempfile.TemporaryDirectory() as root:
            ram=Path(root)/"ram"; disk=Path(root)/"disk"
            state=node(root)
            with mock.patch.object(bopos.performance_mode,"ram_directory",return_value=str(ram)), \
                 mock.patch.object(bopos.log_config,"INTERNAL_DIR",str(disk)):
                log=NodeLog(lambda:bopos.node_log_directory(state))
                log.append("sensor",["development"]); log.close()
                before={path:path.read_bytes() for path in disk.glob("*.log")}
                state.performance=True
                log.append("sensor",["performance"]); log.close()
                self.assertTrue(any("performance" in path.read_text() for path in ram.glob("*.log")))
                self.assertEqual(before,{path:path.read_bytes() for path in disk.glob("*.log")})
                state.performance=False
                log.append("sensor",["resumed"]); log.close()
                self.assertFalse(any("performance" in path.read_text() for path in disk.glob("*.log")))
            memory=NodeLog(lambda:None)
            memory.append("sensor",["in RAM"])
            self.assertIn("in RAM",memory.memory[-1])


class HostModeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.args=SimpleNamespace(data_dir=self.tmp.name,devices_file=None,listen_port=0,
            send_port=0,osc_target="127.0.0.1",assets_dir=self.tmp.name+"/assets",
            patches_dir=self.tmp.name+"/patches")
        self.dash=Dashboard(self.args)
        self.dash.broadcast=mock.AsyncMock()
        self.dash.osc.set_performance=mock.Mock()
        self.ws=SimpleNamespace(send_json=mock.AsyncMock())

    async def test_host_restart_project_change_and_exit(self):
        await self.dash.handle_ws({"type":"set_performance","data":{"active":True}},self.ws)
        restarted=Dashboard(self.args)
        self.assertTrue(restarted.state.performance)
        self.assertTrue((await restarted.public_state())["performance"])
        self.dash.state.create_project("another")
        await self.dash.open_project("another")
        self.assertTrue(self.dash.state.performance)
        await self.dash.handle_ws({"type":"set_performance","data":{"active":False}},self.ws)
        self.assertFalse(Dashboard(self.args).state.performance)
        self.dash.osc.set_performance.assert_has_calls([mock.call(True),mock.call(False)])

    async def test_forged_stale_tab_development_messages_are_refused(self):
        self.dash.state.performance=True
        self.dash.osc.send=mock.Mock(); self.dash.osc.fetch=mock.Mock()
        self.dash.osc.probe=mock.Mock(); self.dash.osc.uid_command=mock.Mock()
        commands={
            "monitor_probe":{"uid":"node-a","name":"sensor"},
            "monitor_send":{"address":"/all/os/master","args":[.5]},
            "set_wifi_networks":{"config":{}}, "send_wifi_networks":{"confirmed":True},
            "set_fleet_patch":{"patch":"next","confirmed":True},
            "retry_fleet_patch":{"uid":"node-a"}, "save_patch_manifest":{"patch":"next"},
            "create_patch":{"name":"next"}, "new_patch_version":{"name":"next"},
            "set_edit":{"active":True,"patch":"next","confirmed":True}, "relaunch_edit":{},
            "send_distribution":{"kind":"patch","name":"next"},
            "drop_distribution":{"kind":"patch","name":"next"},
        }
        for kind,data in commands.items():
            await self.dash.handle_ws({"type":kind,"data":data},self.ws)
            self.assertEqual(self.ws.send_json.call_args.args[0]["type"],"error",kind)
        for method in (self.dash.osc.send,self.dash.osc.fetch,self.dash.osc.probe,self.dash.osc.uid_command):
            method.assert_not_called()
        self.assertFalse((Path(self.args.patches_dir)/"next").exists())

    async def test_entering_performance_stops_editor(self):
        self.dash.state.data["supervisor"]={"mode":"edit"}
        self.dash.stop_supervisor=mock.AsyncMock()
        await self.dash.handle_ws({"type":"set_performance","data":{"active":True}},self.ws)
        self.dash.stop_supervisor.assert_awaited_once()

    async def test_new_disagreeing_and_missing_mode_reports_converge_with_bounded_retry(self):
        state=self.dash.state; state.performance=True
        bridge=OSCBridge(state,lambda *_:None,0,0,"127.0.0.1")
        bridge.send_for_uid=mock.Mock()
        device={"uid":"node-a","online":True,"report":{"performance":False}}
        bridge.converge_performance(device)
        bridge.converge_performance(device)
        bridge.send_for_uid.assert_called_once_with("node-a","/all/os/performance",[1])
        bridge._performance_replayed["node-a"]-=4
        bridge.converge_performance(device)
        self.assertEqual(bridge.send_for_uid.call_count,2)
        device["report"]["performance"]=True
        bridge.converge_performance(device)
        self.assertNotIn("node-a",bridge._performance_replayed)
        device["report"]={}
        bridge.converge_performance(device)
        self.assertEqual(bridge.send_for_uid.call_count,3)


class SimulatedModeTests(unittest.TestCase):
    def test_mode_persists_for_ephemeral_nodes_and_reports_ram(self):
        with tempfile.TemporaryDirectory() as root:
            device=simfleet.Device("node-a","sim",0,"test",ephemeral=True)
            mode.save(device.performance_file(root),True)
            device.load_assignment(root)
            self.assertTrue(device.performance)
            self.assertEqual(simfleet.device_log_state(device)["effective"],"ram")
            fleet=simfleet.SimFleet.__new__(simfleet.SimFleet)
            fleet.args=SimpleNamespace(report_port=5550); fleet.start_monotonic=0
            frames=[]
            fleet.sock=SimpleNamespace(sendto=lambda packet,_:frames.append(OscMessage(packet)))
            fleet.send_report(device,("127.0.0.1",5550))
            self.assertTrue(json.loads(frames[-1].params[0])["performance"])
            fleet.send_rev=mock.Mock()
            fleet.admin_verb(device,"patch",["next"],("127.0.0.1",5550))
            fleet.send_rev.assert_called_once_with(device,("127.0.0.1",5550),"err","performance")
            fleet.uid_admin(device,"wifi-config",["{}"],("127.0.0.1",5550))
            self.assertEqual(frames[-1].params[1:3],["err","performance"])


if __name__=="__main__":
    unittest.main()
