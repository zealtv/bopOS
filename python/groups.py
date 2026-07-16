"""Canonical Seat-group wire validation and selector matching.

This module is deliberately transport-agnostic so the real node, protocol
simulator, and audible virtual nodes cannot acquire subtly different parsers.
"""

INT32_MIN = -(2 ** 31)
INT32_MAX = 2 ** 31 - 1


def group_ids(values):
    """Return a sorted membership tuple, or ``None`` for an invalid full set."""
    result = []
    for value in values:
        # OSC group IDs are int32, not numeric-looking strings or integral
        # floats. bool is also excluded even though it subclasses int.
        if type(value) is not int or not 0 <= value <= INT32_MAX:
            return None
        result.append(value)
    if len(result) != len(set(result)):
        return None
    return tuple(sorted(result))


def stored_group_ids(values):
    """Load persisted membership fail-closed when old/corrupt data is present."""
    parsed = group_ids(values if isinstance(values, (list, tuple)) else ())
    return parsed if parsed is not None else ()


def group_selector(selector):
    """Return the group ID for canonical ``g<id>`` or ``None``."""
    if not isinstance(selector, str) or not selector.startswith("g"):
        return None
    token = selector[1:]
    if not token or (token != "0" and token.startswith("0")) or not token.isascii():
        return None
    if not token.isdecimal():
        return None
    value = int(token)
    return value if value <= INT32_MAX else None


def selector_matches(selector, seat_id, memberships=()):
    """Match ``all``, canonical signed-int32 Seat IDs, or group selectors."""
    if selector == "all":
        return True
    selected_group = group_selector(selector)
    if selected_group is not None:
        try:
            assigned = int(seat_id)
        except (TypeError, ValueError):
            return False
        return assigned != -1 and selected_group in memberships
    try:
        selected = int(selector)
        assigned = int(seat_id)
    except (TypeError, ValueError):
        return False
    return (INT32_MIN <= selected <= INT32_MAX
            and str(selector) == str(selected)
            and selected == assigned)
