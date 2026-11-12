"""Ratified IO control payloads shared by nodes, dashboard and simfleet."""
import copy
import math
import re

ERRORS = frozenset({'no-bus', 'create-failed', 'invalid-arguments',
                    'unknown-command', 'write-failed'})
# Administrative refusals are receipts, never peripheral faults.
WRITE_ERRORS = ERRORS | {'performance'}
RESERVED_NAMES = frozenset({'create', 'poll', 'report', 'scan', 'stream', 'reinit', 'bridge',
                            'key', 'mouse'})


def empty_io(bus=None):
    return {'bus': bus, 'scanned': False, 'addresses': [], 'modules': {}}


def valid_name(value):
    return (isinstance(value, str) and bool(value)
            and not any(c in value for c in '/\x00')
            and value not in RESERVED_NAMES)


def validate_write(value):
    if (not isinstance(value, dict) or set(value) != {'name', 'command', 'args'}
            or not valid_name(value['name'])
            or not isinstance(value['command'], str) or not value['command']
            or '\x00' in value['command'] or not isinstance(value['args'], list)):
        raise ValueError('invalid-arguments')
    for arg in value['args']:
        if (isinstance(arg, bool) or not isinstance(arg, (str, int, float))
                or (isinstance(arg, str) and '\x00' in arg)
                or (isinstance(arg, int) and not -(2**31) <= arg < 2**31)
                or (isinstance(arg, float) and
                    (not math.isfinite(arg) or abs(arg) > 3.402823466e38))):
            raise ValueError('invalid-arguments')
    try:
        for atom in [value['name'], value['command'], *value['args']]:
            if isinstance(atom, str):
                atom.encode('utf-8')
    except UnicodeError:
        raise ValueError('invalid-arguments') from None
    return copy.deepcopy(value)


# Keyboard and pointer input (v1.24, 84-key-input): what the bridge sends the
# engine from a real device, and all a simulated one may send.
INPUT_BUTTONS = frozenset({'left', 'right', 'middle', 'side', 'extra', 'touch'})


def validate_input(address, args):
    """Return (OSC address, args) for one /io/key or /io/mouse message."""
    args = list(args) if isinstance(args, list) else None
    def ints(values, low, high):
        return all(type(v) is int and low <= v <= high for v in values)
    def unit(values):
        return all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in values)
    if args and address == 'key' and len(args) == 2:
        if (isinstance(args[0], str) and re.fullmatch(r'[a-z0-9_]{1,32}', args[0])
                and ints(args[1:], 0, 1)):
            return '/io/key', args
    elif args and address == 'mouse':
        kind, rest = args[0], args[1:]
        if ((kind in INPUT_BUTTONS and len(rest) == 1 and ints(rest, 0, 1))
                or (kind == 'xy' and len(rest) == 2 and unit(rest))
                or (kind == 'move' and len(rest) == 2 and ints(rest, -32768, 32767))
                or (kind in ('wheel', 'hwheel') and len(rest) == 1 and ints(rest, -32, 32))):
            if kind == 'xy':
                rest = [float(v) for v in rest]
            return '/io/mouse', [kind, *rest]
    raise ValueError('invalid-arguments')


def validate_io(value):
    if (not isinstance(value, dict)
            or set(value) != {'bus', 'scanned', 'addresses', 'modules'}
            or not (value['bus'] is None or type(value['bus']) is int and value['bus'] == 1)
            or type(value['scanned']) is not bool
            or not isinstance(value['addresses'], list)
            or not isinstance(value['modules'], dict)):
        raise ValueError('invalid IO object')
    seen = set()
    def address_valid(address):
        return (isinstance(address, str) and re.fullmatch(r'0x[0-9a-f]{2}', address)
                and 3 <= int(address, 16) <= 0x77)
    for row in value['addresses']:
        if (not isinstance(row, dict) or set(row) != {'address', 'claimed'}
                or not address_valid(row['address']) or type(row['claimed']) is not bool
                or row['address'] in seen):
            raise ValueError('invalid IO addresses')
        seen.add(row['address'])
    for name, row in value['modules'].items():
        if (not valid_name(name) or not isinstance(row, dict)
                or set(row) != {'type', 'address', 'state', 'error'}
                or not isinstance(row['type'], str) or not row['type']
                or not address_valid(row['address'])
                or row['state'] not in ('running', 'errored', 'missing')
                or (row['error'] is not None and
                    (not isinstance(row['error'], str) or row['error'] not in ERRORS))):
            raise ValueError('invalid IO module')
    result = copy.deepcopy(value)
    result['addresses'].sort(key=lambda row: int(row['address'], 16))
    return result
