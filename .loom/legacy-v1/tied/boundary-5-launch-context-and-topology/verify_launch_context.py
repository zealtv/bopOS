#!/usr/bin/env python3
"""Verify the bopOS-owned launch context (runcontext.py) and the shared
provided-term shaping (relay.py) used by both helper.py and audition.py,
plus their launcher/template wiring (engine-boundary ratification, 2026-07-12).
"""
import importlib.util
import os
import py_compile
import re
import socket
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {label}")
    else:
        FAIL += 1
        print(f"[FAIL] {label}")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. runcontext.generate
# ---------------------------------------------------------------------------

import runcontext  # noqa: E402

RUN_ID_RE = re.compile(r"^default-\d{8}-\d{6}-\d{6}$")
SAFE_CHARS_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def test_runcontext_generate():
    ctx = runcontext.generate(patch="default")
    check("seed is int in [0, 999999]",
          isinstance(ctx["seed"], int) and 0 <= ctx["seed"] <= 999999)
    check("run_id matches ^default-YYYYMMDD-HHMMSS-NNNNNN$",
          bool(RUN_ID_RE.match(ctx["run_id"])))
    suffix = ctx["run_id"].rsplit("-", 1)[-1]
    check("run_id suffix equals seed zero-padded to 6 digits",
          suffix == f"{ctx['seed']:06d}")

    no_patch_ctx = runcontext.generate(patch=None)
    check("patchless run_id has no prefix (starts with a digit)",
          re.match(r"^\d{8}-\d{6}-\d{6}$", no_patch_ctx["run_id"]) is not None)

    weird_ctx = runcontext.generate(patch="my patch!/x")
    check("weird patch name yields a run_id using only safe characters",
          bool(SAFE_CHARS_RE.match(weird_ctx["run_id"])))

    seeds = {runcontext.generate(patch="default")["seed"] for _ in range(5)}
    check("5 calls to generate() give >=2 distinct seeds", len(seeds) >= 2)


