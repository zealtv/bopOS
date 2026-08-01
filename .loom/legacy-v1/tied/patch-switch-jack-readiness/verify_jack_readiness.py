#!/usr/bin/env python3
"""Focused regression checks for the JACK/engine lifecycle."""

import json
import os
import shutil
import shlex
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    REPO = os.path.dirname(REPO)
sys.path[:0] = [os.path.join(REPO, "python"), os.path.join(REPO, "python", "io")]

import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        pass

    def addMsgHandler(self, _address, _callback):
        pass

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["bopos.py", "unknown"]
import bopos  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def executable(path, text):
    with open(path, "w", encoding="utf-8") as target:
        target.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


def lifecycle_fixture(root):
    for directory in ("bash", "python", "run", "bin", "patches/test/bop/samplepacks"):
        os.makedirs(os.path.join(root, directory), exist_ok=True)
    for relative in ("bash/start-engine.sh", "bash/stop-engine.sh",
                     "python/manifest.py", "python/runcontext.py"):
        shutil.copy2(os.path.join(REPO, relative), os.path.join(root, relative))
    with open(os.path.join(root, "patches", "active_patch.txt"), "w", encoding="utf-8") as target:
        target.write("test\n")
    with open(os.path.join(root, "patches", "test", "main.bin"), "w", encoding="utf-8") as target:
        target.write("test\n")
    engine = os.path.join(root, "bin", "fakeengine")
    executable(engine, "#!/bin/bash\ntouch \"$ENGINE_STARTED\"\nexec sleep 60\n")
    manifest = {"engine": engine, "entrypoint": "main.bin", "params": [],
                "caps": [], "slots": []}
    with open(os.path.join(root, "patches", "test", "bopos.patch.json"),
              "w", encoding="utf-8") as target:
        json.dump(manifest, target)
    ready_path = shlex.quote(os.path.join(root, "jack.ready"))
    executable(os.path.join(root, "bin", "jackd"), """#!/bin/bash
if [ "$FAKE_JACK_MODE" = "exit" ]; then exit 1; fi
if [ "$FAKE_JACK_MODE" = "ready" ]; then touch %s; fi
exec sleep 60
""" % ready_path)
    executable(os.path.join(root, "bin", "jack_lsp"),
               "#!/bin/bash\n[ -f %s ]\n" % ready_path)


def run_start(root, mode):
    env = os.environ.copy()
    env.update({
        "PATH": os.path.join(root, "bin") + os.pathsep + env["PATH"],
        "FAKE_JACK_MODE": mode,
        "JACK_READY": os.path.join(root, "jack.ready"),
        "ENGINE_STARTED": os.path.join(root, "engine.started"),
        "BOPOS_JACK_START_TIMEOUT": "1",
        "BOPOS_STOP_TIMEOUT": "1",
    })
    result = subprocess.run(["bash", os.path.join(root, "bash", "start-engine.sh")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=10)
    return result, env


def shell_lifecycle_checks():
    with tempfile.TemporaryDirectory() as root:
        lifecycle_fixture(root)
        result, _env = run_start(root, "exit")
        check("launcher fails when JACK exits during startup",
              result.returncode != 0 and not os.path.exists(os.path.join(root, "engine.started")),
              "return code {}".format(result.returncode))
        check("failed JACK launch leaves no success pid marker",
              not os.path.exists(os.path.join(root, "run", "jackd.pid")))

    with tempfile.TemporaryDirectory() as root:
        lifecycle_fixture(root)
        result, _env = run_start(root, "unready")
        check("launcher times out rather than starting an engine without JACK",
              result.returncode != 0 and not os.path.exists(os.path.join(root, "engine.started")),
              "return code {}".format(result.returncode))

    with tempfile.TemporaryDirectory() as root:
        lifecycle_fixture(root)
        result, env = run_start(root, "ready")
        engine_pid_path = os.path.join(root, "run", "engine.pid")
        jack_pid_path = os.path.join(root, "run", "jackd.pid")
        check("ready JACK permits engine launch",
              result.returncode == 0 and os.path.exists(engine_pid_path)
              and os.path.exists(jack_pid_path), "return code {}".format(result.returncode))
        launched_pids = []
        for pid_path in (engine_pid_path, jack_pid_path):
            with open(pid_path, encoding="utf-8") as source:
                launched_pids.append(int(source.read().strip()))
        stopped = subprocess.run(["bash", os.path.join(root, "bash", "stop-engine.sh")],
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, timeout=10)
        pids_gone = not any(os.path.exists(path) for path in (engine_pid_path, jack_pid_path))
        for pid in launched_pids:
            try:
                os.kill(pid, 0)
                pids_gone = False
            except ProcessLookupError:
                pass
        check("stop lifecycle waits for and clears engine and JACK",
              stopped.returncode == 0 and pids_gone, stopped.stdout)


def node_health_checks():
    old_dir, old_proc = bopos.BOPOS_DIR, bopos.PROC_DIR
    try:
        with tempfile.TemporaryDirectory() as root:
            run = os.path.join(root, "run")
            proc = os.path.join(root, "proc")
            os.makedirs(run)
            os.makedirs(os.path.join(proc, "101"))
            os.makedirs(os.path.join(proc, "202"))
            with open(os.path.join(run, "engine.name"), "w", encoding="utf-8") as target:
                target.write("pd\n")
            with open(os.path.join(run, "engine.pid"), "w", encoding="utf-8") as target:
                target.write("101\n")
            with open(os.path.join(run, "pd.pid"), "w", encoding="utf-8") as target:
                target.write("101\n")
            with open(os.path.join(proc, "101", "comm"), "w", encoding="utf-8") as target:
                target.write("pd\n")
            bopos.BOPOS_DIR, bopos.PROC_DIR = root, proc
            check("surviving PD is unhealthy when JACK is absent", bopos.engine_alive() == 0)
            with open(os.path.join(run, "jackd.pid"), "w", encoding="utf-8") as target:
                target.write("202\n")
            with open(os.path.join(proc, "202", "comm"), "w", encoding="utf-8") as target:
                target.write("jackd\n")
            check("heartbeat health requires both JACK and the engine",
                  bopos.engine_alive() == 1)
    finally:
        bopos.BOPOS_DIR, bopos.PROC_DIR = old_dir, old_proc


def main():
    shell_lifecycle_checks()
    node_health_checks()
    total = 7
    print("\n{}/{} passed".format(total - len(FAILURES), total))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
