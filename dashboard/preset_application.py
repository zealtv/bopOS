"""Pure helpers for preset application, capture, replay, and provenance."""

from __future__ import annotations

import math
import random

from python.paramgen import ParamGrammarError, parse_message


def canonical_float(value):
    """Return the exact numeric value OSCBridge._datagram puts on the wire."""
    return float(format(float(value), ".6g"))


def canonicalize_value(declaration, value):
    """Canonicalize one durable scalar at the shared write boundary."""
    kind = declaration.get("kind") if isinstance(declaration, dict) else None
    if kind == "text":
        return value if isinstance(value, str) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    if kind in {"int", "toggle", "enum"}:
        return int(math.floor(number))
    if kind == "float":
        return canonical_float(number)
    return None


def canonicalize_args(declaration, args):
    """Canonicalize a stored full-state argument list to OSC precision."""
    if not isinstance(args, list) or not args:
        return None
    # Stop is a command, not a durable scalar, but it passes through this
    # shared live-automation boundary after the caller has parsed the grammar.
    # Do not feed it to canonicalize_value(), which correctly rejects strings
    # for numeric declarations.
    if args == ["stop"]:
        return ["stop"]
    if len(args) == 1:
        value = canonicalize_value(declaration, args[0])
        return [value] if value is not None else None
    result = []
    for value in args:
        if isinstance(value, float):
            result.append(canonical_float(value))
        else:
            result.append(value)
    kind = declaration.get("kind") if isinstance(declaration, dict) else None
    if kind == "int":
        try:
            spec = parse_message(result, "i")
        except ParamGrammarError:
            spec = None
        if spec is not None and spec.kind == "fade":
            positional = list(result)
            while positional and isinstance(positional[-1], str) \
                    and positional[-1].startswith(("c:", "curve:")):
                positional.pop()
            if len(positional) == 2:
                value_indexes = (0,)
            elif len(positional) == 3:
                value_indexes = (0, 1)
            else:
                value_indexes = range(0, len(positional), 2)
            for index in value_indexes:
                result[index] = int(math.floor(float(result[index])))
    return result


def automation_key(seat):
    """Return the automation-table key for one concrete target.

    Seats key by their numeric id, which is also their OSC selector. The patch
    editor's audition engine answers on selector 0 but is not Seat 0, so it
    carries an explicit key of its own rather than sharing a real Seat's
    automation entries (08-editor-save-recall).
    """
    key = seat.get("automation_key") if isinstance(seat, dict) else None
    return str(key) if key else str(seat.get("id"))


def automation_spec(entry, declaration):
    if not isinstance(entry, dict) or not isinstance(entry.get("args"), list):
        return None
    try:
        return parse_message(
            entry["args"],
            "f" if declaration.get("kind") == "float" else "i",
        )
    except (ParamGrammarError, AttributeError):
        return None


def automation_active(entry, declaration, now):
    """Derive whether an automation entry still owns replay."""
    spec = automation_spec(entry, declaration)
    if spec is None:
        return False
    if spec.kind in {"lfo", "loop"}:
        return True
    if spec.kind != "fade":
        return False
    sent_at = entry.get("sent_at")
    if isinstance(sent_at, bool) or not isinstance(sent_at, (int, float)):
        return False
    total_ms = sum(segment[1] for segment in spec.segments)
    return (float(now) - float(sent_at)) * 1000.0 < total_ms


def replay_args(seat, declaration, automation, now):
    """Return active automation args, otherwise the durable scalar."""
    identity = declaration["identity"]
    entry = automation.get(automation_key(seat), {}).get(identity)
    if automation_active(entry, declaration, now):
        return canonicalize_args(declaration, entry["args"])
    value = seat.get("params", {}).get(identity)
    canonical = canonicalize_value(declaration, value)
    return [canonical] if canonical is not None else None


def _shape(frac, curve):
    frac = min(1.0, max(0.0, frac))
    if frac == 0.0:
        return 0.0
    try:
        exponent = 2.0 ** curve
    except OverflowError:
        return 0.0 if frac < 1.0 else 1.0
    return frac ** exponent


def _fade_value(spec, entry, elapsed_ms):
    start = spec.start if spec.start is not None else entry.get("from")
    if not isinstance(start, (int, float)) or isinstance(start, bool):
        start = spec.segments[0][0]
    total = sum(duration for _target, duration in spec.segments)
    if spec.kind == "loop" and total > 0:
        elapsed_ms %= total
    elif elapsed_ms >= total:
        return spec.segments[-1][0]
    cursor = float(start)
    offset = 0.0
    for target, duration in spec.segments:
        if elapsed_ms <= offset + duration:
            fraction = 1.0 if duration == 0 else (elapsed_ms - offset) / duration
            return cursor + (target - cursor) * _shape(fraction, spec.curve)
        cursor = target
        offset += duration
    return spec.segments[-1][0]


def _random_value(identity, spec, cycle):
    seed = "{}|{}|{}|{}|{}|{}".format(
        identity, spec.shape, spec.minimum, spec.maximum,
        max(1, int(spec.period * 1e6)), cycle)
    return random.Random(seed).uniform(spec.minimum, spec.maximum)


