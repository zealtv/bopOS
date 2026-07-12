#!/usr/bin/env python3
"""Focused v1.2 adoption regression for the Stage 0 audition launcher."""

import importlib.util
from pathlib import Path
import sys


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def current_launch_context_test(audition):
    args = audition.parse_args(["--devices", "2", "--audio-backend", "coreaudio"])
    rig = object.__new__(audition.AuditionRig)
    rig.args = args
    patch_dir = ROOT / "patches" / "default"
    loaded, error = audition.patch_manifest.load(str(patch_dir))
    assert error is None
    contexts = [
        {"seed": 123456, "run_id": "run-a"},
        {"seed": 654321, "run_id": "run-b"},
    ]
    nodes = [
        audition.VirtualNode(0, 1, "audition-0001", 16661),
        audition.VirtualNode(1, 2, "audition-0002", 16662),
    ]
    commands = [
        rig.engine_command(node, str(patch_dir), loaded, context)
        for node, context in zip(nodes, contexts)
    ]
    sends = [command[command.index("-send") + 1] for command in commands]
    assert all("-pa" in command for command in commands)
    assert "BOPOS_ENGINE_PORT 16661" in sends[0]
    assert "bopos-context seed 123456" in sends[0]
    assert "bopos-context run-id run-a" in sends[0]
    assert "BOPOS_ENGINE_PORT 16662" in sends[1]
    assert "bopos-context seed 654321" in sends[1]
    assert "ID " not in sends[0] and "ID " not in sends[1]


def pd_override_test():
    text = (ROOT / "pd" / "bopos.pd").read_text()
    assert "r BOPOS_ENGINE_PORT" in text
    assert "listen \\$1" in text
    assert "netreceive -u -b 6661" in text


def main():
    old = load(
        "audition_1a_verify",
        ROOT / ".loom" / "tied" / "audition-1a-relay-launcher" / "verify_audition.py",
    )
    audition = old.load_audition_module()
    current_launch_context_test(audition)
    pd_override_test()
    old.exclusive_bind_test()
    old.partial_start_failure_test()
    old.no_engine_protocol_test()
    old.owned_process_test()
    print("PASS: v1.2 context, PD port override, relay isolation, and owned teardown")


if __name__ == "__main__":
    main()
