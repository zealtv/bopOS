#!/usr/bin/env python3
"""Verify PD's common 6661 surface while its direct 6660 path remains."""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

from pyOSC3 import OSCMessage, decodeOSC
import bopos as helper


class RecordingClient:
    def __init__(self):
        self.datagrams = []

    def send(self, message):
        self.datagrams.append(message.getBinary())


class UnusedReplySocket:
    def sendto(self, *_args):
        raise AssertionError("provided-term relay unexpectedly used LAN reply socket")


def packet(address, *values):
    message = OSCMessage(address)
    for value in values:
        helper.typed_append(message, value)
    return message.getBinary()


def main():
    pd_abstraction = os.path.join(REPO, "pd", "bopos.osc.pd")
    with open(pd_abstraction) as source:
        pd_text = source.read()
    assert "netreceive -u -b 6660" in pd_text, "PD direct 6660 safety path was removed"
    assert "netreceive -u -b 6661" in pd_text, "PD common 6661 ingress is missing"

    recorder = RecordingClient()
    original_client = helper.client
    helper.client = recorder
    state = helper.node_state
    original_id, original_elements = state.id, state.elements
    state.id = 7
    state.elements = [[0.0, 0.0]]
    try:
        source = ("127.0.0.1", 5550)
        reply = UnusedReplySocket()
        assert helper.handle_lan_datagram(
            packet("/7/os/master", 0.4), source, reply, state)
        assert helper.handle_lan_datagram(
            packet("/7/p/gain", 0.6), source, reply, state)

        # Identity, point, cue, and identify notification already use 6661.
        helper.config_callback()
        assert helper.handle_lan_datagram(
            packet("/pt", 0, 0.0, 0.0, 1.0, 0), source, reply, state)
        helper.fire_cue_to_engine("downbeat")
        assert helper.identify(state.uid, state)
    finally:
        helper.client = original_client
        state.id, state.elements = original_id, original_elements

    decoded = [decodeOSC(datagram) for datagram in recorder.datagrams]
    addresses = [str(message[0]) for message in decoded]
    expected = ["/os/master", "/p/gain", "/id", "/pt", "/cue", "/identify"]
    assert addresses == expected, "common-surface mismatch: {}".format(addresses)
    assert abs(float(decoded[0][2]) - 0.4) < 1e-6
    assert abs(float(decoded[1][2]) - 0.6) < 1e-6
    assert int(decoded[2][2]) == 7
    assert [int(decoded[3][2]), int(decoded[3][3])] == [0, 0]
    assert abs(float(decoded[3][4]) - 1.0) < 1e-6
    assert str(decoded[4][2]) == "downbeat"
    assert len(decoded[5]) == 2

    print("[PASS] PD abstraction retains direct 6660 and common 6661 listeners")
    print("[PASS] master, params, identity, points, cues, and identify notification use 6661")
    print("[PASS] common messages are selector-stripped and decodable")
    print("boundary-2 PD parallel relay checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
