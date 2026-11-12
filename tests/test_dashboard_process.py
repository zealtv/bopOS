"""Keep real dashboard test processes off the operator's default ports."""
import ast
from pathlib import Path
import unittest
from unittest import mock

from dashboard_process import LISTENER_DEFAULTS, launch_dashboard


def unisolated_launches(source):
    """Find process launches, including argv stored in a local variable."""
    tree = ast.parse(source)
    assignments = {node.targets[0].id: node.value for node in ast.walk(tree)
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name)}

    def strings(node, seen=()):
        if isinstance(node, ast.Name) and node.id in assignments and node.id not in seen:
            return strings(assignments[node.id], seen + (node.id,))
        return " ".join(str(child.value) for child in ast.walk(node)
                        if isinstance(child, ast.Constant) and isinstance(child.value, str))

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = ast.unparse(node.func).split(".")[-1]
        if name not in {"Popen", "run", "call", "check_call", "check_output",
                        "create_subprocess_exec", "create_subprocess_shell"}:
            continue
        argv = strings(node.args[0])
        if "dashboard" in argv and "server.py" in argv:
            violations.append(node.lineno)
    return violations


class DashboardProcessTests(unittest.TestCase):
    def test_unused_listeners_get_kernel_assigned_ports(self):
        command = ["python", "dashboard/server.py", "--port", "41000",
                   "--listen-port=41001", "--send-port", "41002"]
        original = command[:]
        with mock.patch("dashboard_process.subprocess.Popen") as popen:
            result = launch_dashboard(command, cwd="fixture", stdout=mock.sentinel.log)
        self.assertIs(result, popen.return_value)
        self.assertEqual(command, original)
        popen.assert_called_once_with(original + ["--stream-port", "0", "--input-port", "0",
                                                             "--sim-io-listen-port", "0"],
                                      cwd="fixture", stdout=mock.sentinel.log)

    def test_defaults_are_rejected_before_launch_even_with_duplicates(self):
        for option, default in {**LISTENER_DEFAULTS, "--send-port": 6660}.items():
            for args in ([option, str(default)], [f"{option}={default}"],
                         [option, str(default), option, "0"]):
                with self.subTest(args=args), mock.patch("dashboard_process.subprocess.Popen") as popen:
                    with self.assertRaises(ValueError):
                        launch_dashboard(["python", "dashboard/server.py"] + args)
                    popen.assert_not_called()

    def test_managed_command_listener_needs_a_private_port(self):
        with mock.patch("dashboard_process.subprocess.Popen") as popen:
            with self.assertRaises(ValueError):
                launch_dashboard(["python", "dashboard/server.py"])
            popen.assert_not_called()

    def test_guard_finds_direct_and_indirect_launches(self):
        for argv in ('["python", "dashboard/server.py"]',
                     '["python", str(ROOT / "dashboard" / "server.py")]'):
            self.assertEqual(unisolated_launches(f"subprocess.Popen({argv})"), [1])
            self.assertEqual(unisolated_launches(f"args = {argv}\nsubprocess.Popen(args)"), [2])
            self.assertEqual(unisolated_launches(f"launch_dashboard({argv})"), [])

    def test_dashboard_launches_use_shared_helper(self):
        violations = []
        for path in Path(__file__).parent.rglob("*.py"):
            if path.name in {"dashboard_process.py", Path(__file__).name}:
                continue
            violations.extend(f"{path.name}:{line}" for line in unisolated_launches(path.read_text()))
        self.assertEqual(violations, [], "Use dashboard_process.launch_dashboard: " + ", ".join(violations))


if __name__ == "__main__":
    unittest.main()
