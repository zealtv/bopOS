#!/usr/bin/env python3
"""Port-sharing spike (audition-0-port-spike).

Question: can N processes on one host all receive the same UDP broadcast on
one port, the way N Pis do on a network? Runs the Python control matrix
(which socket flags make it work, and what happens to unicast) and prints a
table. The PD half is driven separately (spike_pd.sh) because PD needs a
patch and an OSC listener to observe replies.

Usage: python3 spike_port_sharing.py [--port 16660]
"""
import argparse
import multiprocessing
import platform
import socket
import sys
import time


def make_socket(port, reuseaddr, reuseport):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if reuseaddr:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if reuseport and hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", port))
    return sock


def receiver(port, reuseaddr, reuseport, queue, tag):
    try:
        sock = make_socket(port, reuseaddr, reuseport)
    except OSError as error:
        queue.put((tag, "bind-error", str(error)))
        return
    queue.put((tag, "bound", ""))
    sock.settimeout(3.0)
    got = []
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        try:
            datagram, _ = sock.recvfrom(65535)
            got.append(datagram.decode(errors="replace"))
        except socket.timeout:
            break
    queue.put((tag, "received", ",".join(got)))


def run_case(port, reuseaddr, reuseport, destination):
    queue = multiprocessing.Queue()
    workers = [multiprocessing.Process(target=receiver,
                                       args=(port, reuseaddr, reuseport, queue, f"rx{i}"))
               for i in range(3)]
    for worker in workers:
        worker.start()
    time.sleep(0.5)
    bound, errors = set(), {}
    # drain bind results
    results = {}
    for _ in workers:
        tag, status, detail = queue.get(timeout=5)
        if status == "bound":
            bound.add(tag)
        else:
            errors[tag] = detail

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    for i in range(3):
        sender.sendto(b"ping%d" % i, (destination, port))
        time.sleep(0.05)
    sender.close()

    received = {}
    deadline = time.monotonic() + 6.0
    expected = len(bound)
    while len(received) < expected and time.monotonic() < deadline:
        try:
            tag, status, detail = queue.get(timeout=6)
        except Exception:
            break
        if status == "received":
            received[tag] = [item for item in detail.split(",") if item]
    for worker in workers:
        worker.join(timeout=2)
        if worker.is_alive():
            worker.terminate()
    return bound, errors, received


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=16660)
    args = parser.parse_args()

    print(f"platform: {platform.platform()}")
    print(f"python:   {platform.python_version()}")
    print(f"SO_REUSEPORT available: {hasattr(socket, 'SO_REUSEPORT')}")
    print()

    destinations = [("255.255.255.255", "broadcast"), ("127.0.0.1", "unicast-loopback")]
    flag_cases = [(False, False, "no flags"),
                  (True, False, "SO_REUSEADDR"),
                  (True, True, "SO_REUSEADDR+SO_REUSEPORT")]
    port = args.port
    for destination, dest_label in destinations:
        for reuseaddr, reuseport, flag_label in flag_cases:
            port += 1  # fresh port per case: no lingering-socket bleed
            bound, errors, received = run_case(port, reuseaddr, reuseport, destination)
            all_got_all = (len(bound) == 3
                           and all(len(received.get(tag, [])) == 3 for tag in bound))
            counts = {tag: len(received.get(tag, [])) for tag in sorted(bound)}
            print(f"[{dest_label:17}] [{flag_label:26}] bound={len(bound)}/3 "
                  f"received={counts if bound else '-'} "
                  f"{'<< ALL SEE ALL' if all_got_all else ''}")
            for tag, detail in sorted(errors.items()):
                print(f"    {tag}: {detail}")
    print()
    print("verdict criteria: audition-rig needs 'broadcast + some flag combo' to be")
    print("ALL SEE ALL with 3/3 bound; unicast rows show what happens to node-")
    print("targeted replies when every 'node' shares one IP.")


if __name__ == "__main__":
    main()
