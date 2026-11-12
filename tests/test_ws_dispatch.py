"""Frontend verb reachability and the WebSocket dispatch concurrency boundary."""
import ast
import asyncio
import inspect
from pathlib import Path
import re
import sys
import textwrap
from types import SimpleNamespace
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
from server import Dashboard
from ws_handlers import WS_HANDLERS, WSHandlers


def frontend_types():
    """Read real send sites, including the two explicitly forwarded paths.

    Unknown dynamic arguments fail the audit instead of silently disappearing.
    Show transport verbs come from buttons, not sendTransport's dead branches.
    """
    kinds = set()
    for path in (ROOT / "dashboard/static/js").glob("*.js"):
        source = path.read_text()
        pattern = r"\b(?:ws|this)\.send\(([^,\n]+),"
        if path.name == "device-io.js":
            pattern = r"\bsend\(([^,\n]+),"
        for match in re.finditer(pattern, source):
            argument = match[1].strip()
            literal = re.fullmatch(r"['\"]([a-z_]+)['\"]", argument)
            if literal:
                kinds.add(literal[1])
            elif "?" in argument:
                choices = re.findall(r"[?:]\s*['\"]([a-z_]+)['\"]", argument)
                if len(choices) != 2:
                    raise AssertionError(f"Unresolved send: {path.name}: {argument}")
                kinds.update(choices)
            elif (path.name, argument) not in {("dashboard-devices.js", "kind"), ("show.js", "type")}:
                raise AssertionError(f"Unresolved send: {path.name}: {argument}")
        if path.name == "show.js":
            kinds.update(re.findall(r"iconButton\(['\"]([a-z_]+)['\"]", source))
            kinds.update(re.findall(r"data-show-action=['\"]([a-z_]+)['\"]", source))
            # The global Play button chooses a transport action from state.
            action = re.search(r"const playAction\s*=([^;]+);", source)
            if action:
                kinds.update(re.findall(r"[?:]\s*['\"]([a-z_]+)['\"]", action[1]))
    return kinds


