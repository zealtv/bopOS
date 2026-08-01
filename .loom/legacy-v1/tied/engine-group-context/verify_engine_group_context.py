#!/usr/bin/env python3
"""Focused browser-free verification for engine-group-context.

Proves (per the stitch brief):
  1. an engine starts with the node's persisted memberships as integer values;
  2. replacing membership emits exactly one complete updated context list;
  3. clearing membership emits exactly `groups -1`;
  4. rejected or failed-to-persist membership does not reach the engine;
  5. assignment/unassignment cannot leak the previous Seat's groups;
  6. audition behavior matches the node helper.

Follows the pyOSC3-monkeypatch pattern from the tied
`.loom/tied/1-protocol-node/verify_group_protocol_node.py` (fake
OSCClient/OSCServer installed *before* `import bopos`, so bopos.py's
module-level engine client becomes inspectable) and the repo-by-marker /
py_compile conventions from `.loom/tied/boundary-5-launch-context-and-topology/
verify_launch_context.py`.
"""

import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "simfleet.py").is_file():
            return candidate
    raise RuntimeError("could not locate repository root")


REPO = repo_root()
sys.path[:0] = [str(REPO), str(REPO / "python"), str(REPO / "python" / "io"),
                str(REPO / "tools")]

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
    def __init__(self):
        self.sent = []

    def connect(self, _target):
        pass

    def send(self, message):
        self.sent.append(pyOSC3.decodeOSC(message.getBinary()))


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["verify_engine_group_context.py", "unknown"]

import groups as group_protocol  # noqa: E402
import bopos  # noqa: E402
import audition  # noqa: E402
import runcontext  # noqa: E402
from store import Store  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


class CaptureSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((data, target))


class PyReply:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class Node:
    """Minimal bopos.NodeState stand-in -- mirrors the tied group-protocol
    verifier's helper, trimmed to what apply_assign/apply_unassign/
    apply_groups touch."""

    def __init__(self, root, groups=(), device_id=7):
        self.uid = "node-a"
        self.id = device_id
        self.store = Store(os.path.join(root, "store"))
        self.store.put("assignment", [device_id, "stage-left", 1.0, 2.0])
        self.store.put("groups", list(groups))
        self.elements = [[1.0, 2.0]]
        self.groups = tuple(groups)


def last_engine_message():
    return bopos.client.sent[-1] if bopos.client.sent else None


# ---------------------------------------------------------------------------
# 1 & 3. Launch delivery: runcontext resolves persisted memberships, sentinel
#         -1 for no membership.
# ---------------------------------------------------------------------------

def test_launch_context():
    with tempfile.TemporaryDirectory(prefix="bopos-groupctx-launch-") as root:
        store = Store(os.path.join(root, "state", "store"))
        store.put("groups", [5, 2])  # unsorted on disk; wire order is canonical
        check("resolve_groups reads persisted membership in sorted order",
              runcontext.resolve_groups(root) == [2, 5])

        ctx = runcontext.generate(patch="default", repo_dir=root)
        check("generate() carries the same groups list", ctx["groups"] == [2, 5])

    with tempfile.TemporaryDirectory(prefix="bopos-groupctx-launch-empty-") as root:
        check("no persisted membership resolves to sentinel [-1]",
              runcontext.resolve_groups(root) == [-1])
        ctx = runcontext.generate(patch=None, repo_dir=root)
        check("generate() sentinel [-1] with no store", ctx["groups"] == [-1])

    # CLI: BOPOS_GROUPS is present and eval-able alongside the existing lines.
    with tempfile.TemporaryDirectory(prefix="bopos-groupctx-cli-") as root:
        store = Store(os.path.join(root, "state", "store"))
        store.put("groups", [9, 1])
        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, str(REPO / "python" / "runcontext.py"), "default"],
            capture_output=True, text=True, timeout=10, cwd=root, env=env,
        )
        # runcontext.py resolves REPO_DIR from its own file location, not cwd,
        # so exercise resolve_groups()/generate() directly for the root-dir
        # case (above) and just confirm the CLI prints a BOPOS_GROUPS line at
        # all here.
        check("runcontext CLI prints a BOPOS_GROUPS line",
              any(line.startswith("BOPOS_GROUPS='") for line in
                  result.stdout.splitlines()),
              result.stdout)


