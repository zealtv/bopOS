"""Point authoring math for the dashboard (contract sec 4.1).

The dashboard authors and broadcasts point *geometry*; every device
decomposes it locally (python/pointfield.py is the canonical consumer — the
falloff enum values here mirror it). This module is pure: sanitize untrusted
ws payloads into well-formed points, evaluate motion, build wire args.

Motion (static point / swept path / orbit / wall bounce) is the test driver salvaged from
the reverted spatial-0 engine; spatial-1's authoring UI replaces the static
point with a drag.

Coordinates are the installation's floor-plan metres (state.DEFAULT_ROOM:
origin top-left, x right, y down).
"""
import math


FALLOFF_ENUMS = {"linear": 0, "smooth": 1, "gauss": 2}   # wire enum, sec 4.1
DEFAULT_FALLOFF = 1                                       # smooth
DEFAULT_RADIUS = 3.0                                      # metres
RATE_HZ = 25    # broadcast rate while a point moves (contract: ~20-30 Hz)
MAX_POINTS = 32  # frame stays well under one MTU (1 + 5*32 args)


def sanitize_point(raw, room=None):
    """One ws point payload -> a safe point dict, or None if unusable.

    Falloff accepts the wire enum int or its name. A malformed motion is
    dropped (the point stays static at x, y) rather than rejected.
    """
    if not isinstance(raw, dict):
        return None
    try:
        point_id = int(raw.get("id"))
    except (TypeError, ValueError):
        return None
    if point_id < 0:
        return None
    center = _center(room)
    point = {
        "id": point_id,
        "x": _clamp_float(raw.get("x"), center[0], -1000.0, 1000.0),
        "y": _clamp_float(raw.get("y"), center[1], -1000.0, 1000.0),
        "r": _clamp_float(raw.get("r"), DEFAULT_RADIUS, 0.01, 1000.0),
        "falloff": _falloff_enum(raw.get("falloff")),
    }
    motion = _sanitize_motion(raw.get("motion"), room, (point["x"], point["y"]))
    if motion is not None:
        point["motion"] = motion
    return point


def sanitize_points(raw, room=None):
    """A ws full-state list -> {id: point}, silently dropping garbage."""
    points = {}
    for item in raw if isinstance(raw, list) else []:
        point = sanitize_point(item, room)
        if point is not None and len(points) < MAX_POINTS:
            points[point["id"]] = point
    return points


def current_xy(point, elapsed):
    """The point's (x, y) at `elapsed` seconds into its motion."""
    motion = point.get("motion")
    if not motion:
        return (point["x"], point["y"])
    elapsed = max(0.0, elapsed - float(motion.get("started", 0.0)))
    if motion["type"] == "orbit":
        angle = 2.0 * math.pi * (elapsed / motion["period"])
        return (motion["center"][0] + motion["radius"] * math.cos(angle),
                motion["center"][1] + motion["radius"] * math.sin(angle))
    if motion["type"] == "bounce":
        origin, velocity, bounds = motion["origin"], motion["velocity"], motion["bounds"]
        return (_reflect(origin[0] + velocity[0] * elapsed, bounds[0]),
                _reflect(origin[1] + velocity[1] * elapsed, bounds[1]))
    # path: polyline swept over a duration, equal time per segment
    points = motion["points"]
    if len(points) == 1:
        return tuple(points[0])
    progress = elapsed / motion["duration"]
    progress = progress % 1.0 if motion.get("loop") else min(max(progress, 0.0), 1.0)
    segments = len(points) - 1
    span = progress * segments
    index = min(int(span), segments - 1)
    local = span - index
    a, b = points[index], points[index + 1]
    return (a[0] + (b[0] - a[0]) * local, a[1] + (b[1] - a[1]) * local)


def is_dynamic(point):
    """True when the point moves over time -- the broadcast loop must tick;
    a static point applies in one frame and silence = hold does the rest."""
    motion = point.get("motion")
    if not motion:
        return False
    return motion["type"] in ("orbit", "bounce") or len(motion["points"]) > 1


def frame_args(points, elapsed):
    """Wire args for one atomic /pt frame: [n, <id x y r f> * n]."""
    args = [len(points)]
    for point_id in sorted(points):
        point = points[point_id]
        x, y = current_xy(point, elapsed)
        args += [int(point_id), float(x), float(y),
                 float(point["r"]), int(point["falloff"])]
    return args


def sparse_args(point, elapsed):
    """Wire args for the sparse upsert form: [id, x, y, r, f]."""
    x, y = current_xy(point, elapsed)
    return [int(point["id"]), float(x), float(y),
            float(point["r"]), int(point["falloff"])]


def _falloff_enum(value):
    if value in FALLOFF_ENUMS:
        return FALLOFF_ENUMS[value]
    try:
        enum = int(value)
    except (TypeError, ValueError):
        return DEFAULT_FALLOFF
    return enum if enum in FALLOFF_ENUMS.values() else DEFAULT_FALLOFF


def _sanitize_motion(motion, room=None, origin=None):
    if not isinstance(motion, dict):
        return None
    kind = motion.get("type")
    if kind == "orbit":
        center = _coerce_point(motion.get("center"))
        if center is None:
            return None
        return {"type": "orbit", "center": center,
                "radius": _clamp_float(motion.get("radius"), 2.0, 0.0, 1000.0),
                "period": _clamp_float(motion.get("period"), 8.0, 0.1, 3600.0)}
    if kind == "bounce":
        room_width, room_depth = _room_bounds(room)
        start = _coerce_point(motion.get("origin")) or list(origin or _center(room))
        velocity = _coerce_point(motion.get("velocity")) or [0.7, 0.45]
        # A stationary axis defeats the purpose of this deliberately two-axis
        # first mover; replace only the zero component with the default.
        if abs(velocity[0]) < 0.001:
            velocity[0] = 0.7
        if abs(velocity[1]) < 0.001:
            velocity[1] = 0.45
        return {"type": "bounce",
                "origin": [min(max(start[0], 0.0), room_width),
                           min(max(start[1], 0.0), room_depth)],
                "velocity": [_clamp_float(velocity[0], 0.7, -100.0, 100.0),
                             _clamp_float(velocity[1], 0.45, -100.0, 100.0)],
                "bounds": [room_width, room_depth]}
    if kind == "path":
        points = [p for p in (_coerce_point(item) for item in
                              (motion.get("points") or [])) if p]
        if not points:
            return None
        return {"type": "path", "points": points,
                "duration": _clamp_float(motion.get("duration"), 8.0, 0.1, 3600.0),
                "loop": bool(motion.get("loop"))}
    return None


def _center(room):
    if isinstance(room, dict) and room.get("width") and room.get("depth"):
        return (float(room["width"]) / 2.0, float(room["depth"]) / 2.0)
    return (5.0, 4.0)


def _room_bounds(room):
    if isinstance(room, dict):
        return (_clamp_float(room.get("width"), 10.0, 0.01, 1000.0),
                _clamp_float(room.get("depth"), 8.0, 0.01, 1000.0))
    return (10.0, 8.0)


def _reflect(value, limit):
    """Triangle-wave reflection into [0, limit], including negative travel."""
    if limit <= 0:
        return 0.0
    wrapped = value % (2.0 * limit)
    return limit - abs(wrapped - limit)


def _coerce_point(value):
    if (isinstance(value, (list, tuple)) and len(value) >= 2
            and _finite(value[0]) and _finite(value[1])):
        return [float(value[0]), float(value[1])]
    return None


def _finite(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _clamp_float(value, fallback, low, high):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    if not math.isfinite(result):
        return fallback
    return min(max(result, low), high)