class ReachabilityTests(unittest.TestCase):
    def test_every_frontend_verb_and_only_frontend_verbs_have_handlers(self):
        self.assertSetEqual(frontend_types(), set(WS_HANDLERS))

    def test_registered_methods_exist_and_no_handler_is_unregistered_or_long(self):
        methods = {rule.method for rule in WS_HANDLERS.values()}
        self.assertSetEqual(methods, {name for name in vars(WSHandlers) if name.startswith("_ws_")})
        for name in methods:
            with self.subTest(handler=name):
                handler = getattr(Dashboard, name)
                self.assertTrue(inspect.iscoroutinefunction(handler))
                self.assertLessEqual(len(inspect.getsourcelines(handler)[0]), 60)
        for rule in WS_HANDLERS.values():
            self.assertIn(rule.supervisor, ("", "dispatch", "handler"))
            if rule.supervisor == "handler":
                tree = ast.parse(textwrap.dedent(inspect.getsource(getattr(Dashboard, rule.method))))
                self.assertTrue(any(isinstance(node, ast.AsyncWith)
                    and any(ast.unparse(item.context_expr) == "self.supervisor_lock"
                            for item in node.items) for node in ast.walk(tree)))


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.dash = object.__new__(Dashboard)
        self.dash.state = SimpleNamespace(data={"supervisor": {"mode": "off"}}, performance=False)
        self.dash.manifest_lock = asyncio.Lock()
        self.dash.supervisor_lock = asyncio.Lock()
        self.dash.monitor_transport = SimpleNamespace(clients=set())
        self.dash.ws_error = mock.AsyncMock()
        self.socket = object()

    async def send(self, message_type, **data):
        await self.dash.handle_ws({"type": message_type, "data": data}, self.socket)

    async def test_every_type_dispatches_to_its_registered_method(self):
        for kind, rule in WS_HANDLERS.items():
            with self.subTest(kind=kind):
                handler = mock.AsyncMock()
                with mock.patch.object(self.dash, rule.method, handler):
                    await self.send(kind)
                handler.assert_awaited_once_with(kind, {}, self.socket)
                self.dash.ws_error.assert_not_awaited()

    async def test_manifest_then_supervisor_locks_and_release_after_failure(self):
        order = []
        class RecordedLock(asyncio.Lock):
            async def acquire(lock):
                order.append(lock.label)
                return await super().acquire()
        self.dash.manifest_lock = RecordedLock()
        self.dash.manifest_lock.label = "manifest"
        self.dash.supervisor_lock = RecordedLock()
        self.dash.supervisor_lock.label = "supervisor"
        async def handler(*args):
            self.assertTrue(self.dash.manifest_lock.locked())
            self.assertTrue(self.dash.supervisor_lock.locked())
            raise RuntimeError("fixture")
        self.dash._ws_save_patch_manifest = handler
        with self.assertRaises(RuntimeError):
            await self.send("save_patch_manifest")
        self.assertEqual(order, ["manifest", "supervisor"])
        self.assertFalse(self.dash.manifest_lock.locked())
        self.assertFalse(self.dash.supervisor_lock.locked())

    async def test_patch_edit_editor_exception_and_live_only_project_guard(self):
        self.dash.state.data["supervisor"]["mode"] = "edit"
        self.dash._ws_set_live_automation = mock.AsyncMock()
        await self.send("set_live_automation", scope="all")
        self.dash._ws_set_live_automation.assert_not_awaited()
        self.dash.ws_error.assert_awaited_with(self.socket,
            "That execution control is unavailable during Patch Edit.")
        await self.send("set_live_automation", scope="editor")
        self.dash._ws_set_live_automation.assert_awaited_once()
        self.dash._ws_create_project = mock.AsyncMock()
        await self.send("open_project")
        self.dash._ws_create_project.assert_not_awaited()
        self.dash.state.data["supervisor"]["mode"] = "simulate"
        await self.send("set_live_automation", scope="editor")
        self.dash.ws_error.assert_awaited_with(self.socket, "The patch editor is not running.")
        await self.send("open_project")
        self.dash.ws_error.assert_awaited_with(self.socket,
            "That execution control is unavailable during Simulation.")

    async def test_waiting_mutation_rechecks_mode_and_performance(self):
        for kind, data, change, error in (
            ("set_live_param", {}, "edit", "That execution control is unavailable during Patch Edit."),
            ("set_live_automation", {"scope": "editor"}, "off", "The patch editor is not running."),
            ("monitor_send", {}, "performance", "Performance"),
        ):
            with self.subTest(kind=kind):
                self.dash.state.performance = False
                self.dash.state.data["supervisor"]["mode"] = "edit" if data else "off"
                rule = WS_HANDLERS[kind]
                handler = mock.AsyncMock()
                with mock.patch.object(self.dash, rule.method, handler):
                    await self.dash.supervisor_lock.acquire()
                    task = asyncio.create_task(self.send(kind, **data))
                    try:
                        await asyncio.sleep(0)
                        self.assertFalse(task.done())
                        if change == "performance":
                            self.dash.state.performance = True
                        else:
                            self.dash.state.data["supervisor"]["mode"] = change
                    finally:
                        self.dash.supervisor_lock.release()
                    await asyncio.wait_for(task, 1)
                handler.assert_not_awaited()
                self.dash.ws_error.assert_awaited_with(self.socket, error)

    async def test_conditional_performance_guards(self):
        self.dash.state.performance = True
        for kind, allowed, blocked in (
            ("set_edit", {"active": False}, {"active": True}),
            ("send_distribution", {"kind": "asset"}, {"kind": "patch"}),
            ("drop_distribution", {"kind": "asset"}, {"kind": "patch"}),
            ("action", {"verb": "reboot"}, {"verb": "droppatch"}),
        ):
            with self.subTest(kind=kind):
                handler = mock.AsyncMock()
                with mock.patch.object(self.dash, WS_HANDLERS[kind].method, handler):
                    await self.send(kind, **allowed)
                    handler.assert_awaited_once()
                    handler.reset_mock()
                    await self.send(kind, **blocked)
                    handler.assert_not_awaited()
                self.dash.ws_error.assert_awaited_with(self.socket, "Performance")

    async def test_capture_selection_bypasses_execution_mode_guards(self):
        client = mock.Mock()
        self.dash.monitor_transport.clients.add(client)
        data = {"scope": "editor", "generation": 2}
        await self.dash.handle_ws({"type": "capture_selection", "data": data}, client)
        client.replace.assert_called_once_with(data)
        self.dash.ws_error.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
