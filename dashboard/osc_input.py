"""Outside-app translation and runtime. No device routing lives here."""
import asyncio
from collections import deque
from dataclasses import dataclass, field
import math
import re
import time

import live_params
from python import manifest as schema
from python.groups import selector_matches
from python.paramgen import _duration
from pythonosc.osc_packet import OscPacket

RESERVED = {'os', 'io', 'sync', 'e', 'p'}


@dataclass
class Translation:
    kind: str
    address: str
    args: list
    clamps: list = field(default_factory=list)
    selector: str = ''
    identity: str = ''


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('expected a finite number')
    return value


def translate(address, args, manifest, groups, now_ns, lead_ms):
    """Return (translation, rejection); declarations are validated manifests."""
    try:
        return _translate(address, list(args), manifest or {}, groups,
                          now_ns, lead_ms), None
    except (ValueError, TypeError, OverflowError) as error:
        return None, str(error)


def _translate(address, args, manifest, groups, now_ns, lead_ms):
    if address in {'/pt', '/point', '/pt/clear'}:
        return Translation('points', address, args)
    if address.startswith('/bop/'):
        command = address[5:]
        if command == 'master' and 1 <= len(args) <= 2:
            value = number(args[0])
            if not 0 <= value <= 1:
                raise ValueError('master must be in 0..1')
            return Translation('master', address, [value, _duration(args[1]) if len(args) == 2 else 0])
        if command == 'mute' and len(args) == 1 and number(args[0]) in (0, 1):
            return Translation('mute', address, [int(args[0])])
        if command == 'lead' and len(args) == 1:
            value = number(args[0])
            if value != int(value) or not 0 <= value <= 10000:
                raise ValueError('lead must be whole milliseconds in 0..10000')
            return Translation('lead', address, [int(value)])
        raise ValueError('unknown command or invalid arguments')
    parts = address.split('/')
    if len(parts) < 3 or parts[0] or any(not part for part in parts[1:]):
        raise ValueError('expected /target/[e|p/]identity')
    target, tail = parts[1], parts[2:]
    if target == 'all':
        selector = target
    elif re.fullmatch(r'[0-9]+', target):
        seat_id = int(target)
        if seat_id > 2 ** 31 - 1:
            raise ValueError('seat number must fit a nonnegative int32')
        selector = str(seat_id)
    elif re.fullmatch(r'g[0-9]+', target) and str(int(target[1:])) in groups:
        selector = 'g' + str(int(target[1:]))
    else:
        selector = next(('g' + str(key) for key, group in groups.items()
                         if group.get('name') == target), None)
        if selector is None:
            raise ValueError('unknown target')
    explicit = tail[0] if tail[0] in {'e', 'p'} else None
    identity = '/'.join(tail[1:] if explicit else tail)
    event = schema.declared_event(manifest, identity)
    param = next((p for p in manifest.get('params', ())
                  if schema.qualify_param(p) == identity), None)
    if explicit is None and (tail[0] in RESERVED or bool(event) == bool(param)):
        raise ValueError('ambiguous or undeclared identity; use explicit /e/ or /p/')
    plane = explicit or ('e' if event else 'p')
    if (plane == 'e' and event is None) or (plane == 'p' and param is None):
        raise ValueError('identity is not declared in that plane')
    wire = f'/{selector}/{plane}/{identity}'
    if plane == 'p':
        return Translation('param', wire, args, selector=selector, identity=identity)
    fields = event.get('fields', [])
    if len(args) > len(fields):
        raise ValueError('too many event fields')
    values, clamps = [], []
    for index, declaration in enumerate(fields):
        if index >= len(args):
            if not declaration.get('optional'):
                raise ValueError('missing required field: ' + declaration['name'])
            value = declaration['default']
        else:
            value = args[index]
        original = value
        if declaration['kind'] != 'text':
            number(value)
            if declaration['kind'] != 'float' and value != int(value):
                raise ValueError('event integer field must be integral')
            if declaration.get('min') is not None:
                value = max(value, declaration['min'])
            if declaration.get('max') is not None:
                value = min(value, declaration['max'])
        values.append(schema.coerce_event_field(declaration, value))
        if value != original:
            clamps.append(f"{declaration['name']}: {original!r} clamped to {value!r}")
    stamp = '0' if lead_ms == 0 else str(now_ns + lead_ms * 1_000_000)
    return Translation('event', wire, [stamp, *values], clamps, selector, identity)


class MasterRamp:
    """Clock/scheduler injected so fades and cancellation need no real time."""
    def __init__(self, emit, clock=time.monotonic, schedule=None):
        self.emit, self.clock = emit, clock
        self.schedule = schedule or (lambda delay, cb: asyncio.get_running_loop().call_later(delay, cb))
        self.pending = None

    def cancel(self):
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None

    def start(self, origin, destination, duration_ms):
        self.cancel()
        started = self.clock()
        def step():
            self.pending = None
            fraction = min(1, (self.clock() - started) * 1000 / duration_ms) if duration_ms else 1
            self.emit(origin + (destination - origin) * fraction)
            if fraction < 1:
                self.pending = self.schedule(.04, step)
        step()


