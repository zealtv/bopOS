#!/usr/bin/env python3
"""Real-sclang smoke test for the SC starter (requires SuperCollider + JACK)."""
import os
import signal
import math
import re
import shutil
import subprocess
import sys
import threading
import time

from pythonosc.udp_client import SimpleUDPClient


HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

ENTRYPOINT = os.path.join(REPO, "patches", "demo-sc", "main.scd")


def main():
    sclang = shutil.which("sclang")
    if not sclang:
        print("SKIP: sclang is not installed")
        return 2

    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    process = subprocess.Popen(
        [sclang, "-D", ENTRYPOINT], cwd=REPO, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        bufsize=1, start_new_session=True)
    lines = []

    def read_output():
        for line in process.stdout:
            lines.append(line)
            print(line, end="")

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            text = "".join(lines)
            if "bopOS SuperCollider demo ready" in text:
                break
            if process.poll() is not None:
                raise RuntimeError("sclang exited before template ready")
            time.sleep(0.1)
        else:
            raise RuntimeError("template did not become ready within 20 seconds")

        local = SimpleUDPClient("127.0.0.1", 6661)
        local.send_message("/id", 7)
        local.send_message("/p/gain", 0.2)
        local.send_message("/p/frequency", 330.0)
        local.send_message("/os/master", 0.1)
        local.send_message("/pt", [0, 0, 0.1])
        local.send_message("/pt", [0, 1, 0.1])
        local.send_message("/cue", "ping")

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            text = "".join(lines)
            if ("bopOS device id: 7" in text and "bopOS cue: ping" in text
                    and "ping state master=" in text):
                break
            time.sleep(0.1)
        text = "".join(lines)
        match = re.search(
            r"ping state master=([0-9.eE+-]+) gain=([0-9.eE+-]+) frequency=([0-9.eE+-]+)",
            text)
        relayed_state = (match is not None
                         and math.isclose(float(match.group(1)), 0.1, rel_tol=1e-6)
                         and math.isclose(float(match.group(2)), 0.2, rel_tol=1e-6)
                         and math.isclose(float(match.group(3)), 330.0, rel_tol=1e-6))
        checks = {
            "scsynth server ready": "SuperCollider 3 server ready" in text,
            "demo startup reached": "bopOS SuperCollider demo ready" in text,
            "identity OSC received": "bopOS device id: 7" in text,
            "scheduled cue OSC received": "bopOS cue: ping" in text,
            "helper-relayed local state reached SC": relayed_state,
            "no language error before teardown": "ERROR:" not in text,
        }
        for label, passed in checks.items():
            print("[{}] {}".format("PASS" if passed else "FAIL", label))
        return 0 if all(checks.values()) else 1
    except Exception as error:
        print("FAIL:", error)
        return 1
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        reader.join(timeout=1)


if __name__ == "__main__":
    raise SystemExit(main())
