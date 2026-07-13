#!/usr/bin/env python3
"""Interactive, owned-process three-engine audition gate for macOS/Linux.

This harness proves readiness and clean teardown, then leaves the audible
judgment to the operator. It never edits PD patches or claims an audio result.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

import websockets


sys.dont_write_bytecode = True


def repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "python"))
import manifest as patch_manifest  # noqa: E402

AUDITION = ROOT / "tools" / "audition.py"
DASHBOARD = ROOT / "dashboard" / "server.py"
DEFAULT_MANIFEST = ROOT / "patches" / "default" / "bopos.patch.json"
EXPECTED_UIDS = {"audition-0001", "audition-0002", "audition-0003"}
SEEDED_POSITIONS = {
    "audition-0001": [2.0, 3.5],
    "audition-0002": [5.0, 1.5],
    "audition-0003": [8.0, 3.5],
}
PID_LINE = re.compile(r"audition: id=(\d+) port=(\d+) pid=(\d+)")
FATAL_LOG_MARKERS = (
    "oscparse: no such object",
    "bopos_engine_port: no such object",
    "audio device open failed",
    "couldn't open audio",
    "could not open audio",
    "failed to open audio",
    "portaudio error",
    "jack server is not running",
    "jack_client_open() failed",
    "cannot connect to jack server",
    "audio i/o stuck",
)


class GateSignal(BaseException):
    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


def default_pd_bin():
    if sys.platform == "darwin":
        return "/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd"
    return "pd"


def default_backend():
    return "coreaudio" if sys.platform == "darwin" else "jack"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http-port", type=int, default=18098)
    parser.add_argument("--report-port", type=int, default=15558)
    parser.add_argument("--cmd-port", type=int, default=16668)
    parser.add_argument("--engine-port-base", type=int, default=17671)
    parser.add_argument("--pd-bin", default=default_pd_bin())
    parser.add_argument("--audio-backend", choices=("coreaudio", "jack", "none"),
                        default=default_backend())
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--startup-timeout", type=float, default=20.0)
    parser.add_argument("--stop-timeout", type=float, default=8.0)
    parser.add_argument("--results-dir",
                        help="persistent output directory (default: a new /tmp directory)")
    parser.add_argument("--no-engine", action="store_true",
                        help="prove dashboard/relay/state/port lifecycle without launching PD")
    parser.add_argument("--allow-existing-pd", action="store_true",
                        help="continue despite an existing process named pd")
    args = parser.parse_args(argv)
    ports = [args.http_port, args.report_port, args.cmd_port,
             *range(args.engine_port_base, args.engine_port_base + 3)]
    if any(port < 1 or port > 65535 for port in ports) or len(set(ports)) != len(ports):
        parser.error("all HTTP/OSC/engine ports must be distinct valid ports")
    if args.startup_timeout <= 0 or args.stop_timeout <= 0:
        parser.error("timeouts must be positive")
    return args


def tcp_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def udp_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def tcp_listening(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.2)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def process_named_pd():
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        return set()
    result = subprocess.run([pgrep, "-x", "pd"], capture_output=True, text=True)
    return {int(line) for line in result.stdout.splitlines() if line.strip().isdigit()}


def process_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def wait_pids_gone(pids, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(process_exists(pid) for pid in pids):
            return True
        time.sleep(0.1)
    return not any(process_exists(pid) for pid in pids)


def resolve_executable(value):
    if os.path.sep in value:
        path = Path(value).expanduser().resolve()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which(value)


def preflight(args):
    if sys.platform not in ("darwin", "linux"):
        raise RuntimeError("audible gate supports only macOS and Linux")
    pd_bin = resolve_executable(args.pd_bin)
    if pd_bin is None and not args.no_engine:
        raise RuntimeError(f"PD executable not found or not executable: {args.pd_bin}")
    if pd_bin is None:
        pd_bin = args.pd_bin  # parsed but unused by tools/audition.py --no-engine
    manifest = Path(args.manifest).expanduser().resolve()
    if manifest.name != "bopos.patch.json" or not manifest.is_file():
        raise RuntimeError(f"manifest not found: {manifest}")
    loaded, error = patch_manifest.load(str(manifest.parent))
    if loaded is None:
        raise RuntimeError(f"invalid manifest: {error}")
    if loaded["engine"] != "pd":
        raise RuntimeError(
            f"audible PD gate requires manifest engine 'pd', got {loaded['engine']!r}"
        )
    if not tcp_available(args.http_port):
        raise RuntimeError(f"HTTP port {args.http_port} is already in use")
    for port in (args.report_port, args.cmd_port,
                 *range(args.engine_port_base, args.engine_port_base + 3)):
        if not udp_available(port):
            raise RuntimeError(f"UDP port {port} is already in use")
    existing = process_named_pd()
    if existing and not args.allow_existing_pd and not args.no_engine:
        raise RuntimeError(
            "existing PD process(es) detected (PIDs {}); stop them or explicitly pass "
            "--allow-existing-pd".format(", ".join(str(pid) for pid in sorted(existing)))
        )
    return pd_bin, manifest, existing


def write_state(path):
    state = {
        "name": "audition-audible-gate",
        "room": {"width": 10.0, "depth": 8.0, "units": "m"},
        "listener": {"x": 5.0, "y": 6.5, "heading": 0.0},
        "devices": {
            "audition-0001": {"id": 1, "name": "left", "pos1": [2.0, 3.5]},
            "audition-0002": {"id": 2, "name": "front", "pos1": [5.0, 1.5]},
            "audition-0003": {"id": 3, "name": "right", "pos1": [8.0, 3.5]},
        },
    }
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def wait_http(url, process, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"dashboard exited early with {process.returncode}")
        try:
            with urlopen(url, timeout=0.4) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"dashboard did not become ready at {url}")


def engine_ports_bound(base):
    return all(not udp_available(port) for port in range(base, base + 3))


async def dashboard_readiness(ws_url, audition, engine_base, timeout, no_engine=False):
    deadline = time.monotonic() + timeout
    heartbeats = set()
    converged = set()
    async with websockets.connect(ws_url, open_timeout=timeout) as websocket:
        while time.monotonic() < deadline:
            if audition.poll() is not None:
                raise RuntimeError(f"audition relay exited early with {audition.returncode}")
            remaining = max(0.05, deadline - time.monotonic())
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=min(1.0, remaining))
            except asyncio.TimeoutError:
                continue
            message = json.loads(raw)
            kind, data = message.get("type"), message.get("data") or {}
            if kind == "heartbeat" and data.get("uid") in EXPECTED_UIDS:
                heartbeats.add(data["uid"])
            if kind == "state":
                for uid, device in (data.get("devices") or {}).items():
                    expected_alive = 0 if no_engine else 1
                    if (uid in EXPECTED_UIDS and device.get("online")
                            and int(device.get("engine_alive") or 0) == expected_alive):
                        converged.add(uid)
            elif kind == "device_update":
                uid = data.get("uid")
                expected_alive = 0 if no_engine else 1
                if (uid in EXPECTED_UIDS and data.get("online")
                        and int(data.get("engine_alive") or 0) == expected_alive):
                    converged.add(uid)
            ports_ready = (all(udp_available(port) for port in range(engine_base, engine_base + 3))
                           if no_engine else engine_ports_bound(engine_base))
            if heartbeats == EXPECTED_UIDS and converged == EXPECTED_UIDS and ports_ready:
                return
    raise RuntimeError(
        f"startup timed out: heartbeats={sorted(heartbeats)}, "
        f"nodes_converged={sorted(converged)}, ports_bound={engine_ports_bound(engine_base)}"
    )


def terminate_owned_group(process, timeout):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)


def wait_audition_ports_released(args, timeout):
    deadline = time.monotonic() + timeout
    ports = (args.cmd_port, *range(args.engine_port_base, args.engine_port_base + 3))
    while time.monotonic() < deadline:
        if all(udp_available(port) for port in ports):
            return True
        time.sleep(0.1)
    return False


def wait_ports_released(args, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        udp_released = all(udp_available(port) for port in (
            args.report_port, args.cmd_port,
            *range(args.engine_port_base, args.engine_port_base + 3),
        ))
        # A just-closed TCP listener can leave TIME_WAIT records that prevent a
        # fresh exclusive bind despite no process owning the port. Probe for an
        # actual listener here; preflight still uses the stricter bind check.
        if not tcp_listening(args.http_port) and udp_released:
            return True
        time.sleep(0.1)
    return False


def print_phases(url, output_dir, no_engine=False):
    if no_engine:
        print("\nDry readiness complete: three distinct virtual heartbeats were")
        print("observed; no engines were launched and their ports stayed free.")
        print(f"Tech dashboard: {url}")
        print(f"Facilitator: {url}facilitator")
        print(f"Logs and the neutral run record will remain in: {output_dir}")
        return
    print("\nReady: three distinct audition heartbeats, three live engines, and")
    print("three distinct local engine ports were observed.")
    print(f"\nTech dashboard: {url}")
    print(f"Facilitator: {url}facilitator")
    print("\nInteractive audible phases (make the judgment yourself):")
    print("  1. Baseline: identify the named left / front / right sources.")
    print("  2. Drag the white listener puck across the room; listen for smooth")
    print("     position and level changes without clicks, gaps, or image flips.")
    print("  3. Change listener heading through 0 / 90 / 180 / 270 degrees and")
    print("     confirm the stereo perspective rotates continuously.")
    print("  4. Double-click a device dot to add/remove pos2, then move a device")
    print("     into and out of the tray; confirm 0/1/2-position changes converge.")
    print("  5. Reload the browser and confirm the current listener perspective holds.")
    print("  6. Exercise production master at 1 / 0.5 / 0 / 1, patch gain at")
    print("     0 / 1, and Identify; confirm only the intended behavior changes.")
    print(f"\nLogs and the neutral run record will remain in: {output_dir}")
    print("No audible result is recorded automatically.")


def audition_command(args, manifest, pd_bin):
    command = [
        sys.executable, "-u", str(AUDITION), "--devices", "3",
        "--bind", "127.0.0.1", "--target", "127.0.0.1",
        "--report-port", str(args.report_port), "--cmd-port", str(args.cmd_port),
        "--engine-port-base", str(args.engine_port_base),
        "--manifest", str(manifest), "--pd-bin", pd_bin,
        "--audio-backend", args.audio_backend, "--hb-interval", "1",
        "--catchup-secs", "0.5", "--stop-timeout", "3",
    ]
    if args.no_engine:
        command.append("--no-engine")
    return command


def start_audition(args, manifest, pd_bin, log):
    log.flush()
    offset = log.tell()
    command = audition_command(args, manifest, pd_bin)
    process = subprocess.Popen(
        command, cwd=ROOT,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    return process, command, offset


def inspect_audition_start(log_path, offset, args, baseline_pids):
    """Reject known startup failures and identify only this launch's PD children."""
    deadline = time.monotonic() + min(3.0, args.startup_timeout)
    text = ""
    rows = []
    while time.monotonic() < deadline:
        with log_path.open(errors="replace") as source:
            source.seek(offset)
            text = source.read()
        rows = [(int(node), int(port), int(pid))
                for node, port, pid in PID_LINE.findall(text)]
        if args.no_engine or len(rows) >= 3:
            break
        time.sleep(0.1)

    # PID lines are printed when children are spawned, before PD has necessarily
    # finished opening CoreAudio/JACK. Give the backend one bounded settle, then
    # scan the complete launch segment rather than declaring readiness early.
    if not args.no_engine and len(rows) >= 3:
        time.sleep(min(1.0, max(0.0, args.startup_timeout / 4.0)))
        with log_path.open(errors="replace") as source:
            source.seek(offset)
            text = source.read()
        rows = [(int(node), int(port), int(pid))
                for node, port, pid in PID_LINE.findall(text)]

    lower = text.lower()
    failures = [marker for marker in FATAL_LOG_MARKERS if marker in lower]
    if failures:
        raise RuntimeError(
            f"audition startup log contains fatal marker(s) {failures}: {log_path}"
        )
    if args.no_engine:
        if rows:
            raise RuntimeError(f"--no-engine unexpectedly launched PD: {rows}")
        return set(), []

    expected = {(node, args.engine_port_base + node - 1) for node in (1, 2, 3)}
    surfaces = {(node, port) for node, port, _pid in rows}
    pids = {pid for _node, _port, pid in rows}
    if surfaces != expected or len(rows) != 3 or len(pids) != 3:
        raise RuntimeError(
            f"did not prove three distinct PD surfaces; observed={rows}, expected={sorted(expected)}"
        )
    if pids & baseline_pids:
        raise RuntimeError(f"launch PID set overlaps baseline PD PIDs: {sorted(pids & baseline_pids)}")
    dead = sorted(pid for pid in pids if not process_exists(pid))
    if dead or not engine_ports_bound(args.engine_port_base):
        raise RuntimeError(
            f"PD surface ownership check failed: dead_pids={dead}, "
            f"ports_bound={engine_ports_bound(args.engine_port_base)}"
        )
    warnings = [line for line in text.splitlines()
                if "netreceive: listen failed: Address already in use" in line]
    return pids, warnings


