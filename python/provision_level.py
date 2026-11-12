"""Preflight privileged requirements before changing a node checkout.

Bump systemd/provision-level whenever new root-owned pieces are required.
The installed marker is root-owned; an absent marker means level zero.
"""
from pathlib import Path

MARKER = '/etc/bopos/provision-level'
REQUIREMENT = 'systemd/provision-level'


def read_level(path):
    try:
        value = Path(path).read_text().strip()
    except FileNotFoundError:
        return 0
    if not value.isdecimal():
        raise ValueError('invalid provision level')
    return int(value)


def incoming(root, ref, run):
    """Pin the fetched revision and inspect its requirement without checkout."""
    def git(*args):
        result = run(['git'] + list(args), root, 15)
        if result['timed_out'] or result['returncode']:
            raise ValueError('cannot inspect incoming framework')
        return result['stdout'].strip()

    revision = git('rev-parse', '--verify', ref + '^{commit}')
    present = git('ls-tree', '--name-only', revision, '--', REQUIREMENT)
    required = git('show', revision + ':' + REQUIREMENT) if present else '0'
    if not required.isdecimal():
        raise ValueError('invalid incoming provision level')
    return revision, int(required)


def preflight(root, ref, run):
    try:
        revision, required = incoming(root, ref, run)
        if read_level(MARKER) < required:
            return revision, {'status': 'err', 'phase': 'provision'}
        return revision, None
    except (OSError, ValueError):
        # A damaged requirement/marker must never authorize a checkout.
        return None, {'status': 'err', 'phase': 'provision'}