# ---------------------------------------------------------------------------
# start-engine.sh / audition.py launch wiring (static + engine_command()).
# ---------------------------------------------------------------------------

def test_start_engine_sh():
    text = (REPO / "bash" / "start-engine.sh").read_text()
    for token in ('BOPOS_GROUPS="${BOPOS_GROUPS:--1}"',
                  "bopos-context groups $BOPOS_GROUPS",
                  'BOPOS_GROUPS="$BOPOS_GROUPS"'):
        check(f"start-engine.sh contains {token!r}", token in text)
    result = subprocess.run(["bash", "-n", str(REPO / "bash" / "start-engine.sh")],
                            capture_output=True, text=True)
    check("bash -n start-engine.sh succeeds", result.returncode == 0, result.stderr)


def test_audition_engine_command():
    patch_dir = str(REPO / "patches" / "demo-pd")
    loaded, error = audition.patch_manifest.load(patch_dir)
    check("demo-pd manifest loads", error is None and loaded is not None)
    if loaded is None:
        return
    args = audition.parse_args(["--devices", "1", "--engine", "pd"])
    rig = object.__new__(audition.AuditionRig)
    rig.args = args
    node = audition.VirtualNode(0, 1, "audition-0001", 36661)
    node.groups = (1, 4)  # VirtualNode.groups is canonical sorted, like state.groups
    command = rig.engine_command(node, patch_dir, loaded)
    send_string = command[command.index("-send") + 1]
    check("-send string carries the sorted membership",
          "bopos-context groups 1 4" in send_string, send_string)

    empty_node = audition.VirtualNode(0, 1, "audition-0002", 36662)
    command = rig.engine_command(empty_node, patch_dir, loaded)
    send_string = command[command.index("-send") + 1]
    check("-send string sentinels no membership",
          "bopos-context groups -1" in send_string, send_string)


# ---------------------------------------------------------------------------
# 2, 3, 4, 5. Live delivery through bopos.py.
# ---------------------------------------------------------------------------

