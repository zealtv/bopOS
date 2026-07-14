#!/usr/bin/env python3
"""Static verifier for the boundary-4 PD edit wave."""
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo root")
    REPO = parent


def read(path):
    with open(path) as source:
        return source.read()


def fail(message):
    raise AssertionError(message)


def assert_true(condition, message):
    if not condition:
        fail(message)


def main():
    pd_dir = os.path.join(REPO, "pd")
    patch_dir = os.path.join(REPO, "patches", "demo-pd")
    helper_path = os.path.join(REPO, "python", "bopos.py")
    bopos_path = os.path.join(pd_dir, "bopos.pd")
    point_path = os.path.join(pd_dir, "bopos.point.pd")
    out_path = os.path.join(pd_dir, "bopos.out~.pd")
    main_path = os.path.join(patch_dir, "main.pd")

    assert_true(os.path.isfile(bopos_path), "pd/bopos.pd missing")
    assert_true(not os.path.exists(os.path.join(pd_dir, "bopos.osc.pd")),
                "pd/bopos.osc.pd should be absent")

    bopos_text = read(bopos_path)
    point_text = read(point_path)
    out_text = read(out_path)
    main_text = read(main_path)
    helper_text = read(helper_path)

    for required in (
        "netreceive -u -b 6662",
        "netreceive -u -b;",
        "listen 6661",
        "s bopos-context",
        "s bopos-master",
        "s bopos-param",
        "s bopos-point",
        "s bopos-cue",
        "s bopos-notify",
        "s bopos-io",
        "r to-bopos-io",
        "r to-bopos-report",
        "connect 127.0.0.1 7770",
        "connect 127.0.0.1 8880",
    ):
        assert_true(required in bopos_text, f"missing required token in pd/bopos.pd: {required}")

    assert_true("r bopos-point" in point_text, "pd/bopos.point.pd must listen on bopos-point")
    assert_true("r bopos-master" in out_text, "pd/bopos.out~.pd must listen on bopos-master")
    assert_true("r bopos-notify" in out_text, "pd/bopos.out~.pd must listen on bopos-notify")

    assert_true("bopos" in main_text, "default patch must instantiate bopos")
    assert_true("r bopos-param" in main_text, "default patch must read bopos-param")
    assert_true("r bopos-io" in main_text, "default patch must read bopos-io")
    assert_true("s to-bopos-io" in main_text, "default patch must write to-bopos-io")
    assert_true("r bopos-cue" in main_text, "default patch must read bopos-cue")
    assert_true("bopos.point 0 0" in main_text, "default patch must use bopos.point 0 0")
    assert_true("bopos.out~" in main_text, "default patch must use bopos.out~")

    forbidden_pd_patterns = {
        "bopos.osc": [main_text, bopos_text],
        "osc-in": [main_text, bopos_text, out_text],
        "osc-out": [main_text, bopos_text],
        "from-bopos-io": [main_text, bopos_text],
        "bopos-points": [point_text, main_text, bopos_text],
        "route-by-id": [bopos_text, main_text],
        "from-helper": [bopos_text, main_text],
        "role:meter": [main_text, bopos_text],
    }
    for token, texts in forbidden_pd_patterns.items():
        for text in texts:
            assert_true(token not in text, f"forbidden legacy token remains: {token}")

    for forbidden in ("6660", "5550"):
        pd_corpus = "\n".join(
            read(os.path.join(root, name))
            for root, _dirs, files in os.walk(pd_dir)
            for name in files if name.endswith(".pd")
        )
        patch_corpus = "\n".join(
            read(os.path.join(root, name))
            for root, _dirs, files in os.walk(os.path.join(REPO, "patches"))
            for name in files if name.endswith(".pd")
        )
        assert_true(forbidden not in pd_corpus, f"forbidden port remains in pd/*.pd: {forbidden}")
        assert_true(forbidden not in patch_corpus, f"forbidden port remains in patches/*.pd: {forbidden}")

    legacy_engine_msgs = re.findall(
        r'OSCMessage\("/(identify|update|getsamples|shutdown|reboot|checkout|restart-engine)"\)',
        helper_text,
    )
    assert_true(not legacy_engine_msgs,
                f"legacy helper engine notification messages remain: {legacy_engine_msgs}")
    assert_true('OSCMessage("/notify")' in helper_text, "helper.py must emit /notify")

    print("[PASS] PD transport rename and common-surface buses are present")
    print("[PASS] Legacy PD transport/report symbols are removed from active patches")
    print("[PASS] 6660/5550 no longer appear in shipped/reference PD patches")
    print("[PASS] helper.py emits /notify <event> instead of legacy lifecycle addresses")
    print("boundary-4 PD wave static checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
