#!/usr/bin/env python3
"""Check subscribed runs against real transport observations, not estimates."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
directory = Path(sys.argv[1])
result = json.loads((directory/'monitor-results.json').read_text())
assert result['source_unchanged_during_run'] and result['nodes'] in (50, 100)
counts, sizes = defaultdict(Counter), defaultdict(Counter)
for line in (directory/'ws-observations.jsonl').read_text().splitlines():
    row = json.loads(line)
    event = row['event']
    wire_bytes = len(json.dumps(event, ensure_ascii=True, separators=(',', ':')).encode())
    counts[row['phase']][event['type']] += 1
    sizes[row['phase']][event['type']] += wire_bytes
    assert event['type'] == 'telemetry'
    assert wire_bytes <= 32 * 1024
    assert event['data']['generation'] == 1
    assert len(event['data']['entries']) <= 100
    assert not any(entry['type'] in ('osc_in', 'osc_out', 'sync')
                   for entry in event['data']['entries'])
    assert all(channel.get('dropped_since_subscribe', 0) == 0
               for name, channel in event['data']['status'].items() if name != 'rates')
for phase in result['phases']:
    assert phase['publication_tasks'] == 0
    assert not phase['publications']
    assert len(phase['peers']) == phase['clients']
    if phase['clients']:
        assert counts[phase['name']] == phase['peers'][0]['frames']
        assert sizes[phase['name']] == phase['peers'][0]['bytes']
        for peer in phase['peers']:
            assert sum(peer['frames'].values()) <= phase['elapsed_s'] * 10 + 1
    assert bool(phase['queued'].get('point_frame', 0)) == phase['moving']
print('PASS: %s nodes; exact recorded bytes/counts; zero publication tasks/raw frames/drops; bounded batches and <=10 frames/s/client' % result['nodes'])
