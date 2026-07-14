#!/usr/bin/env python3
"""Browser-free acceptance test for tools/audition.py."""

import json
import importlib.util
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

from pythonosc import osc_message, osc_message_builder


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
AUDITION = ROOT / "tools" / "audition.py"


def load_audition_module():
    spec = importlib.util.spec_from_file_location("audition_under_test", AUDITION)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def udp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(2)
    return sock


def free_udp_port():
    sock = udp_socket()
    port = sock.getsockname()[1]
    sock.close()
    return port


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def receive(sock):
    message = osc_message.OscMessage(sock.recvfrom(65535)[0])
    return message.address, list(message.params)


def wait_for(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.03)
    return False


def process_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def no_engine_protocol_test():
    reports = udp_socket()
    command_port = free_udp_port()
    engines = [udp_socket() for _ in range(3)]
    base = engines[0].getsockname()[1]
    # Reserve a deterministic contiguous range rather than assuming ephemeral
    # allocation happens to be adjacent.
    for sock in engines:
        sock.close()
    engines = []
    while True:
        try:
            for offset in range(3):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("127.0.0.1", base + offset))
                sock.settimeout(0.35)
                engines.append(sock)
            break
        except OSError:
            for sock in engines:
                sock.close()
            engines = []
            base += 3

    proc = subprocess.Popen([
        sys.executable, str(AUDITION), "--devices", "3", "--no-engine",
        "--bind", "127.0.0.1", "--target", "127.0.0.1",
        "--report-port", str(reports.getsockname()[1]),
        "--cmd-port", str(command_port),
        "--engine-port-base", str(base), "--hb-interval", "0.2",
        "--catchup-secs", "0.15",
    ])
    try:
        heartbeats = [receive(reports) for _ in range(3)]
        assert all(address == "/hb" for address, _args in heartbeats)
        assert {args[0] for _address, args in heartbeats} == {
            "audition-0001", "audition-0002", "audition-0003"
        }
        assert {args[1] for _address, args in heartbeats} == {1, 2, 3}
        assert all(args[3] == 0 for _address, args in heartbeats)

        assert [receive(sock) for sock in engines] == [
            ("/id", [1]), ("/id", [2]), ("/id", [3])
        ]

        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.sendto(packet("/all/p/gain", 0.25), ("127.0.0.1", command_port))
        assert [receive(sock) for sock in engines] == [
            ("/p/gain", [0.25]), ("/p/gain", [0.25]), ("/p/gain", [0.25])
        ]

        sender.sendto(packet("/2/os/master", 1), ("127.0.0.1", command_port))
        assert receive(engines[1]) == ("/os/master", [1])
        for index in (0, 2):
            try:
                receive(engines[index])
                raise AssertionError("exact-id command leaked to another engine")
            except socket.timeout:
                pass

        sender.sendto(packet("/999/p/gain", 0.9), ("127.0.0.1", command_port))
        for sock in engines:
            try:
                receive(sock)
                raise AssertionError("unmatched selector was forwarded")
            except socket.timeout:
                pass

        sender.sendto(packet("/all/sync/offset", "12"), ("127.0.0.1", command_port))
        sender.sendto(packet("/1/os/provision", 4), ("127.0.0.1", command_port))
        sender.sendto(packet("/all/pt", "point", 0.5, 0.5),
                      ("127.0.0.1", command_port))
        for sock in engines:
            try:
                receive(sock)
                raise AssertionError("non-Stage-0 framework traffic was forwarded")
            except socket.timeout:
                pass
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=4)
        reports.close()
        for sock in engines:
            sock.close()
    assert proc.returncode == 0