class InputProtocol(asyncio.DatagramProtocol):
    def __init__(self, receiver):
        self.receiver = receiver

    def datagram_received(self, data, addr):
        try:
            packet = OscPacket(data)
        except Exception:
            self.receiver.note(addr[0], '', 'invalid OSC packet', 'rejection')
            return
        # Sender timetags are deliberately ignored: the dashboard owns time.
        for timed in packet.messages:
            try:
                self.receiver.handle(timed.message.address, list(timed.message.params), addr[0])
            except (ValueError, TypeError, OSError, OverflowError) as error:
                self.receiver.note(addr[0], timed.message.address, str(error), 'rejection')


class OSCInput:
    def __init__(self, dashboard, port=5552, clock=time.monotonic, schedule=None):
        self.dashboard, self.port = dashboard, port
        self.transport = None
        self.recent = deque(maxlen=50)
        self.ramp = MasterRamp(self.emit_master)
        self.clock = clock
        self.schedule = schedule or (
            lambda delay, cb: asyncio.get_running_loop().call_later(delay, cb))
        self._next_state_at = 0
        self._state_flush = None

    async def start(self):
        self.transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: InputProtocol(self), local_addr=('0.0.0.0', self.port))
        self.port = self.transport.get_extra_info('sockname')[1]

    def close(self):
        if self._state_flush is not None:
            self._state_flush.cancel()
            self._state_flush = None
        self.ramp.cancel()
        if self.transport:
            self.transport.close()

    def snapshot(self):
        return {'port': self.port, 'recent': list(self.recent)}

    def note(self, ip, address, reason, kind):
        self.recent.append({'time': time.time(), 'sender': ip, 'address': address,
                            'reason': reason, 'kind': kind})
        self.queue_state()

    def queue_state(self):
        """Publish at most every 100 ms, retaining one trailing flush."""
        if self._state_flush is not None:
            return
        delay = self._next_state_at - self.clock()
        if delay > 0:
            self._state_flush = self.schedule(delay, self.flush_state)
        else:
            self.flush_state()

    def flush_state(self):
        self._state_flush = None
        self._next_state_at = self.clock() + .1
        self.dashboard.queue_broadcast('state')

    def emit_master(self, value):
        app = self.dashboard
        app.state.data['master'] = value
        app.osc.send_master()
        app.queue_broadcast('master', {'value': value})

    def set_master(self, value, duration=0):
        app = self.dashboard
        origin = app.state.data.get('master', 1.0)
        # Fades flush the destination before transient steps replace the live
        # value. Immediate writes retain the UI's existing save debounce.
        previous = app.state.data.get('master_destination')
        app.state.data['master_destination'] = value
        try:
            if duration:
                app.state.save()
            else:
                app.state.save_debounced()
        except (OSError, ValueError, TypeError):
            if previous is None:
                app.state.data.pop('master_destination', None)
            else:
                app.state.data['master_destination'] = previous
            raise
        self.ramp.start(origin, value, duration)

    def handle(self, address, args, ip):
        app = self.dashboard
        patch = app.state.data.get('editor', {}).get('patch') if app.supervisor_mode == 'edit' else None
        manifest = (app.live_control_manifest(patch) if patch or app.supervisor_mode != 'edit' else None)
        result, error = translate(address, args, manifest, app.state.data.get('groups', {}),
                                  time.monotonic_ns(), app.state.data.get('event_lead_ms', 500))
        if error:
            self.note(ip, address, error, 'rejection')
            return
        for reason in result.clamps:
            self.note(ip, address, reason, 'clamp')
        if result.kind == 'master':
            self.set_master(*result.args)
        elif result.kind == 'lead':
            app.state.data['event_lead_ms'] = result.args[0]
            app.state.save_debounced()
            self.queue_state()
        elif result.kind == 'mute':
            app.state.data['muted'] = bool(result.args[0])
            app.osc.send_mute_all()
            app.queue_broadcast('mute_all', {'value': result.args[0]})
            self.queue_state()
        else:
            if result.kind == 'points':
                app.osc.outside_points_until = time.monotonic() + 2
            elif result.kind == 'param':
                if app.supervisor_mode == 'edit':
                    editor = app.editor_target()
                    seats = ([editor] if selector_matches(
                        result.selector, 0, editor.get('groups', ())) else [])
                else:
                    seats = app.osc._selector_seats(result.selector)
                if len(result.args) == 1:
                    declaration = next(p for p in manifest.get('params', ())
                                       if schema.qualify_param(p) == result.identity)
                    value = live_params.canonicalize_value(declaration, result.args[0])
                    if value is not None:
                        app.osc._store_fade_destination(seats, result.identity, value)
                app.osc.record_param_for(seats, result.identity, result.args)
                app.state.save_debounced()
                self.queue_state()
            app.osc.send(result.address, result.args)