def _lfo_value(identity, spec, entry, elapsed_ms):
    # Synced LFO entries record the leader phase at send time. Free LFO node
    # phase is intentionally unknowable; using the authored phase is the
    # dashboard-state estimate documented by the application core.
    if not spec.free and isinstance(entry.get("phase_at_send_ms"), (int, float)):
        periods = (float(entry["phase_at_send_ms"]) + elapsed_ms) / spec.period
    else:
        periods = elapsed_ms / spec.period + spec.phase
    cycle = math.floor(periods)
    phase = periods - cycle
    low, high = spec.minimum, spec.maximum
    span = high - low
    if spec.shape == "sine":
        return low + span * (0.5 - 0.5 * math.cos(phase * 2.0 * math.pi))
    if spec.shape == "tri":
        ramp = phase * 2.0 if phase < 0.5 else (1.0 - phase) * 2.0
        return low + span * _shape(ramp, spec.curve)
    if spec.shape == "saw":
        return low + span * _shape(phase, spec.curve)
    if spec.shape == "square":
        return high if phase < 0.5 else low
    first = _random_value(identity, spec, cycle)
    if spec.shape == "sh":
        return first
    second = _random_value(identity, spec, cycle + 1)
    return first + (second - first) * _shape(phase, spec.curve)


def estimate_automation(identity, declaration, entry, now):
    """Evaluate the dashboard's held-value estimate for an explicit Stop."""
    spec = automation_spec(entry, declaration)
    sent_at = entry.get("sent_at") if isinstance(entry, dict) else None
    if (spec is None or spec.kind not in {"fade", "loop", "lfo"}
            or isinstance(sent_at, bool) or not isinstance(sent_at, (int, float))):
        return None
    elapsed_ms = max(0.0, (float(now) - float(sent_at)) * 1000.0)
    if spec.kind in {"fade", "loop"}:
        value = _fade_value(spec, entry, elapsed_ms)
    else:
        value = _lfo_value(identity, spec, entry, elapsed_ms)
    return canonicalize_value(declaration, value)


def capture_params(seats, declarations, automation, now):
    """Capture values all target seats agree on; report mixed omissions."""
    captured = {}
    omitted = []
    for declaration in declarations:
        identity = declaration["identity"]
        values = []
        complete = True
        for seat in seats:
            entry = automation.get(automation_key(seat), {}).get(identity)
            spec = automation_spec(entry, declaration)
            if (spec is not None and spec.kind in {"lfo", "loop"}
                    and automation_active(entry, declaration, now)):
                args = canonicalize_args(declaration, entry["args"])
            else:
                value = canonicalize_value(
                    declaration, seat.get("params", {}).get(identity))
                args = [value] if value is not None else None
            if args is None:
                complete = False
                break
            values.append(args)
        if complete and values and all(value == values[0] for value in values[1:]):
            captured[identity] = values[0]
        else:
            omitted.append(identity)
    return {"params": captured, "omitted": omitted}


def card_preset_projection(seats):
    """Project per-seat provenance using the panel's agree-or-mixed idiom."""
    if not seats:
        return {"preset": None, "dirty": False, "mixed": False}
    markers = [seat.get("applied_preset") for seat in seats]
    if not all(marker == markers[0] for marker in markers[1:]):
        return {"preset": None, "dirty": False, "mixed": True}
    dirty = any(bool(seat.get("preset_dirty")) for seat in seats)
    return {"preset": markers[0], "dirty": dirty, "mixed": False}


def capture_target(seats, all_seats, groups):
    """Return the most portable selector shape for an exact concrete seat set."""
    selected = {int(seat["id"]) for seat in seats}
    every = {int(seat["id"]) for seat in all_seats}
    if selected == every:
        return {"scope": "all", "id": None}
    matches = []
    for raw_group_id in groups:
        group_id = int(raw_group_id)
        members = {int(seat["id"]) for seat in all_seats
                   if group_id in seat.get("groups", [])}
        if members == selected:
            matches.append(group_id)
    if matches:
        return {"scope": "group", "id": min(matches)}
    return {"scope": "seats", "ids": sorted(selected)}


def preset_dirty(document, seat, declarations, automation, effective_patch, now):
    """Derive why one seat differs from its provenance preset, if at all."""
    marker = seat.get("applied_preset")
    if not isinstance(marker, dict):
        return None
    if marker.get("patch") != effective_patch:
        return "foreign-patch"
    if marker.get("patch") != document.get("_patch"):
        return "foreign-patch"
    by_identity = {item["identity"]: item for item in declarations}
    for identity, expected in document.get("params", {}).items():
        declaration = by_identity.get(identity)
        if declaration is None:
            return "deviated"
        entry = automation.get(automation_key(seat), {}).get(identity)
        spec = automation_spec(entry, declaration)
        if len(expected) > 1:
            actual = (canonicalize_args(declaration, entry["args"])
                      if spec is not None
                      and spec.kind in {"lfo", "loop"}
                      and automation_active(entry, declaration, now)
                      else None)
        else:
            value = canonicalize_value(
                declaration, seat.get("params", {}).get(identity))
            actual = [value] if value is not None else None
        if actual != canonicalize_args(declaration, expected):
            return "deviated"
    return None
