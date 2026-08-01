#!/usr/bin/env python3
"""Measure systemd-supervised bopOS control recovery on a real node."""
import argparse
import socket
import subprocess
import time

from pyOSC3 import OSCMessage, decodeOSC


def message(address, value):
    packet = OSCMessage(address)
    packet.append(value)
    return packet.getBinary()


def ssh(args, command):
    result = subprocess.run(
        ["ssh", "-i", args.identity, "-o", "BatchMode=yes", args.ssh_target, command],
        check=True, capture_output=True, text=True)
    return result.stdout.strip()


def service_state(args):
    output = ssh(
        args,
        "systemctl show bopos-helper.service -p MainPID -p NRestarts --value")
    pid, restarts = output.splitlines()
    return int(pid), int(restarts)


def wait_for_pong(sock, target, selector, token, timeout, send_mute=False):
    deadline = time.monotonic() + timeout
    next_send = 0.0
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now >= next_send:
            if send_mute:
                sock.sendto(message(f"/{selector}/os/mute", 1), target)
            sock.sendto(message(f"/{selector}/os/ping", token), target)
            next_send = now + 0.1
        try:
            decoded = decodeOSC(sock.recvfrom(65535)[0])
        except socket.timeout:
            continue
        if str(decoded[0]) == "/os/pong" and int(decoded[2]) == token:
            return time.monotonic()
    raise TimeoutError(f"no pong for token {token} within {timeout}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="bop000.local")
    parser.add_argument("--ssh-target", default="pi@bop000.local")
    parser.add_argument("--identity", required=True)
    parser.add_argument("--selector", default="-1")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 5550))
    sock.settimeout(0.05)
    target = (args.host, 6660)

    baseline_token = int(time.monotonic_ns() % 2_000_000_000)
    wait_for_pong(sock, target, args.selector, baseline_token, args.timeout)
    print("baseline pong: PASS")

    recoveries = []
    for trial in range(1, args.trials + 1):
        old_pid, old_restarts = service_state(args)
        token = (baseline_token + trial) % 2_000_000_000
        kill_started = time.monotonic()
        ssh(args, f"kill -9 {old_pid}")
        kill_returned = time.monotonic()
        pong_at = wait_for_pong(
            sock, target, args.selector, token, args.timeout, send_mute=True)
        new_pid, new_restarts = service_state(args)
        assert new_pid > 0 and new_pid != old_pid, (old_pid, new_pid)
        assert new_restarts == old_restarts + 1, (old_restarts, new_restarts)
        conservative = pong_at - kill_started
        post_kill = pong_at - kill_returned
        recoveries.append(conservative)
        print(
            f"trial {trial}: PASS pid {old_pid}->{new_pid}, "
            f"restarts {old_restarts}->{new_restarts}, "
            f"kill-start-to-pong={conservative:.3f}s, "
            f"kill-return-to-pong={post_kill:.3f}s")
        time.sleep(0.5)

    print(
        f"PASS: {len(recoveries)} trials; conservative recovery "
        f"min={min(recoveries):.3f}s max={max(recoveries):.3f}s")


if __name__ == "__main__":
    main()