def logged_pd_pids(log_path):
    try:
        return {int(pid) for _node, _port, pid in PID_LINE.findall(
            log_path.read_text(errors="replace")
        )}
    except OSError:
        return set()


async def send_ws_messages(ws_url, messages):
    async with websockets.connect(ws_url, open_timeout=5) as websocket:
        # Consume the initial state so connection/setup failures are visible.
        await asyncio.wait_for(websocket.recv(), timeout=5)
        for kind, data in messages:
            await websocket.send(json.dumps({"type": kind, "data": data}))
            if kind != "set_position":
                continue
            while True:
                raw = await asyncio.wait_for(websocket.recv(), timeout=5)
                message = json.loads(raw)
                update = message.get("data", {})
                if (message.get("type") == "device_update"
                        and update.get("uid") == data.get("uid")
                        and all(update.get(key) == data.get(key)
                                for key in ("pos1", "pos2"))):
                    break


def interactive_loop(args, manifest, pd_bin, audition, audition_log, audition_log_path,
                     ws_url, baseline_pids, active_pids, all_owned_pids,
                     audition_launches):
    restart_count = 0
    commands = []
    print("\nOwned gate commands:")
    print("  r  restart only the owned audition relay/engines and recheck readiness")
    print("  b  bypass: clear all three positions (expect exact identity)")
    print("  s  spatial: restore the seeded left/front/right positions")
    print("  q or Enter  finish and tear down every owned process")
    while True:
        try:
            command = input("\naudible-gate [r/b/s/q, Enter=finish]> ").strip().lower()
        except EOFError:
            command = "q"
        except KeyboardInterrupt:
            print()
            command = "q"
        if command not in {"", "r", "b", "s", "q"}:
            print("Enter r, b, s, or q.")
            continue
        commands.append(command or "enter")
        if command in {"", "q"}:
            return audition, restart_count, commands, command or "enter", active_pids
        if command == "b":
            messages = [("set_position", {"uid": uid, "pos1": None, "pos2": None})
                        for uid in sorted(EXPECTED_UIDS)]
            asyncio.run(send_ws_messages(ws_url, messages))
            print("Bypass frame sent: all three devices now have zero positions.")
            continue
        if command == "s":
            messages = [("set_position", {"uid": uid, "pos1": position, "pos2": None})
                        for uid, position in SEEDED_POSITIONS.items()]
            asyncio.run(send_ws_messages(ws_url, messages))
            print("Seeded one-position left/front/right layout restored.")
            continue

        old_pids = set(active_pids)
        terminate_owned_group(audition, args.stop_timeout)
        if not wait_pids_gone(old_pids, args.stop_timeout):
            raise RuntimeError(f"owned PD PIDs survived restart: {sorted(old_pids)}")
        if not wait_audition_ports_released(args, args.stop_timeout):
            raise RuntimeError("audition restart could not reclaim its command/engine ports")
        replacement, command_argv, log_offset = start_audition(
            args, manifest, pd_bin, audition_log
        )
        launch_record = {"argv": command_argv, "owned_pd_pids": []}
        audition_launches.append(launch_record)
        try:
            asyncio.run(dashboard_readiness(
                ws_url, replacement, args.engine_port_base,
                args.startup_timeout, args.no_engine,
            ))
            replacement_pids, startup_warnings = inspect_audition_start(
                audition_log_path, log_offset, args, baseline_pids
            )
        except Exception:
            terminate_owned_group(replacement, args.stop_timeout)
            raise
        audition = replacement
        active_pids = replacement_pids
        all_owned_pids.update(replacement_pids)
        launch_record["owned_pd_pids"] = sorted(replacement_pids)
        launch_record["startup_warnings"] = startup_warnings
        restart_count += 1
        print(f"Owned audition restart {restart_count} converged.")


