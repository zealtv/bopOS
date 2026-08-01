#!/usr/bin/env python3
"""Local, non-destructive verification for unattended bopOS convergence."""
import asyncio
import json
import os
import shutil
import stat
import subprocess
import socket
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repository")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                              " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def executable(path, content):
    with open(path, "w", encoding="utf-8") as target:
        target.write(content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


FAKE_GIT = r'''#!/bin/bash
printf '%s | prompt=%s interactive=%s ssh=%s\n' "$*" "${GIT_TERMINAL_PROMPT:-}" \
  "${GCM_INTERACTIVE:-}" "${GIT_SSH_COMMAND:-}" >> "$FAKE_LOG"
if [ "$1" = "-C" ] && [ "$3" = "rev-parse" ]; then
  printf '%s\n' "$FAKE_REPO"
  exit 0
fi
if [ "$*" = "restore ." ]; then
  printf 'demo-pd\n' > "$FAKE_REPO/patches/active_patch.txt"
fi
if [ -n "${FAKE_GIT_FAIL_MATCH:-}" ] && [[ "$*" == *"$FAKE_GIT_FAIL_MATCH"* ]]; then
  exit 42
fi
exit 0
'''

FAKE_SUDO = r'''#!/bin/bash
printf '%s\n' "$*" >> "$FAKE_SUDO_LOG"
[ "${FAKE_SUDO_FAIL:-0}" = 0 ]
'''


def shell_fixture():
    temp = tempfile.mkdtemp(prefix="bopos-update-")
    root = os.path.join(temp, "repo")
    fakebin = os.path.join(temp, "bin")
    os.makedirs(os.path.join(root, "bash"))
    os.makedirs(os.path.join(root, "patches"))
    os.makedirs(fakebin)
    for name in ("update.sh", "checkout.sh"):
        shutil.copy2(os.path.join(REPO, "bash", name), os.path.join(root, "bash", name))
    executable(os.path.join(fakebin, "git"), FAKE_GIT)
    executable(os.path.join(fakebin, "sudo"), FAKE_SUDO)
    executable(os.path.join(fakebin, "systemctl"), "#!/bin/bash\nexit 0\n")
    active = os.path.join(root, "patches", "active_patch.txt")
    with open(active, "w", encoding="utf-8") as target:
        target.write("stage-show\n")
    env = dict(os.environ, PATH=fakebin + os.pathsep + os.environ.get("PATH", ""),
               BOPOS_SUDO=os.path.join(fakebin, "sudo"),
               BOPOS_SYSTEMCTL=os.path.join(fakebin, "systemctl"),
               FAKE_REPO=root, FAKE_LOG=os.path.join(temp, "git.log"),
               FAKE_SUDO_LOG=os.path.join(temp, "sudo.log"))
    return temp, root, active, env


def read(path):
    try:
        with open(path, encoding="utf-8") as source:
            return source.read()
    except OSError:
        return ""


def run_shell_checks():
    temp, root, active, env = shell_fixture()
    try:
        denied = dict(env, FAKE_SUDO_FAIL="1")
        result = subprocess.run(["bash", os.path.join(root, "bash", "update.sh")],
                                env=denied, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=5)
        check("authorization failure is terminal", result.returncode != 0)
        check("authorization phase is machine-readable",
              "BOPOS_UPDATE_RESULT status=err phase=authorization" in result.stdout,
              result.stdout)
        check("authorization fails before Git", not read(env["FAKE_LOG"]), read(env["FAKE_LOG"]))
        check("authorization failure preserves active patch", read(active).strip() == "stage-show")

        with open(active, "w", encoding="utf-8") as target:
            target.write("stage-show\n")
        pull_fail = dict(env, FAKE_SUDO_FAIL="0", FAKE_GIT_FAIL_MATCH="pull")
        result = subprocess.run(["bash", os.path.join(root, "bash", "update.sh")],
                                env=pull_fail, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=5)
        log = read(env["FAKE_LOG"])
        check("pull failure is terminal", result.returncode != 0)
        check("pull phase is machine-readable",
              "BOPOS_UPDATE_RESULT status=err phase=pull" in result.stdout, result.stdout)
        check("failed pull restores active patch", read(active).strip() == "stage-show")
        check("failed pull does not reach submodule convergence",
              "submodule sync" not in log and "submodule update" not in log, log)

        open(env["FAKE_LOG"], "w").close()
        with open(active, "w", encoding="utf-8") as target:
            target.write("stage-show\n")
        success = dict(env, FAKE_SUDO_FAIL="0")
        result = subprocess.run(["bash", os.path.join(root, "bash", "update.sh")],
                                env=success, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=5)
        log = read(env["FAKE_LOG"])
        check("framework convergence succeeds", result.returncode == 0, result.stdout)
        check("success phase is machine-readable",
              "BOPOS_UPDATE_RESULT status=ok phase=converged" in result.stdout)
        check("successful convergence preserves active patch", read(active).strip() == "stage-show")
        check("Git cannot prompt", "prompt=0 interactive=never" in log and
              "ssh=ssh -o BatchMode=yes" in log, log)
        check("pull is fast-forward-only and recursive",
              "pull --ff-only --recurse-submodules" in log, log)
        check("submodules sync then update", "submodule sync --recursive" in log and
              "submodule update --init --recursive" in log, log)
        sudo_calls = read(env["FAKE_SUDO_LOG"]).splitlines()
        check("runtime script only preflights reboot",
              len(sudo_calls) == 3 and all(call.startswith("-n -l ") for call in sudo_calls),
              repr(sudo_calls))

        open(env["FAKE_LOG"], "w").close()
        with open(active, "w", encoding="utf-8") as target:
            target.write("stage-show\n")
        fetch_fail = dict(env, FAKE_GIT_FAIL_MATCH="fetch")
        result = subprocess.run(["bash", os.path.join(root, "bash", "checkout.sh"), "next"],
                                env=fetch_fail, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=5)
        check("checkout fetch fails without prompting", result.returncode != 0 and
              "status=err phase=fetch" in result.stdout, result.stdout)
        check("failed checkout preserves active patch", read(active).strip() == "stage-show")
    finally:
        shutil.rmtree(temp)


def run_python_checks():
    import pyOSC3

    class FakeServer:
        def __init__(self, target):
            self.handlers = {}
        def addMsgHandler(self, address, callback):
            self.handlers[address] = callback
        def close(self):
            pass

    class FakeClient:
        def connect(self, target):
            pass
        def send(self, message):
            pass

    pyOSC3.OSCServer = FakeServer
    pyOSC3.OSCClient = FakeClient
    sys.path.insert(0, os.path.join(REPO, "python"))
    old_argv = sys.argv
    sys.argv = ["bopos.py", "unknown"]
    import bopos
    sys.argv = old_argv

    class ReplySocket:
        def __init__(self):
            self.calls = []
        def sendto(self, data, target):
            self.calls.append((pyOSC3.decodeOSC(data), target))

    state = bopos.node_state
    state.uid = "aa:bb:cc:dd:ee:ff"
    state.update_model = "persistent"
    original_resolve = bopos.resolve_version
    original_power = bopos.request_power_action
    bopos.resolve_version = lambda: "abc1234"
    try:
        power = []
        bopos.request_power_action = lambda action: power.append(action) or True
        sock = ReplySocket()
        bopos.run_admin_verb(lambda *unused: {"status": "ok", "phase": "converged",
                                              "reboot": True}, (), state,
                             sock, "10.0.0.8")
        decoded = sock.calls[0][0]
        check("success receipt carries outcome",
              decoded[0] == "/os/rev" and decoded[2:] ==
              ["abc1234", "persistent", state.uid, "ok", "converged"], repr(decoded))
        check("reboot is requested after success receipt", power == ["reboot"], repr(power))

        power.clear()
        sock = ReplySocket()
        bopos.run_admin_verb(lambda *unused: {"status": "err", "phase": "pull"},
                             (), state, sock, "10.0.0.8")
        check("failed convergence does not reboot", not power, repr(power))
        check("failed convergence reports its phase", sock.calls[0][0][5:] == ["err", "pull"],
              repr(sock.calls))

        bopos.request_power_action = lambda action: False
        sock = ReplySocket()
        bopos.run_admin_verb(lambda *unused: {"status": "ok", "phase": "converged",
                                              "reboot": True}, (), state,
                             sock, "10.0.0.8")
        check("reboot rejection emits a second failure receipt",
              len(sock.calls) == 2 and sock.calls[1][0][5:] == ["err", "reboot"],
              repr(sock.calls))

        original_dir = bopos.BOPOS_DIR
        original_framework_command = bopos._framework_command
        original_converge = bopos.converge_framework
        original_send = bopos.send_to_engine
        with tempfile.TemporaryDirectory(prefix="bopos-trusted-checkout-") as temp:
            os.makedirs(os.path.join(temp, "patches"))
            os.makedirs(os.path.join(temp, "bash"))
            active = os.path.join(temp, "patches", "active_patch.txt")
            legacy = os.path.join(temp, "bash", "update.sh")
            marker = os.path.join(temp, "legacy-ran")
            with open(active, "w", encoding="utf-8") as target:
                target.write("stage-show\n")
            with open(legacy, "w", encoding="utf-8") as target:
                target.write("#!/bin/bash\n")
            calls = []

            def trusted_fake(argv, phase, timeout=None):
                calls.append((list(argv), phase))
                if phase == "restore":
                    with open(active, "w", encoding="utf-8") as target:
                        target.write("demo-pd\n")
                if phase == "checkout":
                    with open(legacy, "w", encoding="utf-8") as target:
                        target.write("#!/bin/bash\ntouch {!r}\n".format(marker))
                return None

            bopos.BOPOS_DIR = temp
            bopos._framework_command = trusted_fake
            outcome = bopos.converge_framework("release")
            argv = [entry[0] for entry in calls]
            check("checkout remains in trusted initiating code",
                  outcome.get("status") == "ok" and not os.path.exists(marker), repr(calls))
            check("checkout preserves active patch after branch replacement",
                  read(active).strip() == "stage-show")
            check("checkout validates branch syntax before fetch",
                  ["git", "check-ref-format", "--branch", "release"] in argv, repr(argv))
            check("checkout fetches an explicit remote tracking ref",
                  any(command[-1] ==
                      "+refs/heads/release:refs/remotes/origin/release"
                      for command in argv), repr(argv))
            check("checkout pins local branch to proven remote ref",
                  ["git", "checkout", "-B", "release",
                   "refs/remotes/origin/release"] in argv, repr(argv))
            check("checkout records the explicit upstream for later updates",
                  ["git", "branch", "--set-upstream-to=origin/release", "release"]
                  in argv, repr(argv))

            calls.clear()
            def invalid_path(argv, phase, timeout=None):
                calls.append((list(argv), phase))
                if phase == "branch":
                    return {"status": "err", "phase": "branch"}
                return None
            bopos._framework_command = invalid_path
            outcome = bopos.converge_framework("/tmp/not-a-branch")
            check("filesystem path cannot become a branch",
                  outcome == {"status": "err", "phase": "branch"})
            check("invalid branch stops before fetch",
                  not any(phase == "fetch" for _argv, phase in calls), repr(calls))
            check("invalid branch stops before restoring tracked files",
                  not any(phase == "restore" for _argv, phase in calls), repr(calls))

            calls.clear()
            def missing_remote(argv, phase, timeout=None):
                calls.append((list(argv), phase))
                if phase == "branch" and "show-ref" in argv:
                    return {"status": "err", "phase": "branch"}
                return None
            bopos._framework_command = missing_remote
            outcome = bopos.converge_framework("missing")
            check("missing remote branch is not reported as success",
                  outcome == {"status": "err", "phase": "branch"})
            check("missing remote branch is never checked out",
                  not any(phase == "checkout" for _argv, phase in calls), repr(calls))

            notifications = []
            bopos.converge_framework = lambda branch=None: {
                "status": "ok", "phase": "converged", "reboot": True}
            bopos.send_to_engine = lambda message: notifications.append(
                pyOSC3.decodeOSC(message.getBinary()))
            bopos.checkout_callback("", "", ["release"], "")
            check("checkout sends one notification without duplicate update notify",
                  len(notifications) == 1 and notifications[0][2:] == ["checkout"],
                  repr(notifications))

        bopos.BOPOS_DIR = original_dir
        bopos._framework_command = original_framework_command
        bopos.converge_framework = original_converge
        bopos.send_to_engine = original_send

        with tempfile.TemporaryDirectory(prefix="bopos-timeout-") as temp:
            os.makedirs(os.path.join(temp, "patches"))
            active = os.path.join(temp, "patches", "active_patch.txt")
            terminated = os.path.join(temp, "child-terminated")
            child_pid = os.path.join(temp, "child.pid")
            hang = os.path.join(temp, "hang.sh")
            with open(active, "w", encoding="utf-8") as target:
                target.write("stage-show\n")
            executable(hang, '''#!/bin/bash
"$PYTHON" -c 'import os,signal,sys,time
def stop(sig, frame):
    open(sys.argv[1], "w").write("terminated")
    raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
time.sleep(3)
open(sys.argv[2], "w").write("corrupted\\n")' "$TERM_MARK" "$ACTIVE_FILE" &
echo $! > "$CHILD_PID"
wait
''')
            original_dir = bopos.BOPOS_DIR
            original_framework_command = bopos._framework_command
            bopos.BOPOS_DIR = temp

            def timeout_fake(argv, phase, timeout=None):
                if phase == "authorization":
                    return None
                if phase == "restore":
                    with open(active, "w", encoding="utf-8") as target:
                        target.write("demo-pd\n")
                    return None
                if phase == "pull":
                    env = dict(os.environ, PYTHON=sys.executable, TERM_MARK=terminated,
                               ACTIVE_FILE=active, CHILD_PID=child_pid)
                    result = bopos._bounded_command(["bash", hang], temp, 0.25, env)
                    return {"status": "err", "phase": "pull-timeout"} \
                        if result["timed_out"] else None
                raise AssertionError("unexpected phase after timeout: " + phase)

            bopos._framework_command = timeout_fake
            sock = ReplySocket()
            bopos.run_admin_verb(lambda *unused: bopos.converge_framework(), (), state,
                                 sock, "10.0.0.8")
            check("timed-out Git process group receives termination",
                  read(terminated) == "terminated")
            check("Python restores active patch after timeout",
                  read(active).strip() == "stage-show", read(active))
            check("timeout receipt names the failing phase",
                  sock.calls and sock.calls[0][0][5:] == ["err", "pull-timeout"],
                  repr(sock.calls))
            available = bopos.admin_lock.acquire(blocking=False)
            check("admin lock releases only after timeout cleanup", available)
            if available:
                bopos.admin_lock.release()
            time.sleep(0.5)
            check("terminated descendant cannot mutate active patch later",
                  read(active).strip() == "stage-show", read(active))
            bopos.BOPOS_DIR = original_dir
            bopos._framework_command = original_framework_command
    finally:
        bopos.resolve_version = original_resolve
        bopos.request_power_action = original_power


def run_integration_source_checks():
    bridge = read(os.path.join(REPO, "dashboard", "osc_bridge.py"))
    simulator = read(os.path.join(REPO, "tools", "simfleet.py"))
    dashboard = read(os.path.join(REPO, "dashboard", "static", "js", "dashboard.js"))
    provision = read(os.path.join(REPO, "bash", "provision.sh"))
    check("dashboard retains optional status and phase",
          'receipt["status"] = str(args[3])' in bridge and
          'receipt["phase"] = str(args[4])' in bridge)
    check("dashboard does not reconcile an error receipt",
          'if receipt.get("status") == "err":' in bridge)
    check("selected Device detail exposes the terse update outcome",
          "d.rev.status" in dashboard and "d.rev.phase||'unknown'" in dashboard)
    check("simulator emits successful update outcome",
          'device, source, "ok", "converged"' in simulator)
    check("fresh provisioning requires root", 'provision.sh must run as root' in provision)
    check("fresh provisioning installs narrow power rule",
          '"$SCRIPT_DIR/install-power-control.sh"' in provision)
    check("fresh provisioning retains boot entry installation",
          '"$SCRIPT_DIR/rc.local" /etc/rc.local' in provision)
    check("custom SSH commands are forced into batch mode",
          'ssh_command += " -o BatchMode=yes"' in
          read(os.path.join(REPO, "python", "bopos.py")))


def free_port(kind):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def run_wire_integration():
    import websockets
    http_port = free_port(socket.SOCK_STREAM)
    report_port = free_port(socket.SOCK_DGRAM)
    command_port = free_port(socket.SOCK_DGRAM)
    temp = tempfile.mkdtemp(prefix="bopos-update-wire-")
    server = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard", "server.py"),
        "--port", str(http_port), "--listen-port", str(report_port),
        "--send-port", str(command_port), "--osc-target", "127.0.0.1",
        "--state-file", os.path.join(temp, "installation.json"),
    ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    fleet = subprocess.Popen([
        sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
        "--devices", "2", "--target", "127.0.0.1",
        "--report-port", str(report_port), "--cmd-port", str(command_port),
        "--hb-interval", "0.3", "--boot-secs", "0.5",
    ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ws = None
    try:
        for _ in range(50):
            try:
                ws = await websockets.connect("ws://127.0.0.1:{}/ws".format(http_port))
                break
            except OSError:
                await asyncio.sleep(0.1)
        check("wire integration connects", ws is not None)
        if ws is None:
            return
        devices = set()
        deadline = time.monotonic() + 8
        while len(devices) < 2 and time.monotonic() < deadline:
            message = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
            if message.get("type") == "device_update":
                devices.add(message["data"]["uid"])
        check("wire integration discovers simulated nodes", len(devices) == 2, repr(devices))
        await ws.send(json.dumps({"type": "action",
                                  "data": {"uid": "all", "verb": "updatebopos"}}))
        receipts = {}
        deadline = time.monotonic() + 8
        while len(receipts) < 2 and time.monotonic() < deadline:
            message = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
            if message.get("type") == "rev":
                device = message["data"]
                receipts[device["uid"]] = device.get("rev", {})
        check("wire integration exposes update outcomes", len(receipts) == 2 and
              all(item.get("status") == "ok" and item.get("phase") == "converged"
                  for item in receipts.values()), repr(receipts))
    finally:
        if ws is not None:
            await ws.close()
        fleet.terminate()
        server.terminate()
        fleet.wait(timeout=5)
        server.wait(timeout=5)
        shutil.rmtree(temp)


if __name__ == "__main__":
    run_shell_checks()
    run_python_checks()
    run_integration_source_checks()
    asyncio.run(run_wire_integration())
    if FAILURES:
        raise SystemExit("{} checks failed: {}".format(len(FAILURES), ", ".join(FAILURES)))
    print("All 50 unattended update checks passed.")