def test_runcontext_cli():
    result = subprocess.run(
        [sys.executable, os.path.join(REPO, "python", "runcontext.py"), "default"],
        capture_output=True, text=True, timeout=10,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    check("runcontext CLI prints exactly two lines", len(lines) == 2)
    line_re = re.compile(r"^BOPOS_(SEED|RUN_ID)='[A-Za-z0-9_.-]+'$")
    check("both CLI lines match BOPOS_(SEED|RUN_ID)='...'",
          len(lines) == 2 and all(line_re.match(line) for line in lines))

    eval_cmd = (
        f'eval "$({sys.executable} {os.path.join(REPO, "python", "runcontext.py")} '
        f'default)"; echo "$BOPOS_SEED|$BOPOS_RUN_ID"'
    )
    eval_result = subprocess.run(
        ["bash", "-c", eval_cmd], capture_output=True, text=True, timeout=10,
    )
    out = eval_result.stdout.strip()
    parts = out.split("|", 1)
    check("CLI output is eval-able into non-empty BOPOS_SEED and BOPOS_RUN_ID",
          len(parts) == 2 and parts[0] != "" and parts[1] != "")


# ---------------------------------------------------------------------------
# 2. relay.shape_provided_term
# ---------------------------------------------------------------------------

import relay  # noqa: E402


def test_relay_shape_provided_term():
    check("master term shaped and truncated to first arg",
          relay.shape_provided_term(["all", "os", "master"], [0.5, 9])
          == ("/os/master", [0.5]))
    check("param term shaped with all args",
          relay.shape_provided_term(["2", "p", "gain"], [0.7, 0.3])
          == ("/p/gain", [0.7, 0.3]))
    check("os/mute is not a provided term",
          relay.shape_provided_term(["all", "os", "mute"], [1]) is None)
    check("os/identify is not a provided term",
          relay.shape_provided_term(["all", "os", "identify"], []) is None)
    check("2-part sync/ping address is not a provided term",
          relay.shape_provided_term(["all", "sync", "ping"][:2], [1]) is None)
    check("sync/ping (2 parts total) is not a provided term",
          relay.shape_provided_term(["sync", "ping"], [1]) is None)
    check("4-part address is not a provided term",
          relay.shape_provided_term(["all", "p", "gain", "extra"], [1]) is None)
    check("empty args is not a provided term",
          relay.shape_provided_term(["all", "os", "master"], []) is None)
    check("empty param name is not a provided term",
          relay.shape_provided_term(["all", "p", ""], [1]) is None)


# ---------------------------------------------------------------------------
# 3. helper.py source: uses shared relay.shape_provided_term
# ---------------------------------------------------------------------------

def test_helper_uses_shared_relay():
    with open(os.path.join(REPO, "python", "bopos.py")) as source:
        text = source.read()
    check("helper.py imports relay", "import relay" in text)
    check("helper.py calls relay.shape_provided_term", "shape_provided_term" in text)
    check("helper.py no longer inline-shapes '/p/' + parts[2]",
          '"/p/" + parts[2]' not in text and "'/p/' + parts[2]" not in text)


# ---------------------------------------------------------------------------
# 4. audition runtime (no engines) — relay behavior end to end
# ---------------------------------------------------------------------------

def recv_or_none(sock, timeout=1.5):
    sock.settimeout(timeout)
    try:
        return sock.recvfrom(65535)[0]
    except socket.timeout:
        return None


def drain(sock, timeout=0.3):
    sock.settimeout(timeout)
    try:
        while True:
            sock.recvfrom(65535)
    except socket.timeout:
        pass


def test_audition_runtime():
    from pythonosc import osc_message, osc_message_builder

    audition = load_module("audition_launch_context_verify",
                            os.path.join(REPO, "tools", "audition.py"))

    engine_ports = [36661, 36662, 36663]
    engines = []
    try:
        for port in engine_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", port))
            sock.settimeout(1.5)
            engines.append(sock)
    except OSError as error:
        check(f"could bind fake engine sockets ({error})", False)
        for sock in engines:
            sock.close()
        return

    args = audition.parse_args([
        "--devices", "3", "--no-engine",
        "--cmd-port", "26660", "--report-port", "25550",
        "--engine-host", "127.0.0.1", "--engine-port-base", "36661",
        "--target", "127.0.0.1", "--bind", "127.0.0.1",
        "--catchup-secs", "0.2", "--hb-interval", "5",
    ])
    rig = audition.AuditionRig(args)
    thread = threading.Thread(target=rig.run, daemon=True)
    thread.start()

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(address, *osc_args):
        builder = osc_message_builder.OscMessageBuilder(address=address)
        for value in osc_args:
            builder.add_arg(value)
        sender.sendto(builder.build().dgram, ("127.0.0.1", 26660))

    def decode(datagram):
        message = osc_message.OscMessage(datagram)
        return message.address, list(message.params)

    def approx_eq(actual, expected):
        # OSC floats are 32-bit; args round-trip through single precision.
        if actual is None or expected is None:
            return actual == expected
        if len(actual) != 2 or actual[0] != expected[0]:
            return False
        a_args, e_args = actual[1], expected[1]
        if len(a_args) != len(e_args):
            return False
        for a, e in zip(a_args, e_args):
            if isinstance(e, float):
                if abs(a - e) > 1e-5:
                    return False
            elif a != e:
                return False
        return True

    try:
        # catch-up /id per node, ids 1,2,3
        id_msgs = []
        for sock in engines:
            datagram = recv_or_none(sock, timeout=2.0)
            id_msgs.append(decode(datagram) if datagram else None)
        check("catch-up /id arrives at all three fake engines",
              all(msg is not None for msg in id_msgs))
        check("catch-up /id carries the right device ids (1,2,3)",
              id_msgs == [("/id", [1]), ("/id", [2]), ("/id", [3])])

        for sock in engines:
            drain(sock)

        # /all/os/master 0.5 -> all three get /os/master [0.5]
        send("/all/os/master", 0.5)
        results = []
        for sock in engines:
            datagram = recv_or_none(sock)
            results.append(decode(datagram) if datagram else None)
        check("/all/os/master relays /os/master [0.5] to all three engines",
              all(approx_eq(r, ("/os/master", [0.5])) for r in results))
        for sock in engines:
            drain(sock)

        # /2/p/gain 0.7 -> only node id 2 (second engine)
        send("/2/p/gain", 0.7)
        got = [recv_or_none(sock, timeout=0.6) for sock in engines]
        decoded = [decode(d) if d else None for d in got]
        expected = [None, ("/p/gain", [0.7]), None]
        check("/2/p/gain relays only to device id 2 (second engine)",
              all(approx_eq(a, e) for a, e in zip(decoded, expected)))
        for sock in engines:
            drain(sock)

        # /all/os/identify (no args) -> all three get /notify ["identify"]
        send("/all/os/identify")
        got = [recv_or_none(sock) for sock in engines]
        decoded = [decode(d) if d else None for d in got]
        check("/all/os/identify (no uid) relays /notify [identify] to all three",
              decoded == [("/notify", ["identify"])] * 3)
        for sock in engines:
            drain(sock)

        # /all/os/identify "audition-0001" -> only first engine
        send("/all/os/identify", "audition-0001")
        got = [recv_or_none(sock, timeout=0.6) for sock in engines]
        decoded = [decode(d) if d else None for d in got]
        check("/all/os/identify with uid relays only to the matching node",
              decoded == [("/notify", ["identify"]), None, None])
        for sock in engines:
            drain(sock)

        # /all/os/mute 1 -> no engine receives anything
        send("/all/os/mute", 1)
        got = [recv_or_none(sock, timeout=0.6) for sock in engines]
        check("/all/os/mute is not relayed to any engine",
              all(datagram is None for datagram in got))
    finally:
        rig.running = False
        thread.join(timeout=4)
        sender.close()
        for sock in engines:
            sock.close()


# ---------------------------------------------------------------------------
# 5. audition.engine_command PD startup -send string
# ---------------------------------------------------------------------------

def test_engine_command_send_string():
    audition = load_module("audition_launch_context_verify2",
                            os.path.join(REPO, "tools", "audition.py"))
    patch_dir = os.path.join(REPO, "patches", "demo-pd")
    loaded, error = audition.patch_manifest.load(patch_dir)
    check("demo-pd manifest loads", error is None and loaded is not None)
    if loaded is None:
        return

    args = audition.parse_args(["--devices", "1", "--engine", "pd"])
    rig = object.__new__(audition.AuditionRig)
    rig.args = args
    node = audition.VirtualNode(0, 1, "audition-0001", 36661)
    command = rig.engine_command(node, patch_dir, loaded)
    send_index = command.index("-send") + 1
    send_string = command[send_index]

    for token in ("BOPOS_ENGINE_PORT", "bopos-context seed ", "bopos-context run-id ",
                  "bopos-context patch demo-pd", "bopos-context assets "):
        check(f"-send string contains {token!r}", token in send_string)
    for legacy in (" ID ", "RANDOM", "STARTTIME", "STARTDATE", "ACTIVEPATCH", "; ASSETS"):
        check(f"-send string does not contain legacy token {legacy!r}",
              legacy not in send_string)


# ---------------------------------------------------------------------------
# 6. bash launchers
# ---------------------------------------------------------------------------

def test_bash_launchers():
    for script in ("start-engine.sh", "start-laptop.sh"):
        path = os.path.join(REPO, "bash", script)
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        check(f"bash -n {script} succeeds", result.returncode == 0)

    with open(os.path.join(REPO, "bash", "start-engine.sh")) as source:
        engine_text = source.read()
    for token in ("runcontext.py", "bopos-context seed", "BOPOS_RUN_ID",
                  'BOPOS_ENGINE_PORT="${BOPOS_ENGINE_PORT:-6661}"'):
        check(f"start-engine.sh contains {token!r}", token in engine_text)
    for legacy in ("RANDOM $RND", "STARTDATE", "BOPOS_RANDOM"):
        check(f"start-engine.sh does not contain {legacy!r}", legacy not in engine_text)

    with open(os.path.join(REPO, "bash", "start-laptop.sh")) as source:
        laptop_text = source.read()
    for token in ("runcontext.py", "bopos-context"):
        check(f"start-laptop.sh contains {token!r}", token in laptop_text)
    for legacy in ("RANDOM $RND", "STARTDATE"):
        check(f"start-laptop.sh does not contain {legacy!r}", legacy not in laptop_text)


# ---------------------------------------------------------------------------
# 7. main.scd template
# ---------------------------------------------------------------------------

def test_main_scd():
    path = os.path.join(REPO, "patches", "demo-sc", "main.scd")
    with open(path) as source:
        text = source.read()
    for token in ('"BOPOS_ENGINE_PORT".getenv', "openUDPPort",
                  "recvPort: ~bopos.enginePort", "while", "sendMsg('/config'", "2.wait",
                  "BOPOS_SEED", "BOPOS_RUN_ID", "BOPOS_ACTIVEPATCH", "BOPOS_ASSETS"):
        check(f"main.scd contains {token!r}", token in text)
    check("main.scd does not hardcode recvPort: 6661", "recvPort: 6661" not in text)


# ---------------------------------------------------------------------------
# 8. py_compile
# ---------------------------------------------------------------------------

def test_py_compile():
    for relative in ("python/runcontext.py", "python/relay.py", "python/bopos.py",
                      "tools/audition.py"):
        path = os.path.join(REPO, relative)
        try:
            py_compile.compile(path, doraise=True,
                                cfile=os.path.join("/tmp", "bopos-pycache-check.pyc"))
            ok = True
        except py_compile.PyCompileError:
            ok = False
        check(f"py_compile succeeds for {relative}", ok)


def main():
    test_runcontext_generate()
    test_runcontext_cli()
    test_relay_shape_provided_term()
    test_helper_uses_shared_relay()
    test_audition_runtime()
    test_engine_command_send_string()
    test_bash_launchers()
    test_main_scd()
    test_py_compile()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