def test_bopos_live_updates():
    original_hostname = bopos.set_hostname
    bopos.set_hostname = lambda _name: None
    try:
        with tempfile.TemporaryDirectory(prefix="bopos-groupctx-") as root:
            state = Node(root, groups=(3, 5), device_id=7)
            reply = PyReply()
            bopos.client.sent.clear()

            # 2. Replacing membership emits exactly one complete updated list.
            before = len(bopos.client.sent)
            check("apply_groups replace succeeds",
                  bopos.apply_groups(["node-a", 2, 9], reply, "10.0.0.8", state))
            check("exactly one engine message emitted on replace",
                  len(bopos.client.sent) == before + 1)
            check("engine message is the complete sorted list",
                  last_engine_message() == ["/groups", ",ii", 2, 9])
            check("state.groups updated", state.groups == (2, 9))

            # 3. Clearing membership emits exactly `groups -1`.
            before = len(bopos.client.sent)
            check("apply_groups clear (empty tail) succeeds",
                  bopos.apply_groups(["node-a"], reply, "10.0.0.8", state))
            check("exactly one engine message emitted on clear",
                  len(bopos.client.sent) == before + 1)
            check("clear sends exactly `groups -1`",
                  last_engine_message() == ["/groups", ",i", -1])
            check("state.groups cleared", state.groups == ())

            # 4a. Rejected (invalid full-state list: duplicate ids) does not
            #     reach the engine.
            bopos.apply_groups(["node-a", 4, 8], reply, "10.0.0.8", state)
            before = len(bopos.client.sent)
            before_groups = state.groups
            check("invalid duplicate ids rejected",
                  not bopos.apply_groups(["node-a", 4, 4], reply, "10.0.0.8", state))
            check("rejected membership sends nothing to the engine",
                  len(bopos.client.sent) == before)
            check("rejected membership leaves state untouched",
                  state.groups == before_groups)

            # 4b. UID mismatch does not reach the engine.
            before = len(bopos.client.sent)
            check("UID mismatch rejected",
                  not bopos.apply_groups(["other-node", 1], reply, "10.0.0.8", state))
            check("UID mismatch sends nothing to the engine",
                  len(bopos.client.sent) == before)

            # 4c. Failed-to-persist membership does not reach the engine.
            class FailingStore:
                def __init__(self, seed):
                    self.values = {"groups": list(seed), "assignment": [7, "old"]}

                def get(self, key):
                    return list(self.values.get(key, []))

                def put(self, key, values):
                    if key == "groups":
                        return False
                    self.values[key] = list(values)
                    return True

            failing_state = Node(root, groups=(1, 4), device_id=7)
            failing_state.store = FailingStore((1, 4))
            before = len(bopos.client.sent)
            check("failed persistence rejects apply_groups",
                  not bopos.apply_groups(["node-a", 6], reply, "10.0.0.8", failing_state))
            check("failed persistence sends nothing to the engine",
                  len(bopos.client.sent) == before)
            check("failed persistence retains old in-memory groups",
                  failing_state.groups == (1, 4))

            # 5a. Direct reassignment to a different Seat cannot leak the
            #     previous Seat's groups: engine sees the clear, not a stale
            #     list, and state.groups is empty under the new id.
            reassign_state = Node(root, groups=(2, 9), device_id=7)
            before = len(bopos.client.sent)
            check("apply_assign to a different Seat succeeds",
                  bopos.apply_assign(["node-a", 8, "stage-right"], reassign_state))
            check("reassignment clears membership in state",
                  reassign_state.groups == () and reassign_state.id == 8)
            sent_since = bopos.client.sent[before:]
            groups_msgs = [msg for msg in sent_since if msg[0] == "/groups"]
            check("reassignment emits exactly one /groups clear, never the old list",
                  groups_msgs == [["/groups", ",i", -1]], groups_msgs)

            # 5b. Repeating an assignment to the *same* Seat must not clear
            #     (and must not emit a spurious /groups message).
            same_seat_state = Node(root, groups=(2, 9), device_id=7)
            before = len(bopos.client.sent)
            check("apply_assign to the same Seat succeeds",
                  bopos.apply_assign(["node-a", 7, "stage-left", 3.0, 4.0],
                                     same_seat_state))
            check("same-Seat reassignment preserves membership",
                  same_seat_state.groups == (2, 9))
            check("same-Seat reassignment emits no /groups message",
                  all(msg[0] != "/groups" for msg in bopos.client.sent[before:]))

            # 5c. Unassignment clears and cannot leak either.
            unassign_state = Node(root, groups=(6, 7), device_id=7)
            before = len(bopos.client.sent)
            check("apply_unassign succeeds",
                  bopos.apply_unassign(unassign_state))
            check("unassign clears state.groups", unassign_state.groups == ())
            groups_msgs = [msg for msg in bopos.client.sent[before:] if msg[0] == "/groups"]
            check("unassign emits exactly one /groups clear",
                  groups_msgs == [["/groups", ",i", -1]], groups_msgs)

            # 4d. A failing group-clear store must fail the whole reassignment
            #     and never expose the new id with stale groups on the wire.
            fail_clear_state = Node(root, groups=(1, 4), device_id=7)
            fail_clear_state.store = FailingStore((1, 4))
            before = len(bopos.client.sent)
            check("reassignment fails when the durable group clear fails",
                  not bopos.apply_assign(["node-a", 9, "new"], fail_clear_state))
            check("failed reassignment keeps the old id",
                  fail_clear_state.id == 7)
            check("failed group-clear sends nothing to the engine",
                  len(bopos.client.sent) == before)
    finally:
        bopos.set_hostname = original_hostname


# ---------------------------------------------------------------------------
# 6. Audition parity: same scenarios, same wire shape, through audition.py.
# ---------------------------------------------------------------------------

