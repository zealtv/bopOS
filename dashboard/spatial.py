"""Spatial automation math (spatial-audio Stage A, spatial-0).

Pure, side-effect-free: a spatial *configuration* (a moving point + a falloff
curve) plus a device position resolve to a per-device gain factor in [0, 1].
The dashboard multiplies that factor into the volume param it already sends
(stored mix x master x spatial -- see osc_bridge.send_device_param), so this
module knows nothing about OSC, state, or persistence.

Designed as mask -> per-device value from day one (spatial-0 brief): point +
radius + falloff is the first mask. `device_factor` is the seam a video or
node-side mask slots into later -- it maps a device position to a scalar.

Coordinates are the installation's floor-plan metres (state.DEFAULT_ROOM:
origin top-left, x right, y down). Positions come from device["pos1"].
"""
import math


# --- falloff curves: distance d (m) and radius R (m) -> gain in [0, 1] -------
# Each is a pure function of d/R. `radius` is the characteristic distance:
# linear/smooth reach zero at d == R; gauss treats R as sigma (e^-1 at d == R,
# never hard zero -- physical tails).

def _linear(ratio):
    return max(0.0, 1.0 - ratio)


def _smooth(ratio):
    # smoothstep on the linear ramp: flat top near the point, soft knee at R
    x = min(max(1.0 - ratio, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def _gauss(ratio):
    return math.exp(-(ratio * ratio))


FALLOFFS = {"linear": _linear, "smooth": _smooth, "gauss": _gauss}
DEFAULT_FALLOFF = "smooth"
DEFAULT_RADIUS = 3.0            # metres
DEFAULT_RATE = 25              # Hz, dashboard-computed send rate (contract sec 4)
MIN_RATE, MAX_RATE = 1, 40


def falloff(name, distance, radius):
    """Gain in [0, 1] for a device `distance` m from the point, given `radius`."""
    if radius <= 0:
        return 0.0
    curve = FALLOFFS.get(name, FALLOFFS[DEFAULT_FALLOFF])
    return max(0.0, min(1.0, curve(distance / radius)))


# --- motion: a config + elapsed seconds -> the point's current (x, y) --------
# static (fixed / drag target), path (polyline swept over a duration), and
# orbit (circular LFO). spatial-1's drag just replaces the static point.

def current_point(motion, elapsed):
    """Current (x, y) of the moving point, or None if the motion is malformed."""
    if not isinstance(motion, dict):
        return None
    kind = motion.get("type")
    if kind == "static":
        point = motion.get("point")
        return tuple(point) if _is_point(point) else None
    if kind == "orbit":
        center, radius = motion.get("center"), motion.get("radius")
        period = motion.get("period") or 8.0
        if not _is_point(center) or not _finite(radius) or period <= 0:
            return None
        angle = 2.0 * math.pi * (elapsed / period)
        return (center[0] + radius * math.cos(angle),
                center[1] + radius * math.sin(angle))
    if kind == "path":
        points = motion.get("points")
        duration = motion.get("duration") or 8.0
        if not isinstance(points, list) or not points or duration <= 0:
            return None
        if len(points) == 1:
            return tuple(points[0]) if _is_point(points[0]) else None
        progress = elapsed / duration
        progress = progress % 1.0 if motion.get("loop") else min(max(progress, 0.0), 1.0)
        # equal time per segment (uniform in parameter, not arc length); for the
        # common straight sweep (2 points) the two are identical anyway
        segments = len(points) - 1
        span = progress * segments
        index = min(int(span), segments - 1)
        local = span - index
        a, b = points[index], points[index + 1]
        if not (_is_point(a) and _is_point(b)):
            return None
        return (a[0] + (b[0] - a[0]) * local, a[1] + (b[1] - a[1]) * local)
    return None


def device_factor(config, position, elapsed):
    """Spatial gain factor in [0, 1] for a device at `position` ([x, y] m).

    Returns 1.0 (spatial does not touch the device) when the layer is inactive,
    the device is unpositioned, or the motion is malformed -- so an unplaced box
    keeps its plain stored x master gain rather than being silenced.
    """
    if not config or not config.get("active"):
        return 1.0
    if not _is_point(position):
        return 1.0
    point = current_point(config.get("motion"), elapsed)
    if point is None:
        return 1.0
    distance = math.hypot(position[0] - point[0], position[1] - point[1])
    return falloff(config.get("falloff", DEFAULT_FALLOFF), distance,
                   config.get("radius", DEFAULT_RADIUS))


def is_dynamic(config):
    """True when the point moves over time (path/orbit) -- callers may keep
    ticking; a static point applies once and needs no further sends."""
    if not config or not config.get("active"):
        return False
    motion = config.get("motion") or {}
    if motion.get("type") == "orbit":
        return True
    if motion.get("type") == "path":
        points = motion.get("points")
        return isinstance(points, list) and len(points) > 1
    return False


# --- validation: untrusted ws payload -> a normalized config ------------------

def sanitize(raw, room=None):
    """Coerce a ws `set_spatial` payload into a safe, fully-populated config.

    Never raises; unknown/garbage fields fall back to defaults. A malformed
    motion becomes a static point at room centre so the layer is always
    well-formed once active.
    """
    raw = raw if isinstance(raw, dict) else {}
    return {
        "active": bool(raw.get("active")),
        "radius": _clamp_float(raw.get("radius"), DEFAULT_RADIUS, 0.01, 1000.0),
        "falloff": raw.get("falloff") if raw.get("falloff") in FALLOFFS else DEFAULT_FALLOFF,
        "rate": _clamp_int(raw.get("rate"), DEFAULT_RATE, MIN_RATE, MAX_RATE),
        "motion": _sanitize_motion(raw.get("motion"), room),
    }


def default_config(room=None):
    return {"active": False, "radius": DEFAULT_RADIUS, "falloff": DEFAULT_FALLOFF,
            "rate": DEFAULT_RATE, "motion": _center_static(room)}


def _sanitize_motion(motion, room):
    if not isinstance(motion, dict):
        return _center_static(room)
    kind = motion.get("type")
    if kind == "static":
        point = _coerce_point(motion.get("point"))
        return {"type": "static", "point": point or list(_center(room))}
    if kind == "orbit":
        center = _coerce_point(motion.get("center")) or list(_center(room))
        return {"type": "orbit", "center": center,
                "radius": _clamp_float(motion.get("radius"), 2.0, 0.0, 1000.0),
                "period": _clamp_float(motion.get("period"), 8.0, 0.1, 3600.0)}
    if kind == "path":
        points = [p for p in (_coerce_point(item) for item in
                              (motion.get("points") or [])) if p]
        if not points:
            return _center_static(room)
        return {"type": "path", "points": points,
                "duration": _clamp_float(motion.get("duration"), 8.0, 0.1, 3600.0),
                "loop": bool(motion.get("loop"))}
    return _center_static(room)


def _center(room):
    if isinstance(room, dict) and room.get("width") and room.get("depth"):
        return (float(room["width"]) / 2.0, float(room["depth"]) / 2.0)
    return (5.0, 4.0)


def _center_static(room):
    return {"type": "static", "point": list(_center(room))}


def _coerce_point(value):
    if _is_point(value):
        return [float(value[0]), float(value[1])]
    return None


def _is_point(value):
    return (isinstance(value, (list, tuple)) and len(value) >= 2
            and _finite(value[0]) and _finite(value[1]))


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _clamp_float(value, fallback, low, high):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    if not math.isfinite(result):
        return fallback
    return min(max(result, low), high)


def _clamp_int(value, fallback, low, high):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return fallback
    return min(max(result, low), high)
