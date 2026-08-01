#!/usr/bin/env python3
"""Guard for 29-fleet-patch-sync-hang/2-fix.

Proves the mute fix: enforce_mute targets the DAC exactly (card-aware amixer +
the card's real control name) and NEVER stops the engine as a fallback.
Regression against the bug where a fleet-patch push muted a DigiAMP+ node whose
default ALSA card had no controls, so mute fell through to stop-engine and the
node sat online with a dead engine.

Run: PYTHONPATH=<repo>/python python3 verify_mute_targeting.py
"""
import os
import sys
import types

# repo-by-marker root, then put python/ on the path (survives tie moves).
here = os.path.abspath(__file__)
root = here
while root != "/" and not os.path.exists(os.path.join(root, "tools", "simfleet.py")):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, "python"))

import pyOSC3
pyOSC3.OSCServer = lambda *a, **k: types.SimpleNamespace(
    addMsgHandler=lambda *a, **k: None, timeout=0, close=lambda: None)
pyOSC3.OSCClient = lambda *a, **k: types.SimpleNamespace(
    connect=lambda *a, **k: None, send=lambda *a, **k: None)
sys.argv = ["bopos.py", "unknown"]
import bopos

failures = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok else f" -- {detail}"))
    if not ok:
        failures.append(name)


class FakeState:
    def __init__(self, soundcard=None, mixer_control=None):
        self.config = {"SOUNDCARD": soundcard, "MIXER_CONTROL": mixer_control}
        self.mixer_control = None


def with_amixer(succeed_when, cards=("vc4hdmi", "DigiAMP")):
    """Install stubs; record amixer argvs; succeed only when succeed_when(argv)."""
    calls = []

    def run_command(argv, wait_for_start=False):
        calls.append(argv)
        if argv and argv[0] == "amixer":
            return 0 if succeed_when(argv) else 1
        return 1  # any bash/*-engine.sh call "succeeds" -> if it were reached,
        #            the no-stop assertions would still catch the call itself.
    bopos.run_command = run_command
    bopos._alsa_card_ids = lambda: list(cards)
    return calls


old_run, old_cards = bopos.run_command, bopos._alsa_card_ids
try:
    # 1) DigiAMP+ auto-detect: default card (vc4hdmi) has no controls; the DAC
    #    control 'Digital' only works with `-c DigiAMP`. Mute must find it.
    calls = with_amixer(lambda a: "-c" in a and a[a.index("-c") + 1] == "DigiAMP"
                        and "Digital" in a)
    st = FakeState()
    ok = bopos.enforce_mute(1, st)
    used = [a for a in calls if a[0] == "amixer" and a[-1] == "mute"]
    winner = used[-1] if used else []
    check("auto-detect mutes via -c DigiAMP Digital",
          ok is True and "-c" in winner and winner[winner.index("-c") + 1] == "DigiAMP"
          and "Digital" in winner, repr(calls))
    hdmi_targets = [t for t in bopos.mute_targets(FakeState()) if t[0] == "vc4hdmi"]
    check("mute_targets never yields an HDMI card", hdmi_targets == [], repr(hdmi_targets))
    check("winning (card, control) remembered", st.mixer_control == ("DigiAMP", "Digital"),
          repr(st.mixer_control))

    # 2) Remembered pair is retried first on the next call.
    calls = with_amixer(lambda a: "-c" in a and a[a.index("-c") + 1] == "DigiAMP"
                        and "Digital" in a)
    st.mixer_control = ("DigiAMP", "Digital")
    bopos.enforce_mute(0, st)
    first = next(a for a in calls if a[0] == "amixer")
    check("remembered pair tried first",
          "-c" in first and first[first.index("-c") + 1] == "DigiAMP"
          and "Digital" in first and first[-1] == "unmute", repr(calls))

    # 3) Configured SOUNDCARD/MIXER_CONTROL win.
    calls = with_amixer(lambda a: "-c" in a and a[a.index("-c") + 1] == "card9"
                        and "MyCtl" in a)
    st = FakeState(soundcard="card9", mixer_control="MyCtl")
    ok = bopos.enforce_mute(1, st)
    check("configured card/control used", ok is True
          and any("card9" in a and "MyCtl" in a for a in calls), repr(calls))

    # 4) THE FIX: no working control -> mute FAILS and the engine is NOT stopped.
    calls = with_amixer(lambda a: False)  # every amixer fails
    st = FakeState()
    ok = bopos.enforce_mute(1, st)
    check("mute with no control returns False", ok is False, repr(ok))
    check("mute never calls stop-engine",
          not any(str(a[-1]).endswith("stop-engine.sh") for a in calls), repr(calls))

    # 5) Unmute with no working control also never starts the engine.
    calls = with_amixer(lambda a: False)
    st = FakeState()
    bopos.enforce_mute(0, st)
    check("unmute never calls start-engine",
          not any(str(a[-1]).endswith("start-engine.sh") for a in calls), repr(calls))

    # 6) muted_via_stop is gone entirely.
    check("muted_via_stop removed from NodeState",
          not hasattr(bopos.NodeState.__new__(bopos.NodeState), "muted_via_stop")
          and "muted_via_stop" not in open(os.path.join(root, "python", "bopos.py")).read(),
          "muted_via_stop still present")
finally:
    bopos.run_command, bopos._alsa_card_ids = old_run, old_cards

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("all mute-targeting checks passed")