def main(argv=None):
    args = parse_args(argv)
    pd_bin, manifest, baseline_pids = preflight(args)
    output_dir = (Path(args.results_dir).expanduser().resolve()
                  if args.results_dir else Path(tempfile.mkdtemp(prefix="bopos-audible-gate-")))
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "installation.json"
    dashboard_log_path = output_dir / "dashboard.log"
    audition_log_path = output_dir / "audition.log"
    record_path = output_dir / "run.json"
    write_state(state_path)

    url = f"http://127.0.0.1:{args.http_port}/"
    dashboard = audition = None
    ready = False
    operator_end = "not-started"
    restart_count = 0
    gate_commands = []
    active_pids = set()
    all_owned_pids = set()
    audition_launches = []
    dashboard_command = [
        sys.executable, "-u", str(DASHBOARD), "--host", "127.0.0.1",
        "--port", str(args.http_port), "--listen-port", str(args.report_port),
        "--send-port", str(args.cmd_port), "--osc-target", "127.0.0.1",
        "--state-file", str(state_path),
    ]
    dashboard_log = dashboard_log_path.open("w", buffering=1)
    audition_log = audition_log_path.open("w", buffering=1)
    started = time.time()
    handled_signals = [signal.SIGTERM]
    if hasattr(signal, "SIGHUP"):
        handled_signals.append(signal.SIGHUP)
    previous_handlers = {signum: signal.getsignal(signum) for signum in handled_signals}

    def controlled_stop(signum, _frame):
        raise GateSignal(signum)

    for signum in handled_signals:
        signal.signal(signum, controlled_stop)
    try:
        dashboard = subprocess.Popen(
            dashboard_command, cwd=ROOT, stdout=dashboard_log, stderr=subprocess.STDOUT,
            start_new_session=True)
        wait_http(url, dashboard, args.startup_timeout)

        audition, launch_argv, log_offset = start_audition(
            args, manifest, pd_bin, audition_log
        )
        launch_record = {"argv": launch_argv, "owned_pd_pids": [],
                         "startup_warnings": []}
        audition_launches.append(launch_record)
        ws_url = f"ws://127.0.0.1:{args.http_port}/ws"
        asyncio.run(dashboard_readiness(
            ws_url, audition,
            args.engine_port_base, args.startup_timeout, args.no_engine,
        ))
        active_pids, startup_warnings = inspect_audition_start(
            audition_log_path, log_offset, args, baseline_pids
        )
        all_owned_pids.update(active_pids)
        launch_record["owned_pd_pids"] = sorted(active_pids)
        launch_record["startup_warnings"] = startup_warnings
        ready = True
        print_phases(url, output_dir, args.no_engine)
        if args.no_engine:
            operator_end = "dry-run-complete"
        else:
            (audition, restart_count, gate_commands, operator_end,
             active_pids) = interactive_loop(
                args, manifest, pd_bin, audition, audition_log, audition_log_path,
                ws_url, baseline_pids, active_pids, all_owned_pids,
                audition_launches,
            )
    except GateSignal as stop:
        operator_end = f"signal-{signal.Signals(stop.signum).name.lower()}"
        print(f"\nControlled stop requested by {signal.Signals(stop.signum).name}.")
    finally:
        audition_log.flush()
        # Launcher PID lines are authoritative for ownership; baseline PIDs are
        # retained only as evidence and are never killed by this harness.
        all_owned_pids.update(logged_pd_pids(audition_log_path) - baseline_pids)
        terminate_owned_group(audition, args.stop_timeout)
        terminate_owned_group(dashboard, args.stop_timeout)
        owned_pd_pids_released = wait_pids_gone(all_owned_pids, args.stop_timeout)
        processes_released = ((audition is None or audition.poll() is not None)
                              and (dashboard is None or dashboard.poll() is not None))
        dashboard_log.close()
        audition_log.close()
        released = wait_ports_released(args, args.stop_timeout)
        record = {
            "started_epoch": started,
            "ended_epoch": time.time(),
            "platform": sys.platform,
            "audio_backend": args.audio_backend,
            "no_engine": args.no_engine,
            "manifest": str(manifest),
            "baseline_pd_pids": sorted(baseline_pids),
            "dashboard_url": url,
            "dashboard_argv": dashboard_command,
            "audition_launches": audition_launches,
            "ready": ready,
            "operator_end": operator_end,
            "restart_count": restart_count,
            "gate_commands": gate_commands,
            "audible_result": "not-recorded",
            "dashboard_returncode": None if dashboard is None else dashboard.poll(),
            "audition_returncode": None if audition is None else audition.poll(),
            "ports_released": released,
            "processes_released": processes_released,
            "owned_pd_pids_released": owned_pd_pids_released,
            "logs": [str(dashboard_log_path), str(audition_log_path)],
        }
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(f"\nRun record: {record_path}")
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)
        if not processes_released or not released or not owned_pd_pids_released:
            raise RuntimeError(
                "owned teardown incomplete: "
                f"processes_released={processes_released}, ports_released={released}, "
                f"owned_pd_pids_released={owned_pd_pids_released}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
