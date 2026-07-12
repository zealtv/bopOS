#!/usr/bin/env python3
"""Soak the shared helper-to-engine OSC client from LAN and cue threads."""
import os
import sys
import threading
import time

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

from pyOSC3 import decodeOSC
import helper


class SlowRecordingClient:
    """Expose overlapping send calls and retain the exact encoded datagrams."""

    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.datagrams = []
        self.guard = threading.Lock()

    def send(self, message):
        with self.guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            # Release the GIL so unlocked callers reliably overlap.
            time.sleep(0.0001)
            datagram = message.getBinary()
            with self.guard:
                self.datagrams.append(datagram)
        finally:
            with self.guard:
                self.active -= 1


def main():
    client = SlowRecordingClient()
    original = helper.client
    helper.client = client
    per_thread = 500
    start = threading.Barrier(5)

    def cues(prefix):
        start.wait()
        for index in range(per_thread):
            helper.fire_cue_to_engine("{}-{}".format(prefix, index))

    def lan(prefix):
        start.wait()
        for index in range(per_thread):
            ok = helper.relay_provided_term("/p/{}".format(prefix), [index])
            if not ok:
                raise AssertionError("provided-term relay failed")

    threads = [
        threading.Thread(target=cues, args=("cue-a",)),
        threading.Thread(target=cues, args=("cue-b",)),
        threading.Thread(target=lan, args=("lan-a",)),
        threading.Thread(target=lan, args=("lan-b",)),
    ]
    try:
        for thread in threads:
            thread.start()
        start.wait()
        for thread in threads:
            thread.join(10)
        assert all(not thread.is_alive() for thread in threads), "soak threads hung"
    finally:
        helper.client = original

    expected = len(threads) * per_thread
    assert client.max_active == 1, "shared client.send overlapped"
    assert len(client.datagrams) == expected, "lost sends: {} != {}".format(
        len(client.datagrams), expected)

    decoded = [decodeOSC(datagram) for datagram in client.datagrams]
    cues_seen = {(str(item[0]), str(item[2])) for item in decoded
                 if str(item[0]) == "/cue"}
    terms_seen = {(str(item[0]), int(item[2])) for item in decoded
                  if str(item[0]).startswith("/p/")}
    assert len(cues_seen) == 2 * per_thread, "cue loss or corruption"
    assert len(terms_seen) == 2 * per_thread, "LAN relay loss or corruption"
    assert all(len(item) == 3 for item in decoded), "malformed OSC message"

    print("[PASS] client.send maximum concurrency: 1")
    print("[PASS] {} /cue and LAN messages delivered".format(expected))
    print("[PASS] every message decoded with its original address and value")
    print("boundary-1 client-lock soak passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
