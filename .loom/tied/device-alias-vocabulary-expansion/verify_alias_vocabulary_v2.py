#!/usr/bin/env python3
"""Focused browser-free verification for the expanded alias vocabulary."""

import json
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "dashboard" / "device_aliases.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "dashboard"))

import device_aliases  # noqa: E402
from state import InstallationState  # noqa: E402


failures = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


check("v2 doubles both curated vocabularies",
      device_aliases.GENERATOR_VERSION == 2
      and len(device_aliases.GIVEN_NAMES) == 128
      and len(device_aliases.CHARACTER_WORDS) == 128)

all_words = device_aliases.GIVEN_NAMES + device_aliases.CHARACTER_WORDS
check("all tokens remain unique, short, and ASCII alphabetic",
      len({word.casefold() for word in device_aliases.GIVEN_NAMES}) == 128
      and len({word.casefold() for word in device_aliases.CHARACTER_WORDS}) == 128
      and all(re.fullmatch(r"[A-Za-z]{2,12}", word) for word in all_words))

v1_vectors = {
    "2c:cf:67:b3:0a:58": ("Niko Cloud", "Ines Neon"),
    "02:00:00:00:00:01": ("Nia Gold", "Zain Rocket"),
    "machine-alpha": ("Nia Quartz", "Lani Sugar"),
}
check("explicit v1 compatibility preserves every pinned vector",
      all((device_aliases.candidate(uid, 0, version=1),
           device_aliases.candidate(uid, 1, version=1)) == expected
          for uid, expected in v1_vectors.items()))

v2_vectors = {
    "2c:cf:67:b3:0a:58": ("Finn Jet", "Zain Solar"),
    "02:00:00:00:00:01": ("Rami Lucky", "Anya Flora"),
    "machine-alpha": ("Amara Lemon", "Sela Willow"),
}
check("default v2 allocation is pinned",
      all((device_aliases.candidate(uid), device_aliases.candidate(uid, 1)) == expected
          for uid, expected in v2_vectors.items()))

uid = "collision-target"
first = device_aliases.candidate(uid)
registry = {"owner": {"alias": first, "source": "generated", "generator": 2}}
allocated = device_aliases.allocate(uid, registry)
check("v2 collision probing advances without changing the owner",
      allocated["alias"] == device_aliases.candidate(uid, 1)
      and registry["owner"]["alias"] == first
      and allocated["generator"] == 2)

space = len(device_aliases.GIVEN_NAMES) * len(device_aliases.CHARACTER_WORDS)
visited = {device_aliases.candidate("complete-space", probe)
           for probe in range(space)}
check("v2 probing visits all 16,384 pairs exactly once", len(visited) == space)

niko_uid = "2c:cf:67:b3:0a:58"
with tempfile.TemporaryDirectory(prefix="bopos-alias-v2-") as root:
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps({
        "schema": 1,
        "seats": {},
        "groups": {},
        "next_group_id": 0,
        "device_registry": {
            niko_uid: {"alias": "Niko Cloud", "source": "generated",
                       "generator": 1, "device_muted": True},
        },
    }), encoding="utf-8")
    state = InstallationState(str(state_path))
    state.save()
    restarted = InstallationState(str(state_path))
    reset_entry, reset_error = restarted.reset_device_alias(niko_uid)
    entry = restarted.device_registry.get(niko_uid)
    check("restart and Reset preserve an existing generated v1 alias exactly",
          reset_error is None and reset_entry == entry
          and entry == {"alias": "Niko Cloud", "source": "generated",
                        "generator": 1, "device_muted": True}, repr(entry))
    check("existing v1 mute intent survives vocabulary expansion",
          entry == {"alias": "Niko Cloud", "source": "generated",
                    "generator": 1, "device_muted": True}, repr(entry))

print(f"\n{len(failures)} failure(s)")
raise SystemExit(1 if failures else 0)
