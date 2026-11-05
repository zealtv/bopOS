#!/usr/bin/env python3
"""Validate retained transport observations against peer counters."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
result = json.loads((HERE/'monitor-results.json').read_text())
observations = [json.loads(line) for line in (HERE/'ws-observations.jsonl').read_text().splitlines()]
frames, sizes = defaultdict(Counter), defaultdict(Counter)
for row in observations:
    event, phase = row['event'], row['phase']
    frames[phase][event['type']] += 1
    sizes[phase][event['type']] += len(json.dumps(event, ensure_ascii=False,
                                                separators=(',', ':')).encode('utf-8'))
assert result['nodes'] == 50 and result['source_unchanged_during_run']
assert [p['clients'] for p in result['phases']] == [0, 1, 1, 3]
for phase in result['phases']:
    assert phase['elapsed_s'] > 0
    assert phase['queued'] == phase['publications']
    assert sum(phase['tap_classes'].values()) == sum(
        phase['queued'].get(kind, 0) for kind in ('osc_in', 'osc_out'))
    assert len(phase['peers']) == phase['clients']
    if phase['clients']:
        assert frames[phase['name']] == phase['peers'][0]['frames']
        assert sizes[phase['name']] == phase['peers'][0]['bytes']
        # Bounded counting-window edge skew, not a claim of packet loss.
        for peer in phase['peers']:
            sent, received = sum(phase['publications'].values()), sum(peer['frames'].values())
            assert abs(received-sent) <= max(10, .01*sent)
    else:
        assert sum(phase['queued'].values()) > 3000
    assert bool(phase['queued'].get('point_frame', 0)) == phase['moving']
    if phase['moving']:
        assert phase['queued']['point_frame'] == phase['tap_classes']['points']
observed_counts = sum(frames.values(), Counter())
pending = json.loads((HERE/'pending-results.json').read_text())
assert pending['observations'] == len(observations)
assert pending['main_unhandled'] == {'sync': observed_counts['sync']}
assert pending['remote_unhandled'] == {kind: observed_counts[kind] for kind in
    ('osc_in', 'heartbeat', 'osc_out', 'sync', 'point_frame') if observed_counts[kind]}
print('PASS: 50 nodes, four phases, %s retained WS messages, counts/bytes and pending replay' % len(observations))
