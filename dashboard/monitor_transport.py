"""Dashboard-local subscriptions and bounded, single-writer WebSockets.

OSC/audio timing is independent of this lossy visual transport. One shared
100 ms clock prepares device projections; each connection owns its raw/sample
queues, counters and writer. No task is created for a tap or a visual update.
"""
import asyncio
from collections import Counter, OrderedDict, deque
import json
import math
import re
import time

TICK = .1
BATCH_BYTES = 32 * 1024
BATCH_ROWS = 100
RAW_ROWS = 500
RAW_BYTES = 128 * 1024
RECORD_BYTES = 4096
CORE_ROWS = 256
CORE_BYTES = 512 * 1024
SNAPSHOT_BYTES = 4 * 1024 * 1024
TOTAL_CORE_BYTES = 8 * 1024 * 1024
SEND_TIMEOUT = 2
SNAPSHOTS = {'state', 'distribution', 'show', 'show_warnings', 'show_playback'}
CLASSES = {'sync', 'heartbeat', 'points'}


def encode(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def traffic_class(address):
    if address.startswith('/sync/') or re.fullmatch(r'/\d+/sync/offset', address):
        return 'sync'
    if address == '/hb':
        return 'heartbeat'
    if address == '/pt' or address.startswith('/pt/'):
        return 'points'
    return 'ordinary'


def selection(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid capture selection.')
    generation = data.get('generation')
    if type(generation) is not int or not 0 <= generation <= 2**53-1:
        raise ValueError('Invalid capture generation.')
    result = {'generation': generation}
    for name, limit, length in (('directions', 2, 3), ('uids', 16, 128),
                                 ('include', 16, 128), ('exclude', 16, 128),
                                 ('classes', 3, 16)):
        values = data.get(name, [])
        if (not isinstance(values, list) or len(values) > limit
                or any(not isinstance(v, str) or not v or len(v) > length for v in values)):
            raise ValueError('Invalid capture %s.' % name)
        result[name] = set(values) if name in {'directions', 'uids', 'classes'} else values
    if result['directions'] - {'in', 'out'} or result['classes'] - CLASSES:
        raise ValueError('Invalid capture direction or traffic class.')
    if any(not p.startswith('/') for p in result['include'] + result['exclude']):
        raise ValueError('Address prefixes must start with /.')
    for name in ('map', 'clock'):
        if type(data.get(name, False)) is not bool:
            raise ValueError('Invalid %s selection.' % name)
        result[name] = data.get(name, False)
    modules = data.get('modules')
    if modules is not None:
        if (not isinstance(modules, dict) or not isinstance(modules.get('uid'), str)
                or not modules['uid'] or len(modules['uid']) > 128
                or not isinstance(modules.get('names'), list) or not modules['names']
                or len(modules['names']) > 64
                or any(not isinstance(n, str) or not n or len(n) > 128 for n in modules['names'])):
            raise ValueError('Invalid module selection.')
        modules = {'uid': modules['uid'], 'names': set(modules['names'])}
    result['modules'] = modules
    return result


class Client:
    def __init__(self, broker, socket):
        self.broker, self.socket = broker, socket
        self.core, self.core_bytes, self.core_regular_bytes = deque(), 0, 0
        self.telemetry = None
        self.wake = asyncio.Event()
        self.closed = False
        self.selection = selection({'generation': 0})
        self.raw, self.raw_bytes = deque(), 0
        self.samples, self.sample_bytes = deque(), 0
        self.visual = OrderedDict()
        self.stats = {'in': Counter(), 'out': Counter(), 'modules': Counter(), 'visual': Counter()}
        self.rates = {'in': Counter(), 'out': Counter()}
        self.tokens, self.token_at = 500., time.monotonic()
        self.last_summary = time.monotonic()
        self.dirty = False
        self.module_uid = None
        self.writer = asyncio.create_task(self.write())

    async def send_json(self, message):
        self.send_core(message)

    @property
    def url(self):
        return self.socket.url

    @property
    def headers(self):
        return self.socket.headers

    def send_core(self, message):
        if self.closed:
            return
        payload = encode(message)
        size = len(payload.encode())
        snapshot = message['type'] in SNAPSHOTS
        if (len(self.core) >= CORE_ROWS or self.core_bytes + size > TOTAL_CORE_BYTES
                or (snapshot and size > SNAPSHOT_BYTES)
                or (not snapshot and self.core_regular_bytes + size > CORE_BYTES)):
            self.closed = True
        else:
            self.core.append((payload, size, snapshot))
            self.core_bytes += size
            if not snapshot:
                self.core_regular_bytes += size
        self.wake.set()

    async def write(self):
        try:
            while not self.closed:
                await self.wake.wait()
                self.wake.clear()
                while not self.closed and (self.core or self.telemetry is not None):
                    if self.core:
                        payload, size, snapshot = self.core.popleft()
                        self.core_bytes -= size
                        if not snapshot:
                            self.core_regular_bytes -= size
                    else:
                        payload, self.telemetry = self.telemetry, None
                    await asyncio.wait_for(self.socket.send_text(payload), SEND_TIMEOUT)
        except (Exception, asyncio.CancelledError):
            pass
        finally:
            self.closed = True
            self.broker.release(self)
            self.core.clear()
            self.raw.clear()
            self.samples.clear()
            self.visual.clear()
            self.telemetry = None
            try:
                await asyncio.wait_for(self.socket.close(code=1013), SEND_TIMEOUT)
            except Exception:
                pass

    async def dispose(self):
        self.closed = True
        self.writer.cancel()
        await asyncio.gather(self.writer, return_exceptions=True)

    def replace(self, data):
        try:
            new = selection(data)
            if new['generation'] <= self.selection['generation']:
                raise ValueError('Capture generation must increase.')
            module = new['modules']
            if module:
                # Subscribe before replacing: a busy/performance refusal leaves
                # the old selection and its source ownership intact.
                self.broker.dashboard.osc.subscribe_io(module['uid'], self, self.sample)
        except ValueError as error:
            self.send_core({'type': 'capture_status', 'data': {'error': str(error),
                           'generation': self.selection['generation'],
                           'requested_generation': data.get('generation') if isinstance(data, dict) else None}})
            return False
        if self.module_uid and (not module or module['uid'] != self.module_uid):
            self.broker.dashboard.osc.unsubscribe_io(self.module_uid, self)
        self.module_uid = module['uid'] if module else None
        self.selection = new
        self.raw.clear()
        self.raw_bytes = 0
        self.samples.clear()
        self.sample_bytes = 0
        self.telemetry = None
        self.visual.pop(('point_frame', None), None)
        self.visual.pop(('clock_summary', None), None)
        self.stats = {channel: Counter() for channel in self.stats}
        self.rates = {'in': Counter(), 'out': Counter()}
        self.dirty = True
        self.send_core({'type': 'capture_status', 'data': {'generation': new['generation']}})
        return True

    def coalesce(self, kind, data):
        if kind == 'point_frame' and not self.selection['map']:
            return
        key = (kind, data.get('uid'))
        if key in self.visual:
            self.stats['visual']['coalesced'] += 1
        self.visual[key] = {'type': kind, 'data': data}

    def invalidate(self, kind, uid):
        for key in list(self.visual):
            if kind == 'state' or key[1] == uid:
                del self.visual[key]
        if self.telemetry is not None:
            envelope = json.loads(self.telemetry)
            envelope['data']['entries'] = [row for row in envelope['data']['entries']
                if row['type'] not in {'device_update', 'heartbeat', 'clock_summary', 'point_frame'}
                or (kind != 'state' and row['data'].get('uid') != uid)]
            self.telemetry = encode(envelope)

    def sample(self, bundle, values):
        module = self.selection['modules']
        if not module or self.broker.dashboard.state.performance:
            return
        values = {name: channels for name, channels in values.items() if name in module['names']}
        if not values:
            return
        # Preserve each original bundle's ordering, values and OSC timetag;
        # the visual adapter never enters or throttles an editor callback.
        row = {'type': 'io_samples', 'data': {'uid': module['uid'], 'values': values,
               'received_at': time.time(), 'timetag': bundle[8:16].hex()}}
        try:
            encoded = encode(row)
        except (TypeError, ValueError):
            self.stats['modules']['dropped'] += 1
            self.dirty = True
            return
        size = len(encoded.encode())
        if size > BATCH_BYTES - 4096:
            self.stats['modules']['dropped'] += 1
            self.dirty = True
            return
        self.samples.append((encoded, size))
        self.sample_bytes += size
        while len(self.samples) > 100 or self.sample_bytes > RAW_BYTES:
            _, removed = self.samples.popleft()
            self.sample_bytes -= removed
            self.stats['modules']['dropped'] += 1
        self.dirty = True

    def flush(self, now):
        if self.closed or self.telemetry is not None:
            return
        summary = now - self.last_summary >= 1
        if not (self.raw or self.samples or self.visual or self.dirty
                or (summary and (self.selection['directions'] or self.selection['clock']))):
            return
        if summary and self.selection['clock']:
            facts = {uid: dict(device.get('sync') or {})
                     for uid, device in self.broker.dashboard.state.devices.items()}
            self.coalesce('clock_summary', {'devices': facts})
        status = {key: {name: count for name, count in counts.items()
                        if name not in {'reported', 'dropped'}} for key, counts in self.stats.items()}
        for key, counts in self.stats.items():
            status[key]['dropped_since_subscribe'] = counts['dropped']
            status[key]['dropped_interval'] = counts['dropped'] - counts['reported']
        if summary:
            elapsed = max(now - self.last_summary, .001)
            status['rates'] = {direction: {name: count / elapsed for name, count in rates.items()}
                               for direction, rates in self.rates.items()}
        envelope = {'generation': self.selection['generation'], 'status': status, 'entries': []}
        # Include the entire envelope/status in the byte budget.
        prefix = encode({'type': 'telemetry', 'data': envelope})
        budget = BATCH_BYTES - len(prefix.encode())
        rows = []
        # Share the budget fairly between UID projections, raw records and
        # complete poll bundles. OrderedDict keeps unsent UIDs ahead of newly
        # changed ones; replacing a UID never moves it to the back.
        while len(rows) < BATCH_ROWS and not self.closed:
            progress = False
            if self.visual:
                key = next(iter(self.visual))
                row = self.visual[key]
                encoded = encode(row)
                size = len(encoded.encode()) + 1
                if size > BATCH_BYTES - 4096:
                    self.send_core(row)  # Never truncate a state projection.
                    del self.visual[key]
                    progress = True
                elif size <= budget:
                    rows.append(encoded)
                    budget -= size
                    del self.visual[key]
                    progress = True
            for queue, channel in ((self.raw, 'raw'), (self.samples, 'sample')):
                if queue and len(rows) < BATCH_ROWS:
                    encoded, size = queue[0]
                    if size + 1 <= budget:
                        queue.popleft()
                        setattr(self, channel + '_bytes', getattr(self, channel + '_bytes') - size)
                        rows.append(encoded)
                        budget -= size + 1
                        progress = True
            if not progress:
                break
        # Splice pre-encoded bounded records without repeatedly serializing
        # argument previews. The empty entries list is the final field.
        payload = prefix[:-4] + '[' + ','.join(rows) + ']}}'
        assert len(payload.encode()) <= BATCH_BYTES
        self.telemetry = payload
        self.wake.set()
        for counts in self.stats.values():
            counts['reported'] = counts['dropped']
        if summary:
            self.last_summary = now
            self.rates = {'in': Counter(), 'out': Counter()}
        self.dirty = False


class MonitorTransport:
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self.clients = set()
        self.updates = OrderedDict()
        self.task = None

    def attach(self, socket):
        client = Client(self, socket)
        self.clients.add(client)
        if self.task is None:
            self.task = asyncio.create_task(self.run())
        return client

    def release(self, client):
        self.clients.discard(client)
        self.dashboard.clients.discard(client)
        self.dashboard.wifi_confirmations.pop(client, None)
        if client.module_uid:
            self.dashboard.osc.unsubscribe_io(client.module_uid, client)
            client.module_uid = None

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
        await asyncio.gather(*(client.dispose() for client in tuple(self.clients)))

    def publish(self, kind, data):
        if kind == 'sync':
            return True  # Backend facts are consumed by the one-second summary.
        if kind == 'device_update':
            uid = data.get('uid')
            device = self.dashboard.state.devices.get(uid)
            if device is not None and self.clients:
                if uid in self.updates:
                    for client in self.clients:
                        client.stats['visual']['coalesced'] += 1
                self.updates[uid] = device
            return True
        if kind in {'heartbeat', 'point_frame'}:
            for client in self.clients:
                client.coalesce(kind, data)
            return True
        # A priority state/removal must invalidate every older pending
        # projection, including an already-prepared telemetry envelope.
        if kind in {'state', 'device_offline'}:
            uid = data.get('uid') if isinstance(data, dict) else None
            if kind == 'state':
                self.updates.clear()
            else:
                self.updates.pop(uid, None)
            for client in self.clients:
                client.invalidate(kind, uid)
                if kind == 'state' and self.dashboard.state.performance:
                    if client.module_uid:
                        self.dashboard.osc.unsubscribe_io(client.module_uid, client)
                        client.module_uid = None
                    client.samples.clear()
                    client.sample_bytes = 0
                    if client.telemetry is not None:
                        envelope = json.loads(client.telemetry)
                        envelope['data']['entries'] = [row for row in envelope['data']['entries']
                                                       if row['type'] != 'io_samples']
                        client.telemetry = encode(envelope)
        return False

    def recipients(self, direction, address, args, route=None, uid=None):
        devices = self.dashboard.state.devices
        if uid in devices:
            return {uid}
        # Only explicit payload identities and selectors establish attribution;
        # never infer one from a shared IP.
        if direction == 'in':
            if address == '/sync/pong' and len(args) > 2:
                return {str(args[2])} & devices.keys()
            if address == '/hb' and args:
                return {str(args[0])} & devices.keys()
            if address.startswith('/os/') and args:
                if str(args[0]) in devices:
                    return {str(args[0])}
                if address == '/os/probe':
                    return {uid for uid in devices if self.dashboard.state.seat_for_uid(uid)
                            and str(self.dashboard.state.seat_for_uid(uid)['id']) == str(args[0])}
            return set()
        parts = address.split('/')
        selector = parts[1] if len(parts) > 1 else ''
        scoped = {uid for uid, device in devices.items()
                  if bool(device.get('virtual')) ==
                  (route == 'execution' and self.dashboard.state.data.get('supervisor', {}).get('mode') != 'off')}
        if address == '/sync/ping':
            return {uid for uid in scoped if self.dashboard.state.seat_for_uid(uid)}
        if selector == 'all':
            if address == '/all/os/to' and args:
                return {str(args[0])} & devices.keys()
            if address in {'/all/os/assign', '/all/os/groups', '/all/os/performance'} and args:
                if str(args[0]) in devices:
                    return {str(args[0])}
            return scoped
        if selector.isdigit():
            return {uid for uid in scoped if self.dashboard.state.seat_for_uid(uid)
                    and str(self.dashboard.state.seat_for_uid(uid)['id']) == selector}
        if re.fullmatch(r'g(?:0|[1-9]\d*)', selector):
            group = int(selector[1:])
            return {uid for uid in scoped if group in
                    (self.dashboard.state.seat_for_uid(uid) or {}).get('groups', [])}
        return set()

    def tap(self, direction, address, args, peer, route=None, uid=None):
        clients = [c for c in self.clients if direction in c.selection['directions'] and not c.closed]
        if not clients:
            return
        kind = traffic_class(address)
        recipients = self.recipients(direction, address, args, route, uid)
        matching = []
        now = time.monotonic()
        for client in clients:
            chosen, counts = client.selection, client.stats[direction]
            client.rates[direction][kind] += 1
            if not recipients:
                counts['unattributed'] += 1
            if ((kind != 'ordinary' and kind not in chosen['classes'])
                    or (chosen['uids'] and not chosen['uids'].intersection(recipients))
                    or (chosen['include'] and not any(address.startswith(p) for p in chosen['include']))
                    or any(address.startswith(p) for p in chosen['exclude'])):
                counts['filtered'] += 1
                continue
            client.tokens = min(500., client.tokens + (now - client.token_at) * 500)
            client.token_at = now
            if client.tokens < 1:
                counts['dropped'] += 1
                client.dirty = True
                continue
            client.tokens -= 1
            matching.append(client)
        if not matching:
            return
        args = self.dashboard.osc._safe_wifi_args(address, args)
        preview, omitted, omitted_values = [], 0, 0
        for arg in args[:64]:
            if isinstance(arg, (bytes, bytearray)):
                preview.append('[blob: %s bytes omitted]' % len(arg))
                omitted += len(arg)
            elif isinstance(arg, str):
                preview.append(arg[:512])
                if len(arg) > 512:
                    omitted += len(arg[512:].encode())
            elif isinstance(arg, (int, float, bool)):
                preview.append(str(arg) if isinstance(arg, float) and not math.isfinite(arg) else arg)
            else:
                preview.append('[value omitted]')
                omitted_values += 1
        if len(args) > 64:
            omitted_values += len(args) - 64
        if len(address) > 512:
            omitted += len(address[512:].encode())
        data = {'ts': time.time(), 'address': address[:512], 'args': preview,
                'target' if direction == 'out' else 'source': str(peer)[:128],
                'recipient_count': len(recipients)}
        if route:
            data['route'] = str(route)[:32]
        row = {'type': 'osc_' + direction, 'data': data}
        while True:
            if omitted or omitted_values:
                data['truncated'] = True
                data['omitted_bytes'] = omitted
                data['omitted_values'] = omitted_values
            encoded = encode(row)
            size = len(encoded.encode())
            if size <= RECORD_BYTES:
                break
            if preview:
                omitted += len(str(preview.pop()).encode())
            else:
                data['address'] = address[:128]
                omitted += 1
        for client in matching:
            if omitted or omitted_values:
                client.stats[direction]['truncated'] += 1
            client.raw.append((encoded, size))
            client.raw_bytes += size
            while len(client.raw) > RAW_ROWS or client.raw_bytes > RAW_BYTES:
                old, removed = client.raw.popleft()
                client.raw_bytes -= removed
                channel = json.loads(old)['type'][4:]
                client.stats[channel]['dropped'] += 1
            client.dirty = True

    async def run(self):
        while True:
            await asyncio.sleep(TICK)
            updates, self.updates = self.updates, OrderedDict()
            for uid, device in updates.items():
                if self.dashboard.state.devices.get(uid) is not device:
                    continue
                public = await self.dashboard.public_device(device)
                if self.dashboard.state.devices.get(uid) is not device or not device.get('online'):
                    continue
                for client in self.clients:
                    client.coalesce('device_update', public)
            now = time.monotonic()
            for client in tuple(self.clients):
                client.flush(now)
