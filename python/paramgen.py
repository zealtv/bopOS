"""Parser and node-side generators for numeric patch parameters."""

import math
import random
import re
import threading
import time


TICK_NS = 30_000_000
_DURATION = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(ms|s|m|h)\Z")
_OPTION = re.compile(r"(c|curve|p|phase):(.*)\Z")
_SHAPES = {"sine", "tri", "saw", "square", "sh", "drift"}


class ParamGrammarError(ValueError):
    pass


class ParamSpec:
    def __init__(self, kind, **values):
        self.kind = kind
        self.__dict__.update(values)

    def __repr__(self):
        values = {key: value for key, value in self.__dict__.items() if key != "kind"}
        return "ParamSpec({!r}, {})".format(self.kind, values)


def _number(value, label="value"):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ParamGrammarError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ParamGrammarError(f"{label} must be finite")
    return result


def _duration(value, label="duration"):
    if isinstance(value, bool):
        raise ParamGrammarError(f"{label} must be a duration")
    if isinstance(value, (int, float)):
        result = _number(value, label)
    elif isinstance(value, str):
        match = _DURATION.fullmatch(value)
        if match is None:
            raise ParamGrammarError(f"bad {label} {value!r}")
        result = float(value[:-len(match.group(1))])
        result *= {"ms": 1.0, "s": 1000.0, "m": 60000.0,
                   "h": 3600000.0}[match.group(1)]
    else:
        raise ParamGrammarError(f"{label} must be a duration")
    if result < 0:
        raise ParamGrammarError(f"{label} must not be negative")
    return result


def _options(values):
    positional = list(values)
    options = {"curve": 0.0, "phase": 0.0, "free": False}
    seen = set()
    while positional and isinstance(positional[-1], str):
        token = positional[-1]
        match = _OPTION.fullmatch(token)
        if token in ("f", "free"):
            name, value = "free", True
        elif match is not None:
            name = "curve" if match.group(1) in ("c", "curve") else "phase"
            try:
                value = float(match.group(2))
            except ValueError:
                raise ParamGrammarError(f"bad option {token!r}")
            if not math.isfinite(value):
                raise ParamGrammarError(f"bad option {token!r}")
            if name == "phase" and not 0.0 <= value <= 1.0:
                raise ParamGrammarError("phase must be between 0 and 1")
        else:
            break
        if name in seen:
            raise ParamGrammarError(f"duplicate {name} option")
        seen.add(name)
        options[name] = value
        positional.pop()
    return positional, options, seen


def _fade(values, loop, curve):
    count = len(values)
    if count == 1:
        return ParamSpec("set", value=_number(values[0]))
    if count == 2:
        segments = [(_number(values[0]), _duration(values[1]))]
        return ParamSpec("fade", segments=segments, start=None, curve=curve)
    if count == 3:
        start = _number(values[0])
        segments = [(_number(values[1]), _duration(values[2]))]
        return ParamSpec("fade", segments=segments, start=start, curve=curve)
    if count >= 4 and count % 2 == 0:
        segments = [(_number(values[index]), _duration(values[index + 1]))
                    for index in range(0, count, 2)]
        return ParamSpec("loop" if loop else "fade", segments=segments,
                         start=None, curve=curve)
    if count >= 5:
        raise ParamGrammarError("fade segment list must contain destination/duration pairs")
    raise ParamGrammarError("bad fade arity")


def parse_message(args, param_type):
    """Parse OSC-decoded arguments into a :class:`ParamSpec`."""
    if param_type not in ("f", "i"):
        raise ParamGrammarError("automation requires a numeric declaration")
    if not args:
        raise ParamGrammarError("parameter message has no arguments")
    values, options, seen = _options(args)
    if not values:
        raise ParamGrammarError("parameter message contains only options")
    head = values[0]
    if head == "stop":
        if len(values) != 1 or seen:
            raise ParamGrammarError("stop takes no arguments or options")
        return ParamSpec("stop")
    if head == "lfo":
        if len(values) != 5:
            raise ParamGrammarError("lfo requires shape, min, max, and period")
        shape = values[1]
        if shape not in _SHAPES:
            raise ParamGrammarError(f"unknown lfo shape {shape!r}")
        period = _duration(values[4], "period")
        if period <= 0:
            raise ParamGrammarError("lfo period must be greater than zero")
        return ParamSpec("lfo", shape=shape, minimum=_number(values[2], "minimum"),
                         maximum=_number(values[3], "maximum"), period=period,
                         curve=options["curve"], phase=options["phase"],
                         free=options["free"])
    if "phase" in seen or "free" in seen:
        raise ParamGrammarError("phase/free options are lfo-only")
    loop = head == "loop"
    if loop:
        values = values[1:]
        if not values:
            raise ParamGrammarError("loop requires a fade form")
    elif isinstance(head, str):
        raise ParamGrammarError(f"unknown keyword or option {head!r}")
    result = _fade(values, loop and len(values) >= 3, options["curve"])
    if result.kind == "set" and "curve" in seen:
        raise ParamGrammarError("curve option requires a fade, loop, or lfo")
    return result


