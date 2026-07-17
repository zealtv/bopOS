#!/usr/bin/env python3
"""Browser-free unit tests for audition_geometry forward-bias.

Pins the three anchor cases from the stitch's pinned design (ahead=1.0,
behind=REAR_FLOOR, abeam=(1+REAR_FLOOR)/2), the distance-0 early return,
and a sanity import of tools/audition.py to confirm no caller assumed
gain independent of heading.
"""

import importlib.util
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "python"))
import audition_geometry  # noqa: E402


checks = 0


def check(condition, label):
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def close(actual, expected, tolerance=1e-9, label=""):
    check(abs(float(actual) - float(expected)) <= tolerance,
          f"{label}: {actual!r} != {expected!r}")


def gain_at(heading_deg, position, range_m=10.0, distance_from_origin=1.0):
    listener = audition_geometry.Listener(0, 0, heading_deg, range_m)
    _, gain = audition_geometry.element_terms(listener, position)
    # Divide out the distance falloff term so only the forward factor remains.
    falloff = audition_geometry_falloff(distance_from_origin, range_m)
    return gain / falloff


def audition_geometry_falloff(distance, range_m):
    import pointfield
    return pointfield.falloff(pointfield.SMOOTH, distance, range_m)


def forward_bias_tests():
    rear_floor = audition_geometry.REAR_FLOOR
    close(rear_floor, 0.35, label="REAR_FLOOR constant")

    # Heading 0 is map-up (0, -1). Element straight ahead (up) from the
    # listener at (0, 0).
    ahead_forward = gain_at(0, (0, -1))
    close(ahead_forward, 1.0, label="ahead forward factor")

    # Element straight behind (down).
    behind_forward = gain_at(0, (0, 1))
    close(behind_forward, rear_floor, label="behind forward factor")

    # Element abeam (to the right, +x) -- exactly 90 degrees off heading.
    abeam_forward = gain_at(0, (1, 0))
    close(abeam_forward, (1 + rear_floor) / 2, label="abeam (+x) forward factor")

    # Abeam the other side (-x) should be identical by symmetry.
    abeam_forward_left = gain_at(0, (-1, 0))
    close(abeam_forward_left, (1 + rear_floor) / 2, label="abeam (-x) forward factor")

    # Rotate the listener 90 degrees clockwise (heading 90, now facing +x/east).
    # "Ahead" is now the +x direction.
    ahead_turned = gain_at(90, (1, 0))
    close(ahead_turned, 1.0, label="ahead forward factor (turned 90)")
    behind_turned = gain_at(90, (-1, 0))
    close(behind_turned, rear_floor, label="behind forward factor (turned 90)")

    # Distance 0 keeps the existing early return, unaffected by heading.
    listener = audition_geometry.Listener(3, 4, 137, 10)
    check(audition_geometry.element_terms(listener, (3, 4)) == (0.0, 1.0),
          "distance-0 early return unaffected by forward bias")

    # terms_for_positions threads the forward factor through in order.
    listener = audition_geometry.Listener(0, 0, 0, 10)
    terms = audition_geometry.terms_for_positions(
        listener, ((0, -1), (1, 0), (0, 1), (-1, 0)))
    falloff = audition_geometry_falloff(1.0, 10.0)
    expected_gains = (
        falloff * 1.0,
        falloff * (1 + rear_floor) / 2,
        falloff * rear_floor,
        falloff * (1 + rear_floor) / 2,
    )
    for index, (term, expected) in enumerate(zip(terms, expected_gains)):
        close(term[1], expected, label=f"terms_for_positions[{index}] gain")


def audition_caller_sanity():
    # Import tools/audition.py to confirm the module still loads cleanly
    # against the new element_terms/terms_for_positions gain shape, and
    # confirm matrix_for_node's only use of terms is passing them straight
    # through to audition_matrix.matrix_for_positions -- it never assumes
    # gain is independent of heading.
    audition_path = ROOT / "tools" / "audition.py"
    spec = importlib.util.spec_from_file_location("audition_forward_bias_sanity", audition_path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "tools"))
    spec.loader.exec_module(module)
    check(hasattr(module, "AuditionRig"), "tools/audition.py imports cleanly")

    import inspect
    source = inspect.getsource(module.AuditionRig.matrix_for_node)
    check("terms_for_positions" in source, "matrix_for_node still calls terms_for_positions")
    check("audition_matrix.matrix_for_positions(terms)" in source,
          "matrix_for_node passes terms straight through without assuming "
          "gain is independent of heading")


def main():
    forward_bias_tests()
    audition_caller_sanity()
    print(f"ok: {checks} checks passed")


if __name__ == "__main__":
    main()
