"""Pure fixed-stereo matrix model for the audition monitor.

Listener geometry is deliberately outside this module. Callers provide one
``(balance, gain)`` pair per positioned element, where balance is -1 (left) to
+1 (right), and gain is the already-computed distance/level scalar.
"""

import math


FRAME_ADDRESS = "/audition/matrix"
IDENTITY = (1.0, 0.0, 0.0, 1.0)
_SQRT_2 = math.sqrt(2.0)


def _scalar(name, value, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if not lower <= value <= upper:
        raise ValueError(f"{name} must be in [{lower:g}, {upper:g}]")
    return value


def _clean(value):
    if abs(value) < 1e-15:
        return 0.0
    if abs(value - 1.0) < 1e-15:
        return 1.0
    return value


def validate_matrix(matrix):
    """Return a validated ``(l0, l1, r0, r1)`` coefficient tuple."""
    if isinstance(matrix, (str, bytes)):
        raise ValueError("matrix must contain exactly four coefficients")
    try:
        values = tuple(matrix)
    except TypeError as error:
        raise ValueError("matrix must contain exactly four coefficients") from error
    if len(values) != 4:
        raise ValueError("matrix must contain exactly four coefficients")
    return tuple(_scalar(f"matrix[{index}]", value, 0.0, 1.0)
                 for index, value in enumerate(values))


def pd_safe_matrix(matrix):
    """Round a valid matrix to PD-safe six-significant-figure floats."""
    safe = []
    for value in validate_matrix(matrix):
        rounded = float(format(value, ".6g"))
        safe.append(0.0 if rounded == 0.0 else rounded)
    return tuple(safe)


def constant_power_pan(balance, gain=1.0):
    """Return constant-power ``(left, right)`` gains for one mono element."""
    balance = _scalar("balance", balance, -1.0, 1.0)
    gain = _scalar("gain", gain, 0.0, 1.0)
    theta = (balance + 1.0) * math.pi / 4.0
    return (_clean(gain * math.cos(theta)),
            _clean(gain * math.sin(theta)))


def one_position_matrix(balance, gain=1.0):
    """Matrix for one co-located stereo or duplicated-mono position.

    Mid is constant-power panned. Side width is bounded by the quieter pan
    gain, preserving identity at centre and collapsing safely at hard edges.
    """
    gain = _scalar("gain", gain, 0.0, 1.0)
    pan_left, pan_right = constant_power_pan(balance)
    width = min(pan_left, pan_right)
    matrix = (
        gain * (pan_left + width) / _SQRT_2,
        gain * (pan_left - width) / _SQRT_2,
        gain * (pan_right - width) / _SQRT_2,
        gain * (pan_right + width) / _SQRT_2,
    )
    return validate_matrix(_clean(value) for value in matrix)


def two_position_matrix(position_0, position_1):
    """Matrix for two independently positioned mono input channels."""
    balance_0, gain_0 = _position("position_0", position_0)
    balance_1, gain_1 = _position("position_1", position_1)
    left_0, right_0 = constant_power_pan(balance_0, gain_0)
    left_1, right_1 = constant_power_pan(balance_1, gain_1)
    return validate_matrix((left_0, left_1, right_0, right_1))


def _position(name, position):
    if isinstance(position, (str, bytes)):
        raise ValueError(f"{name} must be a (balance, gain) pair")
    try:
        values = tuple(position)
    except TypeError as error:
        raise ValueError(f"{name} must be a (balance, gain) pair") from error
    if len(values) != 2:
        raise ValueError(f"{name} must be a (balance, gain) pair")
    return (_scalar(f"{name}.balance", values[0], -1.0, 1.0),
            _scalar(f"{name}.gain", values[1], 0.0, 1.0))


def matrix_for_positions(positions):
    """Dispatch zero, one, or two positioned elements to the fixed ABI."""
    if isinstance(positions, (str, bytes)):
        raise ValueError("positions must be a sequence")
    try:
        positions = tuple(positions)
    except TypeError as error:
        raise ValueError("positions must be a sequence") from error
    if not positions:
        return IDENTITY
    if len(positions) == 1:
        balance, gain = _position("position_0", positions[0])
        return one_position_matrix(balance, gain)
    if len(positions) == 2:
        return two_position_matrix(positions[0], positions[1])
    raise ValueError("fixed-stereo audition supports at most two positions")


def render(matrix, input_0, input_1):
    """Apply a matrix to one sample pair; useful for fixtures and adapters."""
    l0, l1, r0, r1 = validate_matrix(matrix)
    input_0 = _audio_scalar("input_0", input_0)
    input_1 = _audio_scalar("input_1", input_1)
    return (input_0 * l0 + input_1 * l1,
            input_0 * r0 + input_1 * r1)


def _audio_scalar(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def matrix_frame(matrix):
    """Return the frozen private address followed by four PD-safe floats."""
    return (FRAME_ADDRESS, *pd_safe_matrix(matrix))
