#!/usr/bin/env python3
"""Check retained measurement completeness and independently encoded sizes."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from measure_traffic import datagram, model, parse_fires, spread_stats, summary

here = Path(__file__).resolve().parent
results = json.loads((here / 'traffic-results.json').read_text())
stamp = '123456789012345'
uid = '02:53:49:4d:00:01'
assert len(datagram('/sync/ping', [123, stamp])) == 36
assert len(datagram('/sync/query', [123, stamp, uid])) == 60
assert len(datagram('/sync/pong', [123, stamp, uid, stamp])) == 76
assert len(datagram('/1/sync/offset', ['-40000000'])) == 32
assert len(datagram('/100/sync/offset', ['-40000000'])) == 36
assert results['model'] == [model(n) for n in (4, 10, 16, 32, 50, 100)]
assert results['targeted_model'] == [model(n, .1, True) for n in (4, 10, 16, 32, 50, 100)]
assert [r['nodes'] for r in results['measured']] == [4, 16, 32, 50]
for record in results['measured']:
    n = record['nodes']
    fires = parse_fires((here / record['raw_log']).read_text())
    assert set(fires) == {'m%s' % i for i in range(20)}
    assert all(set(nodes) == set(range(1, n+1)) for nodes in fires.values())
    assert record['event_spread_ms'] == summary([v/1e6 for v in spread_stats(fires).values()])
    assert record['complete_events'] == record['requested_events'] == 20
    assert record['synced_nodes'] == record['absolute_estimate_error_ms']['count'] == n
    assert record['counts']['pong'] == record['counts']['offset'] == n*record['counts']['ping']
    assert record['rtt_ms']['count'] == record['counts']['pong']
    assert record['routes'] == [['255.255.255.255', 'execution']]
    for kind, count in record['counts'].items():
        assert record['messages_s'][kind] == count/record['measured_s']
        assert record['osc_bytes_s'][kind] == record['osc_bytes'][kind]/record['measured_s']
print('PASS: encoded models; four complete fleets; 80 complete events; counts, rates and raw-log spreads')
