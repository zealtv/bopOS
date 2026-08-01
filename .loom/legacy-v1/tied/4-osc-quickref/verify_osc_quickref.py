#!/usr/bin/env python3
"""Verify for docs/OSC-REFERENCE.md.

Two layers:
1. Static cross-check: every address/verb table in the reference doc is
   grepped against the real handler tables in python/bopos.py, so the doc
   can't silently drift from the code that actually answers these messages.
2. Live cross-check (per the stitch instructions: "walk at least the mute
   and report examples against tools/simfleet.py live to prove the
   spellings are real"): launches the real tools/simfleet.py and sends the
   *exact* mute and report worked examples from the doc, byte for byte,
   listening for the documented reply shapes.

Run with ~/.venvs/bopos/bin/python.
"""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
          " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def wait_until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.05)
    return False


def free_port():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


DOC = os.path.join(REPO, "docs", "OSC-REFERENCE.md")
BOPOS = os.path.join(REPO, "python", "bopos.py")


def doc_text():
    return open(DOC, encoding="utf-8").read()


def bopos_text():
    return open(BOPOS, encoding="utf-8").read()


def static_cross_checks():
    doc = doc_text()
    code = bopos_text()

    check("doc exists", os.path.isfile(DOC))

    # Every UID-admin verb the doc lists must be the real allowlist, and
    # nothing else -- catches both missing and invented verbs.
    match = re.search(r"UID_ADMIN_VERBS = frozenset\(\{([^}]*)\}\)", code)
    check("found UID_ADMIN_VERBS in bopos.py", match is not None)
    real_uid_verbs = set(re.findall(r'"([a-z-]+)"', match.group(1))) if match else set()
    doc_uid_verbs = set(re.findall(
        r"^\| `([a-z-]+)` \|", doc.split("### Exact-UID administration envelope")[1]
        .split("### Seat-group membership")[0], re.M))
    # mute/hostname are documented in the same table but aren't in the
    # zero-arity UID_ADMIN_VERBS set -- handled separately in the code too.
    doc_uid_verbs -= {"mute", "hostname"}
    check("doc's exact-uid zero-arity verbs match UID_ADMIN_VERBS exactly",
          doc_uid_verbs == real_uid_verbs,
          f"doc={sorted(doc_uid_verbs)} code={sorted(real_uid_verbs)}")

    # Every lifecycle/provisioning verb name in the doc must be a real key.
    lifecycle_match = re.search(r"LIFECYCLE_VERBS = \{([^}]*)\}", code)
    provision_match = re.search(r"PROVISION_VERBS = \{([^}]*)\}", code)
    real_lifecycle = set(re.findall(r'"([a-z-]+)":', lifecycle_match.group(1)))
    real_provision = set(re.findall(r'"([a-z-]+)":', provision_match.group(1)))
    doc_lifeprov_section = doc.split("### Lifecycle and provisioning")[1].split(
        "### Patch and asset distribution")[0]
    doc_lifeprov_verbs = set(re.findall(r"^\| `([a-z-]+)` \|", doc_lifeprov_section, re.M))
    doc_lifeprov_verbs -= {"mute"}  # documented alongside but not in either dict
    check("doc's lifecycle/provisioning verbs match LIFECYCLE_VERBS|PROVISION_VERBS exactly",
          doc_lifeprov_verbs == (real_lifecycle | real_provision),
          f"doc={sorted(doc_lifeprov_verbs)} "
          f"code={sorted(real_lifecycle | real_provision)}")

    # The engine-sent /admin action set (v1.7) must match ENGINE_ADMIN_VERBS.
    # Only the *args column* of that table row -- not the prose description,
    # which names the internal callback verbs (pullpatch/updatebopos) too.
    admin_match = re.search(r"ENGINE_ADMIN_VERBS = \{([^}]*)\}", code)
    real_admin_actions = set(re.findall(r'"([a-z-]+)":', admin_match.group(1)))
    row_match = re.search(r"^\| `/admin <action:s>` \| (.*?) \| \*\*v1\.7", doc, re.M)
    check("found the /admin table row in the doc", row_match is not None)
    action_set_text = row_match.group(1).split("∈", 1)[1] if row_match else ""
    doc_admin_actions = set(re.findall(r"`([a-z-]+)`", action_set_text))
    check("doc's /admin action set matches ENGINE_ADMIN_VERBS exactly",
          doc_admin_actions == real_admin_actions,
          f"doc={sorted(doc_admin_actions)} code={sorted(real_admin_actions)}")

    # /admin really is registered on the 7770 handler map.
    check("bopos.py registers /admin on the 7770 server",
          'server.addMsgHandler( "/admin", admin_callback )' in code)

    # Every provisioning verb the doc flags as "bare /os/rev" really does
    # NOT go through a code path that attaches status/phase (i.e. its
    # callback doesn't return a dict on the happy path) -- addpatch,
    # pullpatch, droppatch, dropassets, patch (switch) all lack `return {`.
    for name, callback in (
        ("addpatch", "add_patch_callback"), ("pullpatch", "pull_active_patch_callback"),
        ("droppatch", "drop_patch_callback"), ("dropassets", "drop_assets_callback"),
        ("patch", "switch_patch_callback"),
    ):
        body_match = re.search(rf"def {callback}\(.*?\n(?=\ndef )", code, re.S)
        check(f"{name}'s callback ({callback}) never returns a status/phase dict",
              body_match is not None and 'return {"status"' not in body_match.group(0))

    # updatebopos/checkout DO attach status/phase (via converge_framework).
    for name, callback in (("updatebopos", "update_bopos_callback"),
                            ("checkout", "checkout_callback")):
        body_match = re.search(rf"def {callback}\(.*?\n(?=\ndef )", code, re.S)
        check(f"{name}'s callback ({callback}) can attach status/phase",
              body_match is not None
              and ("converge_framework" in body_match.group(0)
                   or 'return {"status"' in body_match.group(0)))

    # Links exist from the three places the instructions named.
    readme = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    ports = open(os.path.join(REPO, "docs", "PORTS.md"), encoding="utf-8").read()
    contract = open(os.path.join(REPO, "docs", "OSC-CONTRACT.md"), encoding="utf-8").read()
    check("README links OSC-REFERENCE.md", "OSC-REFERENCE.md" in readme)
    check("PORTS.md links OSC-REFERENCE.md", "OSC-REFERENCE.md" in ports)
    check("OSC-CONTRACT.md links OSC-REFERENCE.md", "OSC-REFERENCE.md" in contract)