def owned_process_test():
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        (temp_path / "entry.fake").write_text("fixture\n")
        (temp_path / "bopos.patch.json").write_text(json.dumps({
            "engine": "fake", "entrypoint": "entry.fake", "params": []
        }))
        fake = temp_path / "fake_engine.py"
        fake.write_text(
            "import os, pathlib, signal, subprocess, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "base=pathlib.Path(os.environ['PID_DIR'], os.environ['BOPOS_AUDITION_ID'])\n"
            "base.with_name(base.name + '-parent').write_text(str(os.getpid()))\n"
            "code='import os,pathlib,signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "pathlib.Path(os.environ[\"CHILD_PID\"]).write_text(str(os.getpid())); time.sleep(30)'\n"
            "child_env=os.environ.copy(); child_env['CHILD_PID']=str(base.with_name(base.name + '-child'))\n"
            "subprocess.Popen([sys.executable, '-c', code], env=child_env)\n"
            "while True: time.sleep(1)\n"
        )
        reports = udp_socket()
        command_port = free_udp_port()
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        env = os.environ.copy()
        env["PID_DIR"] = temp
        proc = subprocess.Popen([
            sys.executable, str(AUDITION), "--devices", "2",
            "--bind", "127.0.0.1", "--target", "127.0.0.1",
            "--report-port", str(reports.getsockname()[1]), "--cmd-port", str(command_port),
            "--manifest", str(temp_path / "bopos.patch.json"),
            "--engine-command", f"{sys.executable} {fake} {{entrypoint}}",
            "--catchup-secs", "10", "--stop-timeout", "0.2",
        ], env=env)
        try:
            pid_files = [temp_path / f"{device_id}-{kind}"
                         for device_id in (1, 2) for kind in ("parent", "child")]
            assert wait_for(lambda: all(path.exists() for path in pid_files))
            child_pids = [int(path.read_text()) for path in pid_files]
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=4)
            assert wait_for(lambda: not any(process_exists(pid) for pid in child_pids))
            assert unrelated.poll() is None, "launcher stopped an unrelated process"
        finally:
            if proc.poll() is None:
                proc.kill()
            unrelated.terminate()
            unrelated.wait(timeout=2)
            reports.close()
        assert proc.returncode == 0


def pd_command_test():
    audition = load_audition_module()
    args = audition.parse_args(["--devices", "2", "--audio-backend", "coreaudio"])
    rig = object.__new__(audition.AuditionRig)
    rig.args = args
    patch_dir = ROOT / "patches" / "demo-pd"
    loaded, error = audition.patch_manifest.load(str(patch_dir))
    assert error is None
    nodes = [
        audition.VirtualNode(0, 1, "audition-0001", 16661),
        audition.VirtualNode(1, 2, "audition-0002", 16662),
    ]
    commands = [rig.engine_command(node, str(patch_dir), loaded) for node in nodes]
    assert all("-pa" in command for command in commands)
    sends = [command[command.index("-send") + 1] for command in commands]
    assert "BOPOS_ENGINE_PORT 16661" in sends[0] and "ID 1" in sends[0]
    assert "BOPOS_ENGINE_PORT 16662" in sends[1] and "ID 2" in sends[1]
    assert sends[0] != sends[1]
    args.engine_command = "engine {unknown}"
    try:
        rig.engine_command(nodes[0], str(patch_dir), loaded)
        raise AssertionError("unknown command placeholder was accepted")
    except ValueError as error:
        assert "unknown --engine-command placeholder" in str(error)


def exclusive_bind_test():
    reports = udp_socket()
    owner = udp_socket()
    result = subprocess.run([
        sys.executable, str(AUDITION), "--devices", "1", "--no-engine",
        "--bind", "127.0.0.1", "--target", "127.0.0.1",
        "--report-port", str(reports.getsockname()[1]),
        "--cmd-port", str(owner.getsockname()[1]),
    ], capture_output=True, text=True, timeout=3)
    owner.close()
    reports.close()
    assert result.returncode != 0
    assert "Address already in use" in result.stderr


def partial_start_failure_test():
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        (temp_path / "entry.fake").write_text("fixture\n")
        manifest_path = temp_path / "bopos.patch.json"
        manifest_path.write_text(json.dumps({
            "engine": "fake", "entrypoint": "entry.fake", "params": []
        }))
        first = temp_path / "engine-1"
        first.write_text(
            "#!/usr/bin/env python3\n"
            "import signal,time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(30)\n"
        )
        first.chmod(0o755)
        reports = udp_socket()
        command_port = free_udp_port()
        result = subprocess.run([
            sys.executable, str(AUDITION), "--devices", "2",
            "--bind", "127.0.0.1", "--target", "127.0.0.1",
            "--report-port", str(reports.getsockname()[1]),
            "--cmd-port", str(command_port), "--manifest", str(manifest_path),
            "--engine-command", str(temp_path / "engine-{id}"),
            "--stop-timeout", "0.2",
        ], capture_output=True, text=True, timeout=4)
        reports.close()
        assert result.returncode != 0 and "engine-2" in result.stderr
        first_line = next(line for line in result.stdout.splitlines() if "id=1" in line)
        first_pid = int(first_line.rsplit("pid=", 1)[1])
        assert wait_for(lambda: not process_exists(first_pid))
        rebound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rebound.bind(("127.0.0.1", command_port))
        rebound.close()


def main():
    pd_command_test()
    exclusive_bind_test()
    partial_start_failure_test()
    no_engine_protocol_test()
    owned_process_test()
    print("PASS: heartbeats, selector relay, /id catch-up, and owned teardown")


if __name__ == "__main__":
    main()
