#!/usr/bin/env python3
"""Browser-free verify for rev-outcome-receipts.

Bob's finding (.loom/tied/4-osc-quickref/notes.md): five provisioning verbs
-- addpatch, pullpatch, droppatch, dropassets, patch (switch) -- always sent
a bare /os/rev with no status/phase, even on failure, so an operator with a
bare OSC client could not tell success from failure. This stitch makes the
five callbacks in python/bopos.py return small outcome dicts the way
converge_framework already does, so run_admin_verb/rev_reply append
<status> <phase> to the existing optional bracket (contract v1.7 -- the
bracket was already optional; this is the code catching up).

Exercises the callbacks directly with monkeypatched subprocess/filesystem
effects -- nothing here clones from the network, reboots, or rm -rf's
outside a temp dir. Follows the binding-avoidance pattern from
.loom/tied/2-engine-admin-requests/verify_*.py: pyOSC3.OSCServer/OSCClient
are faked before `import bopos`, so importing this module never binds the
real UDP ports and never fights a running bopos.py instance.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))
sys.path.insert(0, os.path.join(REPO, "tools"))

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
          " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def __init__(self):
        self.sent = []

    def connect(self, target):
        pass

    def send(self, message):
        self.sent.append(pyOSC3.decodeOSC(message.getBinary()))


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["bopos.py", "unknown"]
import bopos  # noqa: E402
import manifest  # noqa: E402


class FakeReplySocket:
    """Captures rev_reply datagrams instead of touching a real UDP socket."""

    def __init__(self):
        self.sent = []  # list of (address_tuple, decoded_osc)

    def sendto(self, data, address):
        self.sent.append((address, pyOSC3.decodeOSC(data)))

    def last_status_phase(self):
        if not self.sent:
            return None
        decoded = self.sent[-1][1]
        # decoded == ["/os/rev", ",sss[ss]", sha, model, uid, (status, phase)]
        tail = decoded[2:]
        if len(tail) >= 5:
            return tail[3], tail[4]
        return None


def write_manifest(path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, manifest.MANIFEST_NAME), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def write_patch(root, name):
    path = os.path.join(root, "patches", name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "w", encoding="utf-8") as target:
        target.write(name)
    write_manifest(path)


def set_active(root, name):
    with open(os.path.join(root, "patches", "active_patch.txt"), "w",
              encoding="utf-8") as target:
        target.write((name or "") + "\n")


class Sandbox:
    """Swaps bopos globals for the duration of a `with` block.

    `bopos.subprocess` and `bopos.shutil` are the *same* module objects as
    this file's own `subprocess`/`shutil` imports (both did `import X`), so
    saving/restoring the attribute on `bopos` would not undo a mutation of
    e.g. `subprocess.run` -- it is the same singleton either way. Anything
    that monkeypatches `subprocess.run` or `shutil.rmtree` must save and
    restore the real function itself; Sandbox only owns the bopos-local
    names that really are independent (BOPOS_DIR, run_command, etc).
    """

    ATTRS = ("BOPOS_DIR", "run_command", "engine_alive", "hb_wake",
             "request_power_action")

    def __enter__(self):
        self.saved = {name: getattr(bopos, name) for name in self.ATTRS}
        self.saved_subprocess_run = subprocess.run
        self.saved_shutil_rmtree = shutil.rmtree
        self.root = tempfile.mkdtemp(prefix="rev-outcome-receipts-")
        os.makedirs(os.path.join(self.root, "patches"))
        os.makedirs(os.path.join(self.root, "assets"))
        os.makedirs(os.path.join(self.root, "run"))
        os.makedirs(os.path.join(self.root, "bash"))
        bopos.BOPOS_DIR = self.root
        bopos.run_command = lambda argv, wait_for_start=False: 0
        bopos.engine_alive = lambda: 1
        bopos.hb_wake = types.SimpleNamespace(set=lambda: None)
        bopos.request_power_action = lambda action: True
        return self

    def __exit__(self, *exc):
        for name, value in self.saved.items():
            setattr(bopos, name, value)
        subprocess.run = self.saved_subprocess_run
        shutil.rmtree = self.saved_shutil_rmtree
        shutil.rmtree(self.root, ignore_errors=True)


def switch_patch_checks():
    with Sandbox() as box:
        root = box.root
        # invalid: no args
        result = bopos.switch_patch_callback(args=[])
        check("switch: no args -> invalid-name",
              result == {"status": "err", "phase": "invalid-name"}, repr(result))

        # invalid: bad pattern
        result = bopos.switch_patch_callback(args=["../escape"])
        check("switch: bad pattern -> invalid-name",
              result == {"status": "err", "phase": "invalid-name"}, repr(result))

        # not found: no such patch directory
        result = bopos.switch_patch_callback(args=["ghost"])
        check("switch: missing patch -> not-found",
              result == {"status": "err", "phase": "not-found"}, repr(result))

        # stop-failed
        write_patch(root, "new")
        set_active(root, "old")
        write_patch(root, "old")
        bopos.run_command = lambda argv, wait_for_start=False: (
            1 if os.path.basename(argv[1]) == "stop-engine.sh" else 0)
        result = bopos.switch_patch_callback(args=["new"])
        check("switch: stop script fails -> stop-failed",
              result == {"status": "err", "phase": "stop-failed"}, repr(result))

        # write-failed: make active_patch.txt's directory read-only so the
        # atomic replace cannot create its .tmp file
        patches_dir = os.path.join(root, "patches")
        bopos.run_command = lambda argv, wait_for_start=False: 0
        mode = os.stat(patches_dir).st_mode
        os.chmod(patches_dir, 0o555)
        try:
            result = bopos.switch_patch_callback(args=["new"])
        finally:
            os.chmod(patches_dir, mode)
        if os.geteuid() == 0:
            check("switch: unwritable active_patch.txt -> write-failed (skipped as root)",
                  True, "running as root; permission bits do not apply")
        else:
            check("switch: unwritable active_patch.txt -> write-failed",
                  result == {"status": "err", "phase": "write-failed"}, repr(result))

        # start-failed: stop ok, write ok, start fails, current exists+restorable
        set_active(root, "old")
        attempts = {"starts": 0}

        def fail_new_start(argv, wait_for_start=False):
            name = os.path.basename(argv[1])
            if name == "start-engine.sh":
                attempts["starts"] += 1
                return 1 if attempts["starts"] == 1 else 0
            return 0

        bopos.run_command = fail_new_start
        result = bopos.switch_patch_callback(args=["new"])
        check("switch: start fails then restores -> start-failed",
              result == {"status": "err", "phase": "start-failed"}
              and open(os.path.join(patches_dir, "active_patch.txt"),
                       encoding="utf-8").read().strip() == "old",
              repr(result))

        # restore-failed: start fails and there was no prior active patch to
        # restore to (current is falsy)
        os.remove(os.path.join(patches_dir, "active_patch.txt"))
        bopos.run_command = lambda argv, wait_for_start=False: (
            1 if os.path.basename(argv[1]) == "start-engine.sh" else 0)
        result = bopos.switch_patch_callback(args=["new"])
        check("switch: start fails with nothing to restore -> restore-failed",
              result == {"status": "err", "phase": "restore-failed"}, repr(result))

        # success
        set_active(root, "old")
        bopos.run_command = lambda argv, wait_for_start=False: 0
        bopos.engine_alive = lambda: 1
        result = bopos.switch_patch_callback(args=["new"])
        check("switch: clean switch -> ok switched",
              result == {"status": "ok", "phase": "switched"}, repr(result))


def add_patch_checks():
    with Sandbox() as box:
        root = box.root
        result = bopos.add_patch_callback(args=["onlyuser"])
        check("addpatch: too few args -> invalid-args",
              result == {"status": "err", "phase": "invalid-args"}, repr(result))

        result = bopos.add_patch_callback(args=["bad user", "repo"])
        check("addpatch: invalid user -> invalid-name",
              result == {"status": "err", "phase": "invalid-name"}, repr(result))

        class FakeCompleted:
            def __init__(self, returncode, stderr=b""):
                self.returncode = returncode
                self.stdout = b""
                self.stderr = stderr

        def ls_remote_fails(argv, **kwargs):
            return FakeCompleted(1)

        subprocess.run = ls_remote_fails
        result = bopos.add_patch_callback(args=["someone", "repo"])
        check("addpatch: repo not found -> not-found",
              result == {"status": "err", "phase": "not-found"}, repr(result))

        def ls_remote_ok(argv, **kwargs):
            if argv[1] == "ls-remote":
                return FakeCompleted(0)
            raise AssertionError("unexpected subprocess call: " + repr(argv))

        subprocess.run = ls_remote_ok
        dest = os.path.join(root, "patches", "repo")
        os.makedirs(dest)
        original_rmtree = shutil.rmtree
        shutil.rmtree = lambda path, *a, **k: (_ for _ in ()).throw(OSError("locked"))
        result = bopos.add_patch_callback(args=["someone", "repo"])
        check("addpatch: cannot remove existing dir -> remove-failed",
              result == {"status": "err", "phase": "remove-failed"}, repr(result))
        shutil.rmtree = original_rmtree
        shutil.rmtree(dest, ignore_errors=True)

        def ls_remote_then_clone_fail(argv, **kwargs):
            if argv[1] == "ls-remote":
                return FakeCompleted(0)
            if argv[1] == "clone":
                return FakeCompleted(1, stderr=b"denied")
            raise AssertionError("unexpected subprocess call: " + repr(argv))

        subprocess.run = ls_remote_then_clone_fail
        result = bopos.add_patch_callback(args=["someone", "repo"])
        check("addpatch: clone fails -> clone-failed",
              result == {"status": "err", "phase": "clone-failed"}, repr(result))

        def ls_remote_then_clone_timeout(argv, **kwargs):
            if argv[1] == "ls-remote":
                return FakeCompleted(0)
            raise subprocess.TimeoutExpired(cmd=argv, timeout=120)

        subprocess.run = ls_remote_then_clone_timeout
        result = bopos.add_patch_callback(args=["someone", "repo"])
        check("addpatch: clone times out -> clone-failed",
              result == {"status": "err", "phase": "clone-failed"}, repr(result))

        def ls_remote_then_clone_ok(argv, **kwargs):
            if argv[1] == "ls-remote":
                return FakeCompleted(0)
            if argv[1] == "clone":
                write_manifest(dest)
                return FakeCompleted(0)
            raise AssertionError("unexpected subprocess call: " + repr(argv))

        subprocess.run = ls_remote_then_clone_ok
        result = bopos.add_patch_callback(args=["someone", "repo"])
        check("addpatch: clean clone -> ok cloned",
              result == {"status": "ok", "phase": "cloned"}, repr(result))


def pull_active_patch_checks():
    with Sandbox() as box:
        class FakeCompleted:
            def __init__(self, returncode):
                self.returncode = returncode

        for code, phase in bopos._PULL_ACTIVE_PATCH_PHASES.items():
            subprocess.run = lambda argv, _c=code, **k: FakeCompleted(_c)
            result = bopos.pull_active_patch_callback()
            check(f"pullpatch: exit {code} -> {phase}",
                  result == {"status": "err", "phase": phase}, repr(result))

        subprocess.run = lambda argv, **k: FakeCompleted(99)
        result = bopos.pull_active_patch_callback()
        check("pullpatch: unmapped exit code -> pull-failed",
              result == {"status": "err", "phase": "pull-failed"}, repr(result))

        def raise_timeout(argv, **k):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=120)

        subprocess.run = raise_timeout
        result = bopos.pull_active_patch_callback()
        check("pullpatch: timeout -> err timeout",
              result == {"status": "err", "phase": "timeout"}, repr(result))

        def raise_generic(argv, **k):
            raise RuntimeError("boom")

        subprocess.run = raise_generic
        result = bopos.pull_active_patch_callback()
        check("pullpatch: exception -> err exception",
              result == {"status": "err", "phase": "exception"}, repr(result))

        subprocess.run = lambda argv, **k: FakeCompleted(0)
        result = bopos.pull_active_patch_callback()
        check("pullpatch: success -> ok pulled, reboot requested",
              result == {"status": "ok", "phase": "pulled", "reboot": True}, repr(result))

        # bash/pull_active_patch.sh itself must no longer reboot -- the
        # receipt-before-reboot ordering now lives in run_admin_verb.
        script_path = os.path.join(REPO, "bash", "pull_active_patch.sh")
        with open(script_path, encoding="utf-8") as source:
            script_text = source.read()
        check("pull_active_patch.sh no longer reboots itself",
              "\nreboot" not in script_text and not script_text.rstrip().endswith("reboot"),
              "script still contains a bare reboot call")


def receipt_before_reboot_check():
    # run_admin_verb must send the /os/rev receipt before it asks for the
    # reboot -- mirrors converge_framework's already-verified ordering.
    with Sandbox() as box:
        events = []

        class FakeCompleted:
            returncode = 0

        subprocess.run = lambda argv, **k: FakeCompleted()

        class OrderingReplySocket:
            def sendto(self, data, address):
                events.append("receipt")

        def tracked_power_action(action):
            events.append("reboot-requested")
            return True

        bopos.request_power_action = tracked_power_action
        bopos.run_admin_verb(bopos.pull_active_patch_callback, [], bopos.node_state,
                             reply_socket=OrderingReplySocket(), requester="10.0.0.5")
        check("pullpatch success sends receipt before requesting reboot",
              events == ["receipt", "reboot-requested"], repr(events))


def drop_patch_checks():
    with Sandbox() as box:
        root = box.root
        result = bopos.drop_patch_callback(args=[])
        check("droppatch: no args -> invalid-name",
              result == {"status": "err", "phase": "invalid-name"}, repr(result))

        result = bopos.drop_patch_callback(args=["../escape"])
        check("droppatch: bad pattern -> invalid-name",
              result == {"status": "err", "phase": "invalid-name"}, repr(result))

        write_patch(root, "live")
        set_active(root, "live")
        result = bopos.drop_patch_callback(args=["live"])
        check("droppatch: refuses active patch -> active-patch",
              result == {"status": "err", "phase": "active-patch"}
              and os.path.isdir(os.path.join(root, "patches", "live")), repr(result))

        write_patch(root, "old")
        target = os.path.join(root, "patches", "old")
        original_rmtree = shutil.rmtree
        shutil.rmtree = lambda path, *a, **k: (_ for _ in ()).throw(OSError("busy"))
        result = bopos.drop_patch_callback(args=["old"])
        check("droppatch: remove raises -> remove-failed",
              result == {"status": "err", "phase": "remove-failed"}, repr(result))
        shutil.rmtree = original_rmtree

        result = bopos.drop_patch_callback(args=["old"])
        check("droppatch: clean drop -> ok dropped",
              result == {"status": "ok", "phase": "dropped"}
              and not os.path.exists(target), repr(result))


def drop_assets_checks():
    with Sandbox() as box:
        root = box.root
        result = bopos.drop_assets_callback(args=[])
        check("dropassets: no args -> invalid-name",
              result == {"status": "err", "phase": "invalid-name"}, repr(result))

        result = bopos.drop_assets_callback(args=[".hidden"])
        check("dropassets: invalid slot -> invalid-name",
              result == {"status": "err", "phase": "invalid-name"}, repr(result))

        slot_dir = os.path.join(root, "assets", "pack1")
        os.makedirs(slot_dir)
        with open(os.path.join(slot_dir, "a.wav"), "w", encoding="utf-8") as target:
            target.write("x")
        original_rmtree = shutil.rmtree
        shutil.rmtree = lambda path, *a, **k: (_ for _ in ()).throw(OSError("busy"))
        result = bopos.drop_assets_callback(args=["pack1"])
        check("dropassets: remove raises -> remove-failed",
              result == {"status": "err", "phase": "remove-failed"}, repr(result))
        shutil.rmtree = original_rmtree

        result = bopos.drop_assets_callback(args=["pack1"])
        check("dropassets: clean drop -> ok dropped",
              result == {"status": "ok", "phase": "dropped"}
              and not os.path.exists(slot_dir), repr(result))


def run_admin_verb_rev_reply_checks():
    # end-to-end: run_admin_verb -> rev_reply appends <status> <phase>
    # exactly the way converge_framework's callers already do.
    with Sandbox() as box:
        state = types.SimpleNamespace(uid="aa:bb", update_model="persistent", version="abc1234")
        bopos.resolve_version = lambda: "abc1234"

        def err_callback(path='', tags='', args='', source=''):
            return {"status": "err", "phase": "not-found"}

        reply = FakeReplySocket()
        bopos.run_admin_verb(err_callback, [], state, reply_socket=reply, requester="10.0.0.5")
        check("run_admin_verb appends err phase to /os/rev",
              reply.last_status_phase() == ("err", "not-found"), repr(reply.sent))

        def ok_callback(path='', tags='', args='', source=''):
            return {"status": "ok", "phase": "dropped"}

        reply = FakeReplySocket()
        bopos.run_admin_verb(ok_callback, [], state, reply_socket=reply, requester="10.0.0.5")
        check("run_admin_verb appends ok phase to /os/rev",
              reply.last_status_phase() == ("ok", "dropped"), repr(reply.sent))

        # an exception inside the callback still yields an attributable
        # receipt rather than silently dropping the reply
        def raising_callback(path='', tags='', args='', source=''):
            raise RuntimeError("boom")

        reply = FakeReplySocket()
        bopos.run_admin_verb(raising_callback, [], state, reply_socket=reply, requester="10.0.0.5")
        check("run_admin_verb reports err exception if the callback raises",
              reply.last_status_phase() == ("err", "exception"), repr(reply.sent))


def provision_verbs_map_unchanged_check():
    check("PROVISION_VERBS still maps all five verbs to their callbacks",
          bopos.PROVISION_VERBS["patch"] is bopos.switch_patch_callback
          and bopos.PROVISION_VERBS["addpatch"] is bopos.add_patch_callback
          and bopos.PROVISION_VERBS["pullpatch"] is bopos.pull_active_patch_callback
          and bopos.PROVISION_VERBS["droppatch"] is bopos.drop_patch_callback
          and bopos.PROVISION_VERBS["dropassets"] is bopos.drop_assets_callback)
    check("ENGINE_ADMIN_VERBS still reuses pull_active_patch_callback for update-patch",
          bopos.ENGINE_ADMIN_VERBS["update-patch"] is bopos.pull_active_patch_callback)


def simfleet_mirror_checks():
    import simfleet

    class FakeDevice:
        mac = "02:53:49:4d:00:09"
        version = "0000001"
        ephemeral = False
        hostname = "sim-rev-check"
        patches = {"demo-pd": {"git": True, "manifest": True, "fingerprint": "abc"}}
        asset_slots = {"pack1": {"fingerprint": "x", "files": 1, "bytes": 1}}
        active_patch = "demo-pd"
        engine_restart_until = 0.0

    fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
    fleet.tty = False
    fleet.args = types.SimpleNamespace(report_port=5550)
    fleet.log = lambda device, message: None
    scheduled = []
    fleet.schedule = lambda delay, fn, *a: scheduled.append((delay, fn, a)) or fn(*a)

    sent = []

    def fake_send_rev(device, source, status=None, phase=None):
        sent.append((status, phase))

    fleet.send_rev = fake_send_rev

    device = FakeDevice()
    fleet.admin_verb(device, "patch", [], ("10.0.0.9", 6660))
    check("simfleet patch with no args -> err invalid-name",
          sent[-1] == ("err", "invalid-name"), repr(sent))

    fleet.admin_verb(device, "patch", ["ghost"], ("10.0.0.9", 6660))
    check("simfleet patch unknown name -> err not-found",
          sent[-1] == ("err", "not-found"), repr(sent))

    fleet.admin_verb(device, "patch", ["demo-pd"], ("10.0.0.9", 6660))
    check("simfleet patch success -> ok switched",
          sent[-1] == ("ok", "switched"), repr(sent))

    fleet.admin_verb(device, "addpatch", ["someone"], ("10.0.0.9", 6660))
    check("simfleet addpatch too few args -> err invalid-args",
          sent[-1] == ("err", "invalid-args"), repr(sent))

    fleet.admin_verb(device, "addpatch", ["someone", "repo"], ("10.0.0.9", 6660))
    check("simfleet addpatch success -> ok cloned",
          sent[-1] == ("ok", "cloned"), repr(sent))

    fleet.admin_verb(device, "pullpatch", [], ("10.0.0.9", 6660))
    check("simfleet pullpatch -> ok pulled",
          sent[-1] == ("ok", "pulled"), repr(sent))

    fleet.admin_verb(device, "droppatch", [], ("10.0.0.9", 6660))
    check("simfleet droppatch no args -> err invalid-name",
          sent[-1] == ("err", "invalid-name"), repr(sent))

    fleet.admin_verb(device, "droppatch", ["demo-pd"], ("10.0.0.9", 6660))
    check("simfleet droppatch refuses active patch -> err active-patch",
          sent[-1] == ("err", "active-patch"), repr(sent))

    fleet.admin_verb(device, "droppatch", ["repo"], ("10.0.0.9", 6660))
    check("simfleet droppatch success -> ok dropped",
          sent[-1] == ("ok", "dropped"), repr(sent))

    fleet.admin_verb(device, "dropassets", [".hidden"], ("10.0.0.9", 6660))
    check("simfleet dropassets invalid slot -> err invalid-name",
          sent[-1] == ("err", "invalid-name"), repr(sent))

    fleet.admin_verb(device, "dropassets", ["pack1"], ("10.0.0.9", 6660))
    check("simfleet dropassets success -> ok dropped",
          sent[-1] == ("ok", "dropped"), repr(sent))


def main():
    switch_patch_checks()
    add_patch_checks()
    pull_active_patch_checks()
    receipt_before_reboot_check()
    drop_patch_checks()
    drop_assets_checks()
    run_admin_verb_rev_reply_checks()
    provision_verbs_map_unchanged_check()
    simfleet_mirror_checks()
    total = len(FAILURES) + PASS_COUNT[0]
    print(f"\n{PASS_COUNT[0]}/{total} passed")
    return 1 if FAILURES else 0


PASS_COUNT = [0]
_original_check = check


def _counting_check(label, condition, detail=""):
    if condition:
        PASS_COUNT[0] += 1
    _original_check(label, condition, detail)


check = _counting_check  # noqa: F811


if __name__ == "__main__":
    raise SystemExit(main())