def test_audition_parity():
    rig = object.__new__(audition.AuditionRig)
    rig.nodes = [audition.VirtualNode(0, 7, "audition-0001", 19001),
                 audition.VirtualNode(1, 8, "audition-0002", 19002)]
    rig.sock = CaptureSocket()
    rig.local_target = "127.0.0.1"
    rig.args = SimpleNamespace(target="127.0.0.1", report_port=5550)
    rig.send_id = lambda _node: None
    rig.send_matrix = lambda _node: None
    rig.send_point_values = lambda *_args: None
    rig.send_heartbeat = lambda _node: None

    def last_groups_message():
        for data, _target in reversed(rig.sock.calls):
            message = osc_message.OscMessage(data)
            if message.address == "/groups":
                return list(message.params)
        return None

    # 2/6. Replace emits exactly one complete list, matching bopos.py's shape.
    before = len(rig.sock.calls)
    rig.relay(packet("/all/os/groups", "audition-0001", 2, 9), ("127.0.0.1", 4000))
    new_calls = rig.sock.calls[before:]
    groups_calls = [c for c in new_calls
                    if osc_message.OscMessage(c[0]).address == "/groups"]
    check("audition replace emits exactly one /groups engine message",
          len(groups_calls) == 1)
    check("audition replace matches bopos.py's sorted-list shape",
          last_groups_message() == [2, 9])

    # 3/6. Clear emits exactly `groups -1`, matching the node helper's shape.
    before = len(rig.sock.calls)
    rig.relay(packet("/all/os/groups", "audition-0001"), ("127.0.0.1", 4000))
    new_calls = rig.sock.calls[before:]
    groups_calls = [c for c in new_calls
                    if osc_message.OscMessage(c[0]).address == "/groups"]
    check("audition clear emits exactly one /groups engine message",
          len(groups_calls) == 1)
    check("audition clear matches bopos.py's sentinel shape",
          last_groups_message() == [-1])

    # 4/6. Rejected (duplicate ids) reaches neither the LAN receipt nor the
    #      engine.
    rig.relay(packet("/all/os/groups", "audition-0001", 2, 9), ("127.0.0.1", 4000))
    before = len(rig.sock.calls)
    rig.relay(packet("/all/os/groups", "audition-0001", 4, 4), ("127.0.0.1", 4000))
    check("audition rejects invalid membership with no new engine traffic",
          len(rig.sock.calls) == before and rig.nodes[0].groups == (2, 9))

    # 5/6. Reassignment clears without leaking; same-Seat reassignment does
    #      not touch groups; unassign clears too.
    rig.relay(packet("/all/os/groups", "audition-0001", 3, 6), ("127.0.0.1", 4000))
    before = len(rig.sock.calls)
    rig.apply_assignment("all", ["audition-0001", 9, "different"])
    new_calls = rig.sock.calls[before:]
    groups_calls = [osc_message.OscMessage(c[0]) for c in new_calls
                    if osc_message.OscMessage(c[0]).address == "/groups"]
    check("audition reassignment clears membership",
          rig.nodes[0].groups == () and rig.nodes[0].device_id == 9)
    check("audition reassignment emits exactly one /groups clear, no stale list",
          [list(m.params) for m in groups_calls] == [[-1]])

    rig.nodes[0].groups = (5,)
    before = len(rig.sock.calls)
    rig.uid_admin(rig.nodes[0], "unassign", (), ("127.0.0.1", 4000))
    new_calls = rig.sock.calls[before:]
    groups_calls = [list(osc_message.OscMessage(c[0]).params) for c in new_calls
                    if osc_message.OscMessage(c[0]).address == "/groups"]
    check("audition unassign clears membership and sends the sentinel",
          rig.nodes[0].groups == () and groups_calls == [[-1]])


# ---------------------------------------------------------------------------
# py_compile the touched files.
# ---------------------------------------------------------------------------

def test_py_compile():
    for relative in ("python/runcontext.py", "python/groups.py", "python/bopos.py",
                      "tools/audition.py"):
        path = REPO / relative
        try:
            py_compile.compile(str(path), doraise=True,
                                cfile=os.path.join(tempfile.gettempdir(),
                                                    "bopos-groupctx-pycache.pyc"))
            ok = True
        except py_compile.PyCompileError as error:
            ok = False
            print(error)
        check(f"py_compile succeeds for {relative}", ok)


def main():
    test_launch_context()
    test_start_engine_sh()
    test_audition_engine_command()
    test_bopos_live_updates()
    test_audition_parity()
    test_py_compile()

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
