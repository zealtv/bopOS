"""Subscription, ordering and backpressure tests without a network fixture."""
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
import monitor_transport as transport
from osc_bridge import OSCBridge
from io_streams import IOStreams


class Socket:
    def __init__(self, blocked=False):
        self.messages = []
        self.blocked = blocked
        self.active = self.maximum = 0
        self.closed = False

    async def send_text(self, payload):
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        try:
            if self.blocked:
                await asyncio.Event().wait()
            self.messages.append(json.loads(payload))
        finally:
            self.active -= 1

    async def close(self, code):
        self.closed = True


class MonitorTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.devices = {str(n): {'uid': str(n), 'online': True, 'ip': '127.0.0.1',
                                  'sync': {'samples': 3}} for n in range(100)}
        self.seats = {str(n): {'id': n, 'groups': [7]} for n in range(100)}
        self.state = SimpleNamespace(devices=self.devices, data={'supervisor': {'mode': 'off'}},
                                     performance=False, seat_for_uid=self.seats.get)
        self.commands = []
        self.stream = IOStreams(self.state, lambda *args: self.commands.append(args))
        self.enriched = []
        async def public_device(device):
            self.enriched.append(device['uid'])
            return dict(device)
        self.dashboard = SimpleNamespace(state=self.state, clients=set(), wifi_confirmations={},
            public_device=public_device, osc=SimpleNamespace(subscribe_io=self.stream.subscribe,
                unsubscribe_io=self.stream.unsubscribe, _safe_wifi_args=OSCBridge._safe_wifi_args))
        self.broker = transport.MonitorTransport(self.dashboard)

    async def asyncTearDown(self):
        await self.broker.close()
        self.stream.close()

    async def client(self, blocked=False):
        socket = Socket(blocked)
        client = self.broker.attach(socket)
        self.dashboard.clients.add(client)
        # Tests drive ticks explicitly, except the shared-enrichment test.
        self.broker.task.cancel()
        await asyncio.gather(self.broker.task, return_exceptions=True)
        return client, socket

    async def drain(self):
        await asyncio.sleep(.01)

    def subscribe(self, client, **fields):
        return client.replace({'generation': client.selection['generation'] + 1, **fields})

    def batch(self, client):
        client.flush(client.last_summary + 1.1)
        return json.loads(client.telemetry)

    async def test_no_subscribers_skip_all_preview_work_and_tasks(self):
        client, socket = await self.client()
        with patch.object(self.dashboard.osc, '_safe_wifi_args', side_effect=AssertionError('preview')):
            for n in range(1000):
                self.broker.tap('in', '/os/receipt', ['0', n], '127.0.0.1')
        self.assertFalse(client.raw)
        self.assertFalse(client.rates['in'])
        self.assertIsNone(client.telemetry)
        self.assertFalse(socket.messages)

    async def test_default_classes_rates_and_explicit_opt_in(self):
        client, _ = await self.client()
        self.subscribe(client, directions=['in', 'out'])
        for direction, address, args in [('in', '/hb', ['0']), ('in', '/sync/pong', [1, 2, '0']),
                                          ('out', '/pt', [1]), ('in', '/os/receipt', ['0', 'ok'])]:
            self.broker.tap(direction, address, args, '127.0.0.1')
        batch = self.batch(client)['data']
        self.assertEqual([e['data']['address'] for e in batch['entries']], ['/os/receipt'])
        self.assertEqual(batch['status']['in']['filtered'], 2)
        self.assertEqual(batch['status']['in']['dropped_since_subscribe'], 0)
        self.assertGreater(batch['status']['rates']['in']['sync'], 0)
        self.subscribe(client, directions=['in'], classes=['sync', 'heartbeat'])
        self.broker.tap('in', '/hb', ['0'], '127.0.0.1')
        self.assertEqual(len(client.raw), 1)

    async def test_filters_shared_ip_scope_and_independent_clients(self):
        left, _ = await self.client()
        right, _ = await self.client()
        self.subscribe(left, directions=['in', 'out'], uids=['0'], include=['/os/', '/g7/'], exclude=['/os/report'])
        self.subscribe(right, directions=['in'])
        for address, args in [('/os/receipt', ['1']), ('/os/receipt', ['0']),
                              ('/os/report', ['0']), ('/unknown', ['0']), ('/os/receipt', ['?'])]:
            self.broker.tap('in', address, args, '127.0.0.1')
        self.broker.tap('out', '/g7/event', [1], '127.0.0.1', 'physical')
        rows = self.batch(left)['data']['entries']
        self.assertEqual([row['data']['address'] for row in rows], ['/os/receipt', '/g7/event'])
        self.assertEqual(left.stats['in']['unattributed'], 2)
        self.assertEqual(len(right.raw), 5)

    async def test_invalid_replacement_is_atomic_and_generation_releases(self):
        client, _ = await self.client()
        self.subscribe(client, directions=['in'])
        self.broker.tap('in', '/os/receipt', ['0'], '127.0.0.1')
        old = client.selection
        self.assertFalse(self.subscribe(client, include=['bad']))
        self.assertIs(client.selection, old)
        self.assertEqual(len(client.raw), 1)
        self.assertFalse(client.replace({'generation': old['generation'], 'directions': ['out']}))
        self.subscribe(client)
        self.assertFalse(client.raw)
        self.broker.tap('in', '/os/receipt', ['0'], '127.0.0.1')
        self.assertFalse(client.raw)

    async def test_preview_redaction_bytes_and_explicit_truncation(self):
        client, _ = await self.client()
        self.subscribe(client, directions=['out', 'in'])
        self.broker.tap('out', '/all/os/to', ['0', 'wifi-config', 'secret-password'], '127.0.0.1')
        self.broker.tap('in', '/os/receipt', ['0', '界' * 10000, b'x' * 100000], '127.0.0.1')
        rows = [json.loads(encoded) for encoded, size in client.raw]
        self.assertNotIn('secret-password', str(rows))
        self.assertIn('[redacted]', str(rows))
        self.assertTrue(rows[-1]['data']['truncated'])
        self.assertGreater(rows[-1]['data']['omitted_bytes'], 100000)
        self.assertTrue(all(size <= transport.RECORD_BYTES for _, size in client.raw))
        # An oversized explicit identity must not create an unshrinkable
        # metadata field when its argument preview is already bounded.
        uid = 'u' * 60000
        self.devices[uid] = {'uid': uid, 'online': True}
        self.broker.tap('in', '/os/receipt', [uid], '127.0.0.1')
        self.assertLessEqual(client.raw[-1][1], transport.RECORD_BYTES)

    async def test_admission_byte_row_and_envelope_bounds_with_gap_counters(self):
        client, _ = await self.client()
        self.subscribe(client, directions=['in'])
        for n in range(1500):
            self.broker.tap('in', '/os/receipt', ['0', n, 'x' * 500], '127.0.0.1')
        self.assertLessEqual(len(client.raw), 500)
        self.assertLessEqual(client.raw_bytes, transport.RAW_BYTES)
        self.assertGreater(client.stats['in']['dropped'], 0)
        before = client.stats['in']['dropped']
        batch = self.batch(client)
        self.assertLessEqual(len(client.telemetry.encode()), transport.BATCH_BYTES)
        self.assertLessEqual(len(batch['data']['entries']), 100)
        self.assertEqual(batch['data']['status']['in']['dropped_interval'], before)
        queued = len(client.raw)
        client.flush(client.last_summary + 1.1)
        self.assertEqual(len(client.raw), queued)  # One pending envelope only.
        client.tokens = 0
        client.token_at = transport.time.monotonic()
        with patch.object(transport.time, 'monotonic', return_value=client.token_at):
            self.subscribe(client, directions=['in'])
            self.broker.tap('in', '/os/receipt', ['0'], '127.0.0.1')
        self.assertFalse(client.raw)  # Filter changes cannot refill the connection's burst.
        self.assertEqual(client.stats['in']['dropped'], 1)

    async def test_slow_writer_deadline_isolation_and_priority_order(self):
        with patch.object(transport, 'SEND_TIMEOUT', .04):
            slow, slow_socket = await self.client(True)
            healthy, socket = await self.client()
            for client in (slow, healthy):
                self.subscribe(client, directions=['in'],
                               modules={'uid': '0', 'names': ['touch']})
                self.broker.tap('in', '/os/receipt', ['0'], '127.0.0.1')
                self.batch(client)
                await client.send_json({'type': 'command_result', 'data': {'status': 'ok'}})
            await asyncio.sleep(.005)  # Slow socket now owns an in-flight send.
            tasks = set(asyncio.all_tasks())
            for n in range(1000):
                self.broker.tap('in', '/os/receipt', ['0', n, 'x' * 500], '127.0.0.1')
                for client in (slow, healthy):
                    client.sample(b'#bundle\0' + b'\0' * 8, {'touch': [n]})
            self.assertEqual(set(asyncio.all_tasks()), tasks)
            self.assertLessEqual(slow.raw_bytes, transport.RAW_BYTES)
            self.assertLessEqual(slow.sample_bytes, transport.RAW_BYTES)
            self.assertLessEqual(len(slow.samples), 100)
            await asyncio.sleep(.08)
            self.assertTrue(slow_socket.closed)
            self.assertNotIn(slow, self.broker.clients)
            self.assertFalse(healthy.closed)
            self.assertNotIn(slow, self.stream.consumers)
            self.assertIn(healthy, self.stream.consumers)
            self.batch(healthy)
            await self.drain()
            self.assertEqual(socket.maximum, 1)
            self.assertLess([m['type'] for m in socket.messages].index('command_result'),
                            [m['type'] for m in socket.messages].index('telemetry'))

    async def test_core_overflow_closes_and_snapshot_has_own_limit(self):
        client, _ = await self.client()
        await client.send_json({'type': 'state', 'data': 'x' * (transport.CORE_BYTES + 1)})
        self.assertFalse(client.closed)
        await client.send_json({'type': 'state', 'data': 'x' * transport.SNAPSHOT_BYTES})
        self.assertTrue(client.closed)
        other, _ = await self.client()
        for n in range(transport.CORE_ROWS + 1):
            await other.send_json({'type': 'command_result', 'data': n})
        self.assertTrue(other.closed)
        self.assertLessEqual(len(other.core), transport.CORE_ROWS)

    async def test_map_opt_in_coalescing_and_clock_summary(self):
        client, _ = await self.client()
        self.broker.publish('point_frame', {'points': {'0': [1, 2]}})
        self.assertFalse(client.visual)
        self.subscribe(client, map=True, clock=True)
        for n in range(10):
            self.broker.publish('point_frame', {'points': {'0': [n, 2]}})
            self.broker.publish('heartbeat', {'uid': '0', 'timestamp': n})
        self.broker.publish('sync', {'uid': '0'})
        rows = self.batch(client)['data']['entries']
        self.assertEqual([row['type'] for row in rows], ['point_frame', 'heartbeat', 'clock_summary'])
        self.assertEqual(rows[0]['data']['points']['0'][0], 9)
        self.assertEqual(rows[1]['data']['timestamp'], 9)
        self.assertEqual(rows[2]['data']['devices']['0']['samples'], 3)

    async def test_enrich_once_across_clients_and_tombstone_guard(self):
        clients = [(await self.client())[0] for _ in range(3)]
        for n in range(10):
            self.broker.publish('device_update', {'uid': '0'})
        del self.devices['0']
        self.broker.task = asyncio.create_task(self.broker.run())
        await asyncio.sleep(.12)
        self.assertEqual(self.enriched, [])
        for n in range(10):
            self.broker.publish('device_update', {'uid': '1'})
        await asyncio.sleep(.12)
        self.assertEqual(self.enriched, ['1'])
        for client in clients:
            self.assertGreater(client.stats['visual']['coalesced'], 0)

    async def test_prepared_tombstone_preserves_raw_and_lane_fairness(self):
        client, _ = await self.client()
        self.subscribe(client, directions=['in'], modules={'uid': '0', 'names': ['touch']})
        for uid in self.devices:
            client.coalesce('device_update', self.devices[uid])
        for n in range(100):
            self.broker.tap('in', '/os/receipt', ['0', n], '127.0.0.1')
            client.sample(b'#bundle\0' + b'\0' * 8, {'touch': [n]})
        batch = self.batch(client)
        kinds = {row['type'] for row in batch['data']['entries']}
        self.assertEqual(kinds, {'device_update', 'osc_in', 'io_samples'})
        self.broker.publish('device_offline', {'uid': '0'})
        rows = json.loads(client.telemetry)['data']['entries']
        self.assertTrue(any(row['type'] == 'osc_in' for row in rows))
        self.assertFalse(any(row['type'] == 'device_update' and row['data']['uid'] == '0' for row in rows))
        self.state.performance = True
        self.broker.publish('state', None)
        self.assertFalse(client.samples)
        self.assertIsNone(client.module_uid)
        self.assertNotIn(client, self.stream.consumers)
        self.assertFalse(any(row['type'] == 'io_samples' for row in json.loads(client.telemetry)['data']['entries']))

    async def test_module_shared_lease_order_busy_and_visual_release(self):
        client, _ = await self.client()
        editor = object()
        self.stream.subscribe('0', editor, lambda *args: None)
        self.subscribe(client, modules={'uid': '0', 'names': ['touch']})
        self.assertEqual(len(self.stream.consumers), 2)
        bundle = b'#bundle\0' + b'\0' * 7 + b'\1'
        for value in (1, 0):
            client.sample(bundle, {'touch': [value], 'other': [10]})
        rows = self.batch(client)['data']['entries']
        self.assertEqual([row['data']['values'] for row in rows], [{'touch': [1]}, {'touch': [0]}])
        self.assertEqual(rows[0]['data']['timetag'], '0000000000000001')
        other, _ = await self.client()
        self.assertFalse(self.subscribe(other, modules={'uid': '1', 'names': ['touch']}))
        self.assertEqual(self.stream.uid, '0')
        self.subscribe(client)  # Hidden panel's complete replacement releases visual interest.
        self.assertEqual(set(self.stream.consumers), {editor})
        self.state.performance = True
        self.assertFalse(self.subscribe(client, modules={'uid': '0', 'names': ['touch']}))

    async def test_module_flood_drops_whole_bundles_and_keeps_latest(self):
        client, _ = await self.client()
        self.subscribe(client, modules={'uid': '0', 'names': ['touch']})
        for n in range(1000):
            client.sample(b'#bundle\0' + b'\0' * 8, {'touch': [n]})
        self.assertEqual(len(client.samples), 100)
        self.assertEqual(client.stats['modules']['dropped'], 900)
        self.assertLessEqual(client.sample_bytes, transport.RAW_BYTES)
        rows = self.batch(client)['data']['entries']
        self.assertEqual(rows[0]['data']['values']['touch'], [900])
        self.assertEqual(rows[-1]['data']['values']['touch'], [999])
        client.sample(b'#bundle\0' + b'\0' * 8, {'touch': [float('nan')]})
        self.assertEqual(client.stats['modules']['dropped'], 901)
        self.assertFalse(client.samples)  # Never alter an unencodable source value.


if __name__ == '__main__':
    unittest.main()
