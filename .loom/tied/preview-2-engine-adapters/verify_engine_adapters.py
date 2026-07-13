#!/usr/bin/env python3
"""Static/model gate for the PD and SC private audition adapters."""

import math
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True


def repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "python"))
import audition_matrix  # noqa: E402


checks = 0


def check(condition, label):
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def contains(text, spelling, label):
    check(spelling in text, label)


def close(actual, expected, tolerance=2e-6):
    check(len(actual) == len(expected), "matrix arity")
    for got, want in zip(actual, expected):
        check(abs(float(got) - float(want)) <= tolerance,
              f"matrix value {got!r} != {want!r}")


def pd_static_test():
    bopos = (ROOT / "pd" / "bopos.pd").read_text()
    audition = (ROOT / "pd" / "bopos.audition~.pd").read_text()
    output = (ROOT / "pd" / "bopos.out~.pd").read_text()

    contains(bopos, "route id os audition", "PD top-level audition route")
    contains(bopos, "route matrix", "PD matrix member route")
    contains(bopos, "s bopos-audition-matrix", "PD private matrix send")
    # Existing engine-surface routes must remain present after adding audition.
    for spelling in (
        "route p pt cue notify", "route master", "s bopos-param",
        "s bopos-point", "s bopos-cue", "s bopos-notify", "s bopos-master",
        "s bopos-context", "r BOPOS_ENGINE_PORT", "listen \\$1",
    ):
        contains(bopos, spelling, f"PD retained {spelling}")
    contains(output, "bopos.audition~", "PD output retains private adapter")
    contains(audition, "r bopos-audition-matrix", "PD helper receives matrix")
    contains(audition, "list length", "PD helper validates arity")
    contains(audition, "== 4", "PD helper requires four gains")
    contains(audition, "t l l b", "PD helper closes candidate gate first")
    contains(audition, "-1 -1 -1 -1", "PD helper resets every typed gain")
    contains(audition, "\\$1 20", "PD helper smooths gains over 20 ms")
    for comparison in ("$f1==$f1", "$f4==$f4", "$f1>=0", "$f4<=1"):
        contains(audition, comparison, f"PD helper validation {comparison}")

    # A typed [unpack] silently retains a cold inlet when an atom has the
    # wrong type. Prove the reset reaches that unpack (not merely the final
    # spigot), so a symbol in any slot leaves an out-of-range sentinel and the
    # complete candidate is rejected.
    validate = audition.split("validate 0;", 1)[1].split("#X restore", 1)[0]
    objects = [line for line in validate.splitlines()
               if line.startswith(("#X obj ", "#X msg "))]

    def object_index(spelling):
        matches = [index for index, line in enumerate(objects)
                   if spelling in line]
        check(len(matches) == 1, f"unique PD validate object: {spelling}")
        return matches[0]

    trigger = object_index("t l l b")
    candidate_spigot = object_index("spigot, f 33")
    typed_unpack = object_index("unpack f f f f")
    validator = object_index("expr ($f1==$f1)")
    sentinel = object_index("-1 -1 -1 -1")
    connections = {
        tuple(map(int, match.groups()))
        for match in re.finditer(
            r"#X connect (\d+) (\d+) (\d+) (\d+);", validate
        )
    }
    for connection, label in (
        ((trigger, 2, sentinel, 0), "PD trigger resets sentinels first"),
        ((sentinel, 0, typed_unpack, 0), "PD sentinel resets typed unpack"),
        ((trigger, 1, typed_unpack, 0), "PD candidate reaches typed unpack"),
        ((trigger, 0, candidate_spigot, 0), "PD data waits at final gate"),
        ((validator, 0, candidate_spigot, 1), "PD validation controls gate"),
    ):
        check(connection in connections, label)
    check((sentinel, 0, candidate_spigot, 1) not in connections,
          "PD sentinel does not bypass typed validation")


def sc_static_test():
    source = (ROOT / "templates" / "supercollider-bopos" / "main.scd").read_text()
    readme = (ROOT / "templates" / "supercollider-bopos" / "README.md").read_text()

    for spelling in (
        "auditionMatrix: [1.0, 0.0, 0.0, 1.0]",
        "|bus=0, master=1, l0=1, l1=0, r0=0, r1=1|",
        "Lag.kr([l0, l1, r0, r1].clip(0, 1), 0.02)",
        "(signal[0] * gains[0]) + (signal[1] * gains[1])",
        "(signal[0] * gains[2]) + (signal[1] * gains[3])",
        "auditioned * Lag.kr(master.clip(0, 1), 0.03)",
        "OSCdef(\\boposAuditionMatrix",
        "message.size == 5",
        "message.copyRange(1, 4)",
        "value.isNumber",
        "value.isNaN.not",
        "value >= 0",
        "value <= 1",
        "'/audition/matrix'",
        "recvPort: ~bopos.enginePort",
    ):
        contains(source, spelling, f"SC adapter spelling: {spelling}")
    # Atomicity: retained state and Synth controls change only inside valid.
    valid_block = source.split("if(valid) {", 2)[-1].split("};", 1)[0]
    contains(valid_block, "~bopos.auditionMatrix =", "SC valid-only retained state")
    contains(valid_block, "~bopos.out.set(", "SC valid-only output update")
    contains(readme, "/audition/matrix <l0> <l1> <r0> <r1>", "SC README frame")
    contains(readme, "L = x0*l0 + x1*l1", "SC README left equation")
    contains(readme, "R = x0*r0 + x1*r1", "SC README right equation")


def shared_fixture_test():
    fixtures = (
        (audition_matrix.IDENTITY, (0.1, 0.2)),
        (audition_matrix.one_position_matrix(-0.5), (0.16892464, 0.10823922)),
        (audition_matrix.two_position_matrix((-0.5, 1), (0.5, 1)),
         (0.16892464, 0.22304425)),
    )
    for matrix, expected in fixtures:
        frame = audition_matrix.matrix_frame(matrix)
        check(frame[0] == "/audition/matrix", "shared frame address")
        check(len(frame) == 5, "shared frame arity")
        check(all(isinstance(value, float) and math.isfinite(value)
                  and 0 <= value <= 1 for value in frame[1:]), "shared safe gains")
        close(audition_matrix.render(frame[1:], 0.1, 0.2), expected)


def main():
    pd_static_test()
    sc_static_test()
    shared_fixture_test()
    print(f"engine adapter verify: {checks} checks passed")


if __name__ == "__main__":
    main()