def _shape(frac, curve):
    frac = min(1.0, max(0.0, frac))
    if frac == 0.0:
        return 0.0
    try:
        exponent = 2.0 ** curve
    except OverflowError:
        return 0.0 if frac < 1.0 else 1.0
    return frac ** exponent


class GeneratorEngine:
    """One lazily scheduled generator slot per canonical parameter identity."""

    def __init__(self, emit, sync_state, now_ns=time.monotonic_ns):
        self._emit = emit
        self._sync = sync_state
        self._now = now_ns
        self._slots = {}
        self._condition = threading.Condition()
        self._thread = None
        self._running = True

    def close(self):
        with self._condition:
            self._running = False
            self._condition.notify_all()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None

    def _start_locked(self):
        if self._thread is None and self._running:
            self._thread = threading.Thread(target=self._loop, name="param-generator",
                                            daemon=True)
            self._thread.start()

    def apply(self, identity, spec, declaration):
        emissions = []
        with self._condition:
            now = self._now()
            current = self._current_locked(identity, now)
            if current is None:
                default = declaration.get("default", 0.0)
                current = float(default) if isinstance(default, (int, float)) else 0.0
            param_type = declaration.get("type")
            if param_type not in ("f", "i"):
                raise ValueError("generator declaration must be numeric")
            if spec.kind == "stop":
                slot = {"kind": "constant", "value": current, "type": param_type}
                emissions.append([int(math.floor(current))] if param_type == "i" else [current])
            elif spec.kind == "set":
                value = math.floor(spec.value) if param_type == "i" else spec.value
                slot = {"kind": "constant", "value": value, "type": param_type}
                emissions.append([int(value)] if param_type == "i" else [value])
            elif spec.kind in ("fade", "loop"):
                start = spec.start if spec.start is not None else current
                slot = self._make_fade(spec, param_type, start, now)
                emissions.extend(self._begin_fade(slot, now))
            else:
                slot = self._make_lfo(identity, spec, param_type, now)
                emissions.extend(self._begin_lfo(slot, now))
            self._slots[identity] = slot
            if slot["kind"] != "constant":
                self._start_locked()
            self._condition.notify_all()
            # Keep replacement and its first output ordered against scheduler
            # output: otherwise an old slot can speak after "last wins".
            for args in emissions:
                self._emit(identity, args)
        return True

    def current_value(self, identity):
        with self._condition:
            return self._current_locked(identity, self._now())

    def _make_fade(self, spec, param_type, start, now):
        segments = []
        cursor = float(start)
        elapsed = 0
        for target, duration_ms in spec.segments:
            duration_ns = int(duration_ms * 1e6)
            segments.append((cursor, float(target), duration_ns, elapsed))
            cursor = float(target)
            elapsed += duration_ns
        return {"kind": spec.kind, "type": param_type, "segments": segments,
                "curve": spec.curve, "start_ns": now, "total_ns": elapsed,
                "last_int": math.floor(start), "next_due": now,
                "explicit": spec.start is not None, "emission_index": 0,
                "events": self._fade_events(segments, spec.curve)}

    def _fade_events(self, segments, curve):
        events = []
        for start, target, duration, offset in segments:
            count = max(1, int(math.ceil(duration / TICK_NS)))
            for index in range(count):
                frac = (index + 1) / count
                value = start + (target - start) * _shape(frac, curve)
                due = offset + int(duration * (index + 1) / count)
                events.append((due, value))
        return events

    def _begin_fade(self, slot, now):
        result = []
        if slot["type"] == "i":
            if slot["explicit"]:
                result.append([int(slot["last_int"])])
            slot["next_due"] = now + TICK_NS
        else:
            if slot["explicit"]:
                result.append([slot["segments"][0][0]])
            slot["next_due"] = self._next_float_due(slot)
        return result

    def _make_lfo(self, identity, spec, param_type, now):
        return {"kind": "lfo", "type": param_type, "identity": identity,
                "shape": spec.shape, "minimum": spec.minimum, "maximum": spec.maximum,
                "period_ns": max(1, int(spec.period * 1e6)), "curve": spec.curve,
                "phase": random.random() if spec.free else spec.phase,
                "free": spec.free, "start_ns": now, "next_due": now,
                "last_int": None}

    def _begin_lfo(self, slot, now):
        if slot["type"] == "i":
            value = math.floor(self._lfo_value(slot, now))
            slot["last_int"] = value
            slot["next_due"] = now + TICK_NS
            return [[int(value)]]
        slot["next_due"] = now + TICK_NS
        return [[self._lfo_value(slot, now)]]

    def _leader_now(self, slot, now):
        if slot["free"]:
            return now - slot["start_ns"]
        if self._sync is not None and self._sync.synced():
            return now - self._sync.offset()
        return now

    def _random_value(self, slot, cycle):
        seed = "{}|{}|{}|{}|{}|{}".format(
            slot["identity"], slot["shape"], slot["minimum"], slot["maximum"],
            slot["period_ns"], cycle)
        return random.Random(seed).uniform(slot["minimum"], slot["maximum"])

    def _lfo_value(self, slot, now):
        periods = self._leader_now(slot, now) / slot["period_ns"] + slot["phase"]
        cycle = math.floor(periods)
        phase = periods - cycle
        low, high = slot["minimum"], slot["maximum"]
        span = high - low
        shape = slot["shape"]
        if shape == "sine":
            return low + span * (0.5 - 0.5 * math.cos(phase * 2.0 * math.pi))
        if shape == "tri":
            ramp = phase * 2.0 if phase < 0.5 else (1.0 - phase) * 2.0
            return low + span * _shape(ramp, slot["curve"])
        if shape == "saw":
            return low + span * _shape(phase, slot["curve"])
        if shape == "square":
            return high if phase < 0.5 else low
        first = self._random_value(slot, cycle)
        if shape == "sh":
            return first
        second = self._random_value(slot, cycle + 1)
        return first + (second - first) * _shape(phase, slot["curve"])

    def _fade_value(self, slot, now):
        elapsed = max(0, now - slot["start_ns"])
        total = slot["total_ns"]
        if slot["kind"] == "loop" and total > 0:
            elapsed %= total
        elif elapsed >= total:
            return slot["segments"][-1][1]
        for start, target, duration, offset in slot["segments"]:
            if elapsed <= offset + duration:
                frac = 1.0 if duration == 0 else (elapsed - offset) / duration
                return start + (target - start) * _shape(frac, slot["curve"])
        return slot["segments"][-1][1]

    def _current_locked(self, identity, now):
        slot = self._slots.get(identity)
        if slot is None:
            return None
        if slot["kind"] == "constant":
            return slot["value"]
        if slot["kind"] in ("fade", "loop"):
            return self._fade_value(slot, now)
        return self._lfo_value(slot, now)

    def _next_float_due(self, slot):
        index = slot["emission_index"]
        if index < len(slot["events"]):
            return slot["start_ns"] + slot["events"][index][0]
        return slot["start_ns"] + slot["total_ns"]

    @staticmethod
    def _crossings(last, current):
        if current > last:
            return [[value] for value in range(last + 1, current + 1)]
        if current < last:
            return [[value] for value in range(last - 1, current - 1, -1)]
        return []

    def _advance_fade(self, slot, now):
        result = []
        if (slot["kind"] == "loop" and slot["type"] == "i"
                and slot["total_ns"] > 0
                and now >= slot["start_ns"] + slot["total_ns"]):
            cycles = max(1, (now - slot["start_ns"]) // slot["total_ns"])
            slot["start_ns"] += cycles * slot["total_ns"]
            snapped = math.floor(slot["segments"][0][0])
            result.append([int(snapped)])
            slot["last_int"] = snapped
        if slot["type"] == "i":
            current = math.floor(self._fade_value(slot, now))
            result.extend(self._crossings(slot["last_int"], current))
            slot["last_int"] = current
            slot["next_due"] = now + TICK_NS
        else:
            while (slot["emission_index"] < len(slot["events"])
                   and now >= slot["start_ns"] + slot["events"][slot["emission_index"]][0]):
                _due, value = slot["events"][slot["emission_index"]]
                result.append([value])
                slot["emission_index"] += 1
            slot["next_due"] = self._next_float_due(slot)
        if now >= slot["start_ns"] + slot["total_ns"]:
            final = slot["segments"][-1][1]
            if slot["kind"] == "loop" and slot["total_ns"] > 0:
                cycles = max(1, (now - slot["start_ns"]) // slot["total_ns"])
                slot["start_ns"] += cycles * slot["total_ns"]
                slot["emission_index"] = 0
                start = slot["segments"][0][0]
                if slot["type"] == "i":
                    slot["next_due"] = slot["start_ns"] + TICK_NS
                else:
                    if not slot["explicit"]:
                        result.append([start])
                    result.extend(self._begin_fade(slot, slot["start_ns"]))
            else:
                param_type = slot["type"]
                slot.clear()
                slot.update({"kind": "constant", "type": param_type,
                             "value": math.floor(final) if param_type == "i" else final})
        return result

    def _advance_lfo(self, slot, now):
        if slot["type"] == "i":
            current = math.floor(self._lfo_value(slot, now))
            result = self._crossings(slot["last_int"], current)
            slot["last_int"] = current
        else:
            result = [[self._lfo_value(slot, now)]]
        slot["next_due"] = now + TICK_NS
        return result

    def _loop(self):
        while True:
            emissions = []
            with self._condition:
                if not self._running:
                    return
                now = self._now()
                nearest = None
                for identity, slot in list(self._slots.items()):
                    due = slot.get("next_due")
                    if due is not None and now >= due:
                        values = (self._advance_lfo(slot, now) if slot["kind"] == "lfo"
                                  else self._advance_fade(slot, now))
                        emissions.extend((identity, args) for args in values)
                        due = slot.get("next_due")
                    if due is not None:
                        nearest = due if nearest is None else min(nearest, due)
                timeout = None if nearest is None else max(0.0, (nearest - self._now()) / 1e9)
                if not emissions:
                    self._condition.wait(timeout=timeout)
                    continue
                for identity, args in emissions:
                    self._emit(identity, args)
