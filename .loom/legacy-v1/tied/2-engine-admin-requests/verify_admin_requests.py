#!/usr/bin/env python3
"""Browser-free verify for the engine-sent /admin <action> request (v1.7).

Exercises python/bopos.py's admin_callback and ENGINE_ADMIN_VERBS dispatch
directly -- no real OSCServer is bound (pyOSC3.OSCServer is faked before
import, same pattern as .loom/tied/08-unbound-admin-seam/verify_uid_admin.py)
so nothing actually reboots or shuts down the machine running this script.
Also exercises tools/simfleet.py's admin_request log-only mirror.
"""

import os
import sys
import time

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


def wait_until(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.02)
    return False


# Import the real helper without opening its legacy OSC server (mirrors
# verify_uid_admin.py's approach).
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


def admin_dispatch_checks():
    calls = []
    originals = dict(bopos.ENGINE_ADMIN_VERBS)
    for name in originals:
        bopos.ENGINE_ADMIN_VERBS[name] = (
            lambda *args, action=name, **kwargs: calls.append(action))
    try:
        # every ratified action reaches its callback exactly once
        for action in ("update-patch", "update-bopos", "shutdown", "reboot"):
            calls.clear()
            bopos.admin_callback(args=[action])
            check(f"/admin {action} dispatches its callback",
                  wait_until(lambda: calls == [action]), repr(calls))

        # unknown action: logged, nothing dispatched, never fatal
        calls.clear()
        bopos.admin_callback(args=["nonsense"])
        time.sleep(.1)
        check("unknown /admin action dispatches nothing", calls == [])

        # missing action: logged, nothing dispatched, never fatal
        calls.clear()
        bopos.admin_callback(args=[])
        time.sleep(.1)
        check("empty /admin dispatches nothing", calls == [])

        # registered on the 7770 handler map used at start-up
        check("/admin is registered on the engine-request server",
              bopos.server.handlers.get("/admin") is bopos.admin_callback,
              repr(bopos.server.handlers.get("/admin")))
    finally:
        bopos.ENGINE_ADMIN_VERBS.clear()
        bopos.ENGINE_ADMIN_VERBS.update(originals)


def no_reply_no_crash_check():
    # run_admin_verb must not explode when reply_socket/requester are the
    # admin_callback defaults (None, None) -- the engine gets no reply.
    outcomes = []

    def fake_reboot(path='', tags='', args='', source=''):
        outcomes.append("reboot-ran")
        return True

    original = bopos.ENGINE_ADMIN_VERBS["reboot"]
    bopos.ENGINE_ADMIN_VERBS["reboot"] = fake_reboot
    try:
        bopos.admin_callback(args=["reboot"])
        check("engine-originated admin verb runs without a reply socket",
              wait_until(lambda: outcomes == ["reboot-ran"]), repr(outcomes))
    finally:
        bopos.ENGINE_ADMIN_VERBS["reboot"] = original


def reuses_lifecycle_and_provision_callbacks_check():
    check("update-patch reuses the LAN pullpatch callback",
          bopos.ENGINE_ADMIN_VERBS["update-patch"]
          is bopos.PROVISION_VERBS["pullpatch"])
    check("update-bopos reuses the LAN updatebopos callback",
          bopos.ENGINE_ADMIN_VERBS["update-bopos"]
          is bopos.PROVISION_VERBS["updatebopos"])
    check("shutdown reuses the LAN shutdown callback",
          bopos.ENGINE_ADMIN_VERBS["shutdown"]
          is bopos.LIFECYCLE_VERBS["shutdown"])
    check("reboot reuses the LAN reboot callback",
          bopos.ENGINE_ADMIN_VERBS["reboot"]
          is bopos.LIFECYCLE_VERBS["reboot"])


def contract_version_check():
    import inspect
    source = inspect.getsource(bopos.report_reply)
    check("bopos.py reports contract_version 1.7", '"contract_version": "1.7"' in source)


def simfleet_admin_mirror_check():
    import simfleet

    class FakeDevice:
        hostname = "sim-admin-check"
        device_id = 3

    logged = []
    fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
    fleet.tty = False
    fleet.log = lambda device, message: logged.append(message)

    fleet.admin_request(FakeDevice(), "update-bopos")
    check("simfleet logs a known admin action instead of executing it",
          logged == ["admin update-bopos"], repr(logged))

    logged.clear()
    fleet.admin_request(FakeDevice(), "reboot-the-laptop")
    check("simfleet logs unknown admin actions without acting on them",
          logged == ["admin unknown-action=reboot-the-laptop"], repr(logged))


def main():
    admin_dispatch_checks()
    no_reply_no_crash_check()
    reuses_lifecycle_and_provision_callbacks_check()
    contract_version_check()
    simfleet_admin_mirror_check()
    total = 15
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
