#!/usr/bin/env python3
"""Verify updatepatch reaches the engine before patch lifecycle teardown."""

import os
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "python/bopos.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = root()
sys.path[:0] = [str(ROOT / "python"), str(ROOT)]
import bopos  # noqa: E402


class Message:
    def __init__(self, address):
        self.address = address
        self.args = []

    def append(self, value, _kind=None):
        self.args.append(value)


def main():
    saved = {name: getattr(bopos, name) for name in (
        "BOPOS_DIR", "OSCMessage", "send_to_engine", "run_command",
        "engine_alive", "hb_wake")}
    saved_run = bopos.subprocess.run
    events = []
    with tempfile.TemporaryDirectory(prefix="bopos-notify-patch-") as directory:
        root_path = Path(directory)
        (root_path / "bash").mkdir()
        patches = root_path / "patches"
        patches.mkdir()
        for name in ("old", "new"):
            patch = patches / name
            patch.mkdir()
            (patch / "bopos.patch.json").write_text(
                '{"engine":"test","entrypoint":"main.bin","caps":[],"slots":[],"params":[],"cues":[]}',
                encoding="utf-8")
            (patch / "main.bin").write_bytes(b"test")
        (patches / "active_patch.txt").write_text("old\n", encoding="utf-8")
        try:
            bopos.BOPOS_DIR = directory
            bopos.OSCMessage = Message
            bopos.send_to_engine = lambda message: events.append(
                ("notify", message.address, tuple(message.args)))
            bopos.run_command = lambda argv, **_kwargs: events.append(
                ("command", os.path.basename(argv[1]))) or 0
            bopos.engine_alive = lambda: 1
            bopos.hb_wake = SimpleNamespace(set=lambda: None)
            bopos.subprocess.run = lambda *_args, **_kwargs: SimpleNamespace(returncode=0)

            result = bopos.pull_active_patch_callback()
            assert result["status"] == "ok"
            assert events[0] == ("notify", "/notify", ("updatepatch",))
            print("[PASS] active-patch pull notifies before its lifecycle script")

            events.clear()
            result = bopos.switch_patch_callback(args=["new"])
            assert result["status"] == "ok"
            stop_index = events.index(("command", "stop-engine.sh"))
            assert events.index(("notify", "/notify", ("updatepatch",))) < stop_index
            print("[PASS] patch switch notifies before stop-engine.sh")

            source = (ROOT / "python/bopos.py").read_text(encoding="utf-8")
            symbols = re.findall(r'msg\.append\("([^"]+)"', source)
            for symbol in ("identify", "updatebopos", "checkout", "restart-engine",
                           "shutdown", "reboot"):
                assert symbol in symbols
            assert symbols.count("updatepatch") == 2
            print("[PASS] six existing lifecycle symbols remain and updatepatch occurs twice")
        finally:
            for name, value in saved.items():
                setattr(bopos, name, value)
            bopos.subprocess.run = saved_run


if __name__ == "__main__":
    main()
