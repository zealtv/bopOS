#!/usr/bin/env python3
"""Focused fixed-stereo controller-model verification."""

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("could not locate bopOS repository")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "python"))
import audition_matrix as model  # noqa: E402


passed = 0


def check(condition, message):
    global passed
    if not condition:
        raise AssertionError(message)
    passed += 1


def close(actual, expected, tolerance=1e-6):
    check(len(actual) == len(expected), f"length: {actual!r} != {expected!r}")
    for got, want in zip(actual, expected):
        check(abs(got - want) <= tolerance, f"{got!r} != {want!r}")


def rejected(call, label):
    try:
        call()
    except ValueError:
        check(True, label)
    else:
        check(False, f"accepted invalid {label}")


def significant_digits(value):
    mantissa = format(value, ".15g").lower().split("e", 1)[0]
    return len(mantissa.replace(".", "").replace("-", "").lstrip("0"))


def main():
    # Missing positions are exact production bypass.
    check(model.matrix_for_positions([]) == model.IDENTITY, "zero-position bypass")
    close(model.render(model.IDENTITY, 0.1, 0.2), (0.1, 0.2))

    # One co-located stereo position: accepted mid/side width law.
    centre = model.matrix_for_positions([(0.0, 1.0)])
    close(centre, (1.0, 0.0, 0.0, 1.0))
    left_mid = model.matrix_for_positions([(-0.5, 1.0)])
    close(left_mid, (0.9238795, 0.3826834, 0.0, 0.5411961))
    right_mid = model.matrix_for_positions([(0.5, 1.0)])
    close(right_mid, (0.5411961, 0.0, 0.3826834, 0.9238795))
    close(model.matrix_for_positions([(-1.0, 1.0)]),
          (math.sqrt(0.5), math.sqrt(0.5), 0.0, 0.0))
    close(model.matrix_for_positions([(1.0, 1.0)]),
          (0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5)))

    # Duplicated mono naturally pans at constant total power.
    for balance in (-1.0, -0.5, 0.0, 0.5, 1.0):
        outputs = model.render(model.one_position_matrix(balance), 1.0, 1.0)
        check(abs(sum(value * value for value in outputs) - 2.0) < 1e-12,
              f"duplicated mono power at {balance}")

    # Two mono positions preserve channel indexing and independent pans.
    close(model.two_position_matrix((-1.0, 1.0), (1.0, 1.0)),
          (1.0, 0.0, 0.0, 1.0))
    symmetric = model.two_position_matrix((-0.5, 1.0), (0.5, 1.0))
    close(symmetric, (0.9238795, 0.3826834, 0.3826834, 0.9238795))
    close(model.two_position_matrix((0.0, 1.0), (0.0, 1.0)),
          (math.sqrt(0.5),) * 4)

    # Exact steady-signal fixtures captured in the Bob-owned PD session.
    fixtures = (
        ((1.0, 0.0, 0.0, 1.0), (0.100000, 0.200000)),
        ((0.92388, 0.382683, 0.382683, 0.92388), (0.168925, 0.223044)),
        ((0.707107,) * 4, (0.212132, 0.212132)),
        ((0.92388, 0.382683, 0.0, 0.541196), (0.168925, 0.108239)),
        ((0.707107, 0.707107, 0.0, 0.0), (0.212132, 0.0)),
    )
    for matrix, expected in fixtures:
        close(model.render(matrix, 0.1, 0.2), expected, tolerance=1.1e-6)

    safe = model.pd_safe_matrix(symmetric)
    check(all(isinstance(value, float) for value in safe), "PD frame floats")
    check(all(significant_digits(value) <= 6 for value in safe), "PD significant figures")
    check(model.pd_safe_matrix((-0.0, 0.0, 0.0, 1.0))[0] == 0.0,
          "negative zero normalized")

    # The private engine frame is exactly address + four ordered float args.
    frame = model.matrix_frame((0.1, 0.2, 0.3, 0.4))
    check(frame == ("/audition/matrix", 0.1, 0.2, 0.3, 0.4), "frame order")
    check(len(frame) == 5, "frame arity")
    check(all(isinstance(value, float) for value in frame[1:]), "frame float types")

    rejected(lambda: model.matrix_for_positions([(-1.0, 1.0)] * 3), "position count")
    rejected(lambda: model.validate_matrix((1.0, 0.0)), "matrix arity")
    rejected(lambda: model.validate_matrix((True, 0.0, 0.0, 1.0)), "bool")
    rejected(lambda: model.one_position_matrix(float("nan")), "NaN")
    rejected(lambda: model.one_position_matrix(float("inf")), "infinity")
    rejected(lambda: model.one_position_matrix(-1.01), "balance range")
    rejected(lambda: model.one_position_matrix(0.0, 1.01), "gain range")
    rejected(lambda: model.validate_matrix((-0.01, 0.0, 0.0, 1.0)), "matrix low range")
    rejected(lambda: model.validate_matrix((1.01, 0.0, 0.0, 1.0)), "matrix high range")
    rejected(lambda: model.matrix_frame(("x", 0.0, 0.0, 1.0)), "frame type")
    rejected(lambda: model.render(model.IDENTITY, float("nan"), 0.0), "audio NaN")

    print(f"audition matrix verify: {passed} checks passed")


if __name__ == "__main__":
    main()
