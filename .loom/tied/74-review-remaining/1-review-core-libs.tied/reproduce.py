"""Bounded review reproductions; fixtures live only under /tmp.

Run from repo root: PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python
.loom/threads/74-review-remaining/1-review-core-libs.stitching/reproduce.py
Private generator helpers allow deterministic time without threads/audio.
Assertions describe observed defects, not desired regression behavior.
"""
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools/simfleet.py').is_file())
sys.path.insert(0, str(ROOT))
from python import manifest, paramgen, fetcher, identity, pointfield
from python.store import Store
from dashboard import points


def raises(kind, operation):
    try:
        operation()
    except kind as exc:
        return type(exc).__name__
    raise AssertionError('expected ' + str(kind))


def emit(label, result):
    print(label + ': ' + str(result))


with tempfile.TemporaryDirectory(prefix='bopos-review-74-1-', dir='/tmp') as temporary:
    root = Path(temporary)
    patch = root / 'patch'
    patch.mkdir()
    (patch / 'main.pd').write_text('fixture; never launched')
    base = {'engine': 'pd', 'entrypoint': 'main.pd'}

    # F1: accepted strings are not shell-quoted before the launcher eval.
    marker = root / 'shell-marker'
    candidate = dict(base, engine="pd'; printf reproduced > '" + str(marker) + "'; #")
    (patch / manifest.MANIFEST_NAME).write_text(json.dumps(candidate))
    loaded, error = manifest.load(str(patch))
    assert loaded and error is None
    cli = subprocess.run([sys.executable, str(ROOT / 'python/manifest.py'), str(patch)],
                         check=True, text=True, capture_output=True).stdout
    subprocess.run(['/bin/bash', '-c', cli], check=True, capture_output=True)
    assert marker.read_text() == 'reproduced'
    emit('F1 CLI shell evaluation', marker.read_text())

    # F2: malformed JSON values escape the documented (manifest, error) boundary.
    bad_kind = dict(base, params=[{'name': 'gain', 'kind': []}])
    huge = dict(base, params=[{'name': 'gain', 'kind': 'float', 'default': 10 ** 400}])
    emit('F2 manifest kind/list', raises(TypeError, lambda: manifest.validate(bad_kind, str(patch))))
    emit('F2 manifest huge integer', raises(OverflowError, lambda: manifest.validate(huge, str(patch))))
    emit('F2 entrypoint NUL', raises(ValueError, lambda: manifest.validate(dict(base, entrypoint='main\0.pd'), str(patch))))

    # F3: finite Python values need not be representable on scalar OSC wires.
    for kind, value, tag in [('float', 1e100, '!f'), ('int', 2 ** 31, '!i')]:
        accepted, error = manifest.validate(dict(base, params=[{'name': 'x', 'kind': kind, 'default': value}]), str(patch))
        assert accepted and error is None
        emit('F3 accepted ' + kind, raises((OverflowError, struct.error), lambda: struct.pack(tag, value)))

    engine = paramgen.GeneratorEngine(lambda *_: None, None, now_ns=lambda: 0)
    engine._running = False  # no worker is started; all advancement uses explicit time

    # F4: contract allows loop x y duration; parser silently removes its loop.
    explicit_loop = paramgen.parse_message(['loop', 0, 1, '1s'], 'f')
    assert explicit_loop.kind == 'fade'
    emit('F4 explicit-start loop kind', explicit_loop.kind)

    # F5: sampling only endpoints misses crossings within complete segments/cycles.
    spec = paramgen.parse_message([2, '10ms', 0, '10ms'], 'i')
    slot = engine._make_fade(spec, 'i', 0, 0)
    engine._begin_fade(slot, 0)
    output = engine._advance_fade(slot, paramgen.TICK_NS)
    assert output == []
    emit('F5 int fade expected [1,2,1,0], observed', output)
    loop = paramgen.parse_message(['loop', 2, '30ms', 4, '30ms'], 'i')
    slot = engine._make_fade(loop, 'i', 0, 0)
    engine._begin_fade(slot, 0)
    assert engine._advance_fade(slot, 30_000_000) == [[1], [2]]
    output = engine._advance_fade(slot, 60_000_000)
    assert output == [[0]]
    emit('F5 int loop endpoint expected [3,4,0], observed', output)

    # F6: string durations skip finiteness; precomputation scales with duration.
    overflow_duration = '9' * 400 + 's'
    spec = paramgen.parse_message([1, overflow_duration], 'f')
    assert math.isinf(spec.segments[0][1])
    emit('F6 accepted infinite duration', raises(OverflowError, lambda: engine.apply('gain', spec, {'kind': 'float'})))
    bounded = engine._make_fade(paramgen.parse_message([1, '60s'], 'i'), 'i', 0, 0)
    assert len(bounded['events']) == 2000
    emit('F6 precomputed events even for int / 60s', len(bounded['events']))
    emit('F6 projected events for accepted 1000000h (not allocated)', math.ceil(1_000_000 * 3600 * 1e9 / paramgen.TICK_NS))

    # F7: point sanitization/decoding can throw instead of rejecting a datagram.
    for label, operation, expected in [
        ('dashboard falloff list', lambda: points.sanitize_point({'id': 0, 'falloff': []}), TypeError),
        ('dashboard path points number', lambda: points.sanitize_point({'id': 0, 'motion': {'type': 'path', 'points': 7}}), TypeError),
        ('dashboard id infinity', lambda: points.sanitize_point({'id': float('inf')}), OverflowError),
        ('node id infinity', lambda: pointfield.parse_wire(['pt'], [float('inf'), 0, 0, 1, 0]), OverflowError),
        ('node falloff infinity', lambda: pointfield.parse_wire(['pt'], [0, 0, 0, 1, float('inf')]), OverflowError),
    ]:
        emit('F7 ' + label, raises(expected, operation))
    large = points.sanitize_point({'id': 2 ** 31})
    assert large is not None
    emit('F7 accepted unwireable point id', raises(struct.error, lambda: struct.pack('!i', points.sparse_args(large, 0)[0])))
    assert pointfield.parse_wire(['pt'], [0.9]) == ('frame', {})
    emit('F7 fractional frame count clears all points', pointfield.parse_wire(['pt'], [0.9]))

    # F8: the temporary write path is another perfectly valid key.
    store = Store(str(root / 'store'))
    assert store.put('assignment.tmp', ['precious'])
    assert store.put('assignment', [7])
    assert store.get('assignment.tmp') == []
    emit('F8 assignment.tmp after assignment write', store.get('assignment.tmp'))
    # Fixed tmp path also collides with simultaneous same-key puts; sequential
    # reproduction above needs no timing assumptions.

    # F9: file-fetch follows source file symlinks that canonical identity excludes.
    source = root / 'source'
    source.mkdir()
    outside = root / 'outside.txt'
    outside.write_text('outside source tree')
    (source / 'linked.txt').symlink_to(outside)
    assert identity.directory_manifest(str(source)) == {'files': []}
    ok, detail = fetcher.fetch(source.as_uri(), 'test', str(root / 'assets'))
    assert ok, detail
    assert (root / 'assets/test/linked.txt').read_text() == outside.read_text()
    assert identity.fingerprint(str(source)) != identity.fingerprint(str(root / 'assets/test'))
    emit('F9 file-fetch vs canonical walk', detail + '; source 0 files, destination 1')

    # F10: a completed non-looping path stays dynamic and keeps 25 Hz traffic.
    point = points.sanitize_point({'id': 0, 'motion': {
        'type': 'path', 'points': [[0, 0], [1, 1]], 'duration': 1, 'loop': False}})
    assert points.current_xy(point, 2) == points.current_xy(point, 100) == (1, 1)
    assert points.is_dynamic(point)
    emit('F10 completed path still dynamic', points.is_dynamic(point))

    # Positive guard checks: path traversal and pre-existing destination symlinks.
    for unsafe in ('/abs', '../escape', 'a/../escape', 'a\\..\\escape', 'C:/escape', 'a//b', 'a\0b'):
        raises(ValueError, lambda: fetcher.safe_path(unsafe))
    destination = root / 'assets/unsafe'
    destination.symlink_to(source, target_is_directory=True)
    ok, detail = fetcher.fetch(source.as_uri(), 'unsafe', str(root / 'assets'))
    assert not ok and 'symlink' in detail
    emit('positive fetch path guards', '7 rejected paths; destination symlink rejected')

print('All bounded reproduction assertions passed.')