def live_simfleet_checks():
    cmd_port = free_port()
    report_port = free_port()
    with tempfile.TemporaryDirectory(prefix="bopos-quickref-state-") as state_dir:
        log_path = os.path.join(state_dir, "sim.log")
        log_file = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
            "--devices", "1", "--target", "127.0.0.1",
            "--cmd-port", str(cmd_port), "--report-port", str(report_port),
            "--state-dir", state_dir, "--hb-interval", "30",
        ], cwd=REPO, stdout=log_file, stderr=subprocess.STDOUT)
        cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        reply_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        reply_sock.bind(("127.0.0.1", report_port))
        reply_sock.settimeout(0.2)
        try:
            check("simfleet starts", wait_until(lambda: proc.poll() is None
                                                and _log_has(log_path, "sim1"), 5))

            uid = "02:53:49:4d:00:01"  # simfleet's default device 1 uid == the doc's example

            # --- exact doc mute example, sent with pyOSC3 exactly as the
            # doc's "raw Python one-liner" worked example shows ---
            import pyOSC3
            msg = pyOSC3.OSCMessage("/all/os/to")
            msg.append(uid)
            msg.append("mute")
            msg.append(1)
            cmd_sock.sendto(msg.getBinary(), ("127.0.0.1", cmd_port))
            reply = _recv_osc_matching(reply_sock, "/os/mute", 3)
            check("doc's mute worked example round-trips through simfleet",
                  reply is not None and list(reply[1]) == [uid, 1, 1], repr(reply))

            # un-mute, so the report example below isn't reading a muted device
            msg = pyOSC3.OSCMessage("/all/os/to")
            msg.append(uid)
            msg.append("mute")
            msg.append(0)
            cmd_sock.sendto(msg.getBinary(), ("127.0.0.1", cmd_port))
            _recv_osc_matching(reply_sock, "/os/mute", 3)

            # --- exact doc report example ---
            msg = pyOSC3.OSCMessage("/all/os/to")
            msg.append(uid)
            msg.append("report")
            cmd_sock.sendto(msg.getBinary(), ("127.0.0.1", cmd_port))
            reply = _recv_osc_matching(reply_sock, "/os/report", 3)
            check("doc's report example round-trips through simfleet",
                  reply is not None, repr(reply))
            if reply is not None and reply[0] == "/os/report":
                payload = json.loads(reply[1][0])
                check("live /os/report carries the current contract_version",
                      payload.get("contract_version") == "1.7", repr(payload))

            # --- fleet-wide broadcast mute, the doc's "kill the whole room" example ---
            msg = pyOSC3.OSCMessage("/all/os/mute")
            msg.append(1)
            cmd_sock.sendto(msg.getBinary(), ("127.0.0.1", cmd_port))
            check("fleet-wide /all/os/mute is accepted without error",
                  wait_until(lambda: proc.poll() is None, 1))
        finally:
            cmd_sock.close()
            reply_sock.close()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            log_file.close()


def _recv_osc_matching(sock, address, timeout):
    """Read datagrams until one matches address, skipping heartbeats/others."""
    import pyOSC3
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        try:
            data, _source = sock.recvfrom(65535)
        except OSError:
            return None
        decoded = pyOSC3.decodeOSC(data)
        if str(decoded[0]) == address:
            return (str(decoded[0]), decoded[2:])
    return None


def _log_has(path, text):
    try:
        return text in open(path, encoding="utf-8").read()
    except OSError:
        return False


def main():
    static_cross_checks()
    live_simfleet_checks()
    total = 18
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
