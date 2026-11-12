"""Pure listener geometry for the audition monitor.

Installation coordinates are metres with the origin at the top left, x
increasing right, and y increasing down.  Heading is expressed in degrees:
zero points map-up and positive angles turn clockwise.  This module derives
listener-relative stereo balance, smooth distance gain, and a forward-bias
scaling that attenuates elements behind the listener.
"""

import math
from dataclasses import dataclass

try:
    from . import pointfield
except ImportError:  # tools add the repository's python directory to sys.path
    import pointfield

# Directly behind the listener is audible but clearly attenuated
# (~ -9 dB); directly ahead is unity gain. The transition is a smooth
# cosine ramp with no seam at +/-90 degrees (abeam).
REAR_FLOOR = 0.35


def _finite_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


@dataclass(frozen=True)
class Listener:
    """Validated full listener state used by the private audition frame."""

    x: float
    y: float
    heading_deg: float
    range_m: float

    def __post_init__(self):
        x = _finite_number("listener.x", self.x)
        y = _finite_number("listener.y", self.y)
        heading = _finite_number("listener.heading_deg", self.heading_deg) % 360.0
        range_m = _finite_number("listener.range_m", self.range_m)
        if range_m <= 0.0:
            raise ValueError("listener.range_m must be greater than zero")
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "heading_deg", heading)
        object.__setattr__(self, "range_m", range_m)


def listener_from_frame(values):
    """Validate private ``x y heading-deg range-m`` full-state values."""
    if isinstance(values, (str, bytes)):
        raise ValueError("listener frame must contain exactly four values")
    try:
        values = tuple(values)
    except TypeError as error:
        raise ValueError("listener frame must contain exactly four values") from error
    if len(values) != 4:
        raise ValueError("listener frame must contain exactly four values")
    return Listener(*values)


def _position(name, position):
    if isinstance(position, (str, bytes)):
        raise ValueError(f"{name} must be an (x, y) pair")
    try:
        values = tuple(position)
    except TypeError as error:
        raise ValueError(f"{name} must be an (x, y) pair") from error
    if len(values) != 2:
        raise ValueError(f"{name} must be an (x, y) pair")
    return (_finite_number(f"{name}.x", values[0]),
            _finite_number(f"{name}.y", values[1]))


def element_terms(listener, position):
    """Return ``(balance, gain)`` for one installation-space position."""
    if not isinstance(listener, Listener):
        raise ValueError("listener must be a Listener")
    x, y = _position("position", position)
    dx, dy = x - listener.x, y - listener.y
    distance = math.hypot(dx, dy)
    if not math.isfinite(distance):
        raise ValueError("position distance must be finite")
    if distance == 0.0:
        return (0.0, 1.0)

    heading = math.radians(listener.heading_deg)
    right_x, right_y = math.cos(heading), math.sin(heading)
    balance = (dx * right_x + dy * right_y) / distance
    balance = max(-1.0, min(1.0, balance))

    # Forward vector: heading 0 is map-up (0, -1), positive clockwise,
    # derived the same way as the right vector above (right rotated -90
    # degrees).
    forward_x, forward_y = math.sin(heading), -math.cos(heading)
    cos_theta = (dx * forward_x + dy * forward_y) / distance
    cos_theta = max(-1.0, min(1.0, cos_theta))
    forward = REAR_FLOOR + (1 - REAR_FLOOR) * (1 + cos_theta) / 2

    gain = pointfield.falloff(pointfield.SMOOTH, distance, listener.range_m) * forward
    return (balance, gain)


def terms_for_positions(listener, positions):
    """Return ordered geometry terms for any number of element positions."""
    if not isinstance(listener, Listener):
        raise ValueError("listener must be a Listener")
    if isinstance(positions, (str, bytes)):
        raise ValueError("positions must be a sequence of (x, y) pairs")
    try:
        positions = tuple(positions)
    except TypeError as error:
        raise ValueError("positions must be a sequence of (x, y) pairs") from error
    validated = tuple(_position(f"positions[{index}]", position)
                      for index, position in enumerate(positions))
    return tuple(element_terms(listener, position) for position in validated)
