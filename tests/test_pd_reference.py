"""Guard the live help patch against the engine surface drifting past it.

Bob's 64/2 stitch removes the explicit skip when pd/bopos~-help.pd lands.
Read source text/AST only: importing bopos.py binds sockets and starts a node.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "pd/bopos~-help.pd"


def pd_records(source):
    for line in source.splitlines():
        # Text comments cannot satisfy a working reference example.
        if line.startswith(("#X obj ", "#X msg ")):
            yield re.split(r"\s+|(?<!\\)[,;]", line.rstrip(";"))[4:]


def exposed_buses(source):
    result = set()
    for atoms in pd_records(source):
        if len(atoms) >= 2 and atoms[0] in {
            "s", "r", "send", "receive", "s~", "r~", "send~", "receive~",
            "throw~", "catch~",
        }:
            bus = atoms[1]
            # $0/#0 sends are abstraction-private, not part of the API.
            if not any(local in bus for local in ("$0", "#0")):
                result.add(bus)
    return result


def engine_verbs(source):
    tree = ast.parse(source)
    admin = None
    requests = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "ENGINE_ADMIN_VERBS"
            for target in node.targets
        ):
            if not isinstance(node.value, ast.Dict):
                raise AssertionError("Update reference guard for changed admin registry")
            admin = {ast.literal_eval(key) for key in node.value.keys}
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "server" and node.func.attr == "addMsgHandler"):
            address = ast.literal_eval(node.args[0])
            requests.add(address.lstrip("/"))
    if not admin or not {"admin", "log"}.issubset(requests):
        raise AssertionError("Engine request registry missing; update reference guard")
    return admin | requests


class ReferenceExtractionTests(unittest.TestCase):
    def test_new_global_bus_is_discovered_and_private_bus_is_excluded(self):
        source = """#X obj 1 2 r bopos-new;
#X obj 1 2 send to-bopos-new;
#X obj 1 2 s~ \\$0-local;
#X obj 1 2 r~ #0-local;
#X obj 1 2 catch~ bopos-0;
#X text 1 2 r pretend;
"""
        self.assertEqual(exposed_buses(source), {"bopos-new", "to-bopos-new", "bopos-0"})

    def test_new_admin_and_log_requests_are_discovered(self):
        source = """ENGINE_ADMIN_VERBS = {'new-action': callback}
server.addMsgHandler('/admin', admin_callback)
server.addMsgHandler('/log', log_callback)
server.addMsgHandler('/new-log-action', log_callback)
"""
        self.assertEqual(engine_verbs(source), {"new-action", "admin", "log", "new-log-action"})

    def test_reference_comments_do_not_count_as_examples(self):
        self.assertEqual(list(pd_records("#X text 1 2 reboot;")), [])

    def test_live_sources_have_extractable_surfaces(self):
        self.assertTrue(exposed_buses((ROOT / "pd/bopos~.pd").read_text()))
        self.assertIn("log", engine_verbs((ROOT / "python/bopos.py").read_text()))


@unittest.skip("64/2-live-pd-reference is Bob's pending Pd edit; unskip when pd/bopos~-help.pd lands")
class LiveReferenceCoverageTests(unittest.TestCase):
    def test_every_exposed_bus_has_a_reference_object(self):
        required = exposed_buses((ROOT / "pd/bopos~.pd").read_text())
        missing = required - exposed_buses(REFERENCE.read_text())
        self.assertFalse(missing, "Add help examples for buses: " + ", ".join(sorted(missing)))

    def test_every_engine_admin_and_log_request_has_a_reference_example(self):
        required = engine_verbs((ROOT / "python/bopos.py").read_text())
        atoms = {atom for record in pd_records(REFERENCE.read_text()) for atom in record}
        missing = required - atoms
        self.assertFalse(missing, "Add help examples for verbs: " + ", ".join(sorted(missing)))


if __name__ == "__main__":
    unittest.main()
