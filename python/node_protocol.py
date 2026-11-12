"""Transport-free device administration grammar and replies (OSC contract §5–7).

Adapters own observations, effects, completion timing and OSC encoding. Replies
are (address, values, tags); tags omit the OSC comma and must survive encoding.
"""
import json
import math
import re

import groups
import io_protocol
import osc_contract

HOSTNAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
UID_ADMIN_VERBS = frozenset({
    'identify', 'report', 'reboot', 'shutdown', 'restart-engine', 'updatebopos', 'unassign',
})
REPORT_FIELDS = frozenset('''uid hostname engine has_i2c has_wifi audio_channels screen
    patch uptime git_rev update_model groups device_enabled mute_all output_enabled
    performance audio log wifi io'''.split())
# Optional fact, sent when the adapter has one: the node's display version
# (version_identity.py), "1.0.0" or "1.0.0+dev.12.gabc1234" (contract 1.26).
# Old nodes omit it, so consumers must treat absence as "not reported".
OPTIONAL_REPORT_FIELDS = frozenset(['release'])


def switch(value):
    """Exact numeric 0/1, never truncation or numeric-looking text."""
    return int(value) if type(value) in (int, float) and value in (0, 1) else None


def assignment(args):
    if len(args) < 3 or not isinstance(args[0], str) or not isinstance(args[2], str):
        return None
    value = args[1]
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not 0 <= value <= groups.INT32_MAX or value != int(value)):
        return None
    flat = args[3:]
    if len(flat) % 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in flat):
        return None
    positions = tuple((float(flat[i]), float(flat[i + 1])) for i in range(0, len(flat), 2))
    return args[0], int(value), args[2], positions


def sync_ping(args):
    return (len(args) == 2 and type(args[0]) is int
            and groups.INT32_MIN <= args[0] <= groups.INT32_MAX
            and isinstance(args[1], str))


def sync_pong(uid, args, now_ns):
    return '/sync/pong', (args[0], args[1], uid, str(now_ns)), 'isss'


def uid_envelope(uid, args):
    if (len(args) >= 2 and isinstance(args[0], str) and args[0] == uid
            and isinstance(args[1], str)):
        return args[1], list(args[2:])
    return None


def json_reply(address, payload, *prefix):
    values = (*prefix, json.dumps(payload, separators=(',', ':')))
    return address, values, 's' * len(values)


def report(release=None, **facts):
    # Missing facts are adapter bugs, not invented defaults/capabilities.
    if facts.keys() != REPORT_FIELDS:
        raise ValueError('incomplete report facts: ' + str(REPORT_FIELDS ^ facts.keys()))
    if release is not None:
        facts['release'] = str(release)
    return json_reply('/os/report', dict(facts, contract_version=osc_contract.VERSION))


def revision(version, update_model, uid, status=None, phase=None):
    values = (str(version), update_model, uid)
    if status is not None:
        values += (str(status), str(phase or 'unknown'))
    return '/os/rev', values, 's' * len(values)


def enabled(uid, value, output):
    return '/os/enabled', (uid, int(value), int(output)), 'sii'


def hostname(uid, name, status):
    return '/os/hostname', (uid, name, status), 'sss'


def memberships(uid, values):
    return '/os/groups', (uid, *values), 's' + 'i' * len(values)


def pong(uid, token, tag):
    return '/os/pong', (token, uid), (tag, 's')


def io_reply(uid, kind, payload, error=None):
    if kind == 'scan':
        return '/os/io-scan', (uid, json.dumps(payload)), 'ss'
    keys = ('name', 'command') if kind == 'write' else ('name',)
    result = {key: payload[key] for key in keys}
    result['error'] = error
    return '/os/io-' + kind, (uid, 'err' if error else 'ok', json.dumps(result)), 'sss'


def write_payload(raw):
    """Keep attributable strings on invalid input, as IOControl always has."""
    value = None
    try:
        value = json.loads(raw)
        return io_protocol.validate_write(value), None
    except (ValueError, TypeError):
        value = value if isinstance(value, dict) else {}
        return {key: value.get(key) if isinstance(value.get(key), str)
                else ('bridge' if key == 'name' else '')
                for key in ('name', 'command')}, 'invalid-arguments'


def patch_row(name, active, valid, fingerprint=None):
    row = dict(name=name, active=bool(active), manifest=bool(valid))
    if fingerprint:
        row['fingerprint'] = fingerprint
    return row
