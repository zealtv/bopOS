"""Node-side point decomposition (contract sec 4.1, seam ruling S1).

Shared by python/bopos.py (the real node) and tools/simfleet.py (the fake
fleet) so both compute identical proximity values; verify scripts import it
to recompute expectations from sniffed wire frames.

Wire forms (LAN 6660 broadcast, selector-less like /sync/ping):

    frame:  /pt <n> <id x y r f>*n     full state, atomic, silence = hold
    sparse: /pt <id> <x> <y> <r> <f>   authoring upsert of one point
    clear:  /pt/clear <id>             authoring removal of one point

The two /pt spellings are unambiguous by arg count: sparse is always 5 args,
a frame is 1 + 5n. `f` is the falloff enum (0 linear, 1 smooth, 2 gauss).

Proximity is a shaped scalar 0->1 per point per element position; the engine
maps it wherever it likes, upstream of its own volume -- the framework never
composes it into a patch param (the sec 1 seam law).
"""
import math


LINEAR, SMOOTH, GAUSS = 0, 1, 2


def _linear(ratio):
    return max(0.0, 1.0 - ratio)


def _smooth(ratio):
    # smoothstep on the linear ramp: flat top near the point, soft knee at R
    x = min(max(1.0 - ratio, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def _gauss(ratio):
    # R as sigma: e^-1 at d == R, never hard zero -- physical tails
    return math.exp(-(ratio * ratio))


FALLOFFS = {LINEAR: _linear, SMOOTH: _smooth, GAUSS: _gauss}


def falloff(enum, distance, radius):
    """Shaped scalar in [0, 1] at `distance` from a point of `radius`.

    The enum registry is closed (contract sec 4.1); an unknown value degrades
    to linear rather than silencing the point.
    """
    if radius <= 0:
        return 0.0
    try:
        curve = FALLOFFS.get(int(enum), _linear)
    except (TypeError, ValueError, OverflowError):
        curve = _linear
    return max(0.0, min(1.0, curve(distance / radius)))


def _integer(value, minimum=0):
    """Int32, without truncation of malformed numeric fields."""
    try:
        number = float(value)
        if (isinstance(value, bool) or not minimum <= number <= 2**31 - 1
                or not number.is_integer()):
            return None
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return None


def _point(values):
    """(x, y, r, f) from four wire args, or None."""
    try:
        x, y, r = float(values[0]), float(values[1]), float(values[2])
        f = _integer(values[3], minimum=-(2**31))
    except (TypeError, ValueError, OverflowError, IndexError):
        return None
    if f is None or not all(-3.4028234663852886e38 <= v <= 3.4028234663852886e38
                            for v in (x, y, r)):
        return None
    return (x, y, r, f)


def parse_wire(parts, args):
    """Decode a /pt-plane datagram into (kind, payload), or None if malformed.

    parts are the address components (["pt"] or ["pt", "clear"]); payloads:
      "frame" -> {id: (x, y, r, f)}      (atomic: any bad entry rejects it all)
      "set"   -> (id, (x, y, r, f))
      "clear" -> id
    """
    if parts == ["pt", "clear"] and len(args) == 1:
        point_id = _integer(args[0])
        return ("clear", point_id) if point_id is not None else None
    if parts != ["pt"] or not args:
        return None
    if len(args) == 5:
        point_id = _integer(args[0])
        if point_id is None:
            return None
        point = _point(args[1:5])
        return ("set", (point_id, point)) if point is not None else None
    count = _integer(args[0])
    if count is None or len(args) != 1 + 5 * count:
        return None
    points = {}
    for index in range(count):
        chunk = args[1 + 5 * index:6 + 5 * index]
        point_id = _integer(chunk[0])
        if point_id is None:
            return None
        point = _point(chunk[1:])
        if point is None:
            return None
        points[point_id] = point
    return ("frame", points)


def decompose(points, elements):
    """[(point_id, element_index, value)] for every point x element.

    `elements` is the assignment's position list, one [x, y] per element;
    element indices are 0-based on the engine wire (pair order, contract
    sec 5; 0-indexing is the project default -- Bob, 2026-07-11).
    """
    entries = []
    for point_id in sorted(points):
        x, y, r, f = points[point_id]
        for index, position in enumerate(elements):
            distance = math.hypot(position[0] - x, position[1] - y)
            entries.append((point_id, index, falloff(f, distance, r)))
    return entries
