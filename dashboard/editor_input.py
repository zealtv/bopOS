"""Session-only IO for the editor, using the bridge's existing local doors."""
import asyncio
import math
import socket

from pyOSC3 import OSCBundle, OSCMessage
from pythonosc.osc_packet import OscPacket, ParseError
from python import io_catalog, io_protocol


class EditorInput(asyncio.DatagramProtocol):
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self.source = None
        self.owner = None
        self.transport = None
        self.timer = None
        self.period = .1
        self.values = {}
        self.outputs = {}
        self.types = {}
        self.held = {}
        self.sender = None

    @property
    def allowed(self):
        return (self.dashboard.supervisor_mode == 'edit'
                and not self.dashboard.state.performance)

    def snapshot(self):
        return {'source': self.source, 'values': self.values, 'outputs': self.outputs}

    def modules(self):
        return {row['name']: io_catalog.descriptions().get(row['type'])
                for row in self.dashboard.state.data['editor'].get('io_modules', [])}

    async def choose(self, source, owner):
        if source is not None and not self.allowed:
            raise ValueError('Performance' if self.dashboard.state.performance
                             else 'The patch editor is not running.')
        if source is not None and not isinstance(source, str):
            raise ValueError('invalid-arguments')
        if source == self.source:
            return
        # Refuse a conflicting device before releasing the old source.
        if source not in (None, 'simulated'):
            device = self.dashboard.state.devices.get(source)
            if not device or device.get('virtual') or not device.get('online'):
                raise ValueError('offline')
            streams = self.dashboard.osc.io_streams
            if streams.uid not in (None, source) and any(key is not self for key in streams.consumers):
                raise ValueError('another device already has stream consumers')
        # Bind before replacing so a busy local bridge leaves the old feed intact.
        transport = None
        if source == 'simulated':
            transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
                lambda: self, local_addr=('127.0.0.1', 8880))
        self.clear()
        self.source, self.owner, self.transport = source, owner, transport
        if source is not None:
            self.sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if source == 'simulated':
            self.reconcile()
            self.pump()
        elif source is not None:
            self.dashboard.osc.subscribe_io(source, self, self.forward)

    def clear(self):
        if self.source not in (None, 'simulated'):
            self.dashboard.osc.unsubscribe_io(self.source, self)
        if self.timer:
            self.timer.cancel()
        if self.transport:
            self.transport.close()
        if self.sender:
            self.sender.close()
            self.sender = None
        self.source = self.owner = self.transport = self.timer = None
        self.values, self.outputs, self.types, self.held = {}, {}, {}, {}
        self.period = .1

    def reconcile(self):
        modules = self.modules()
        types = {row['name']: row['type'] for row in self.dashboard.state.data['editor'].get('io_modules', [])}
        self.values = {name: values for name, values in self.values.items()
                       if self.types.get(name) == types.get(name)}
        self.outputs = {name: values for name, values in self.outputs.items()
                        if self.types.get(name) == types.get(name)}
        self.held = {key: value for key, value in self.held.items()
                     if self.types.get(key[0]) == types.get(key[0]) and key[0] in modules}
        self.types = types
        self.values = {name: self.values.get(name, [
            max(low, min(high, 0)) for low, high in (row['range'] for row in desc['inputs'])])
            for name, desc in modules.items() if desc}
        self.outputs = {name: commands for name, commands in self.outputs.items() if name in modules}

    def forward(self, bundle, _values):
        if self.allowed and self.source not in (None, 'simulated'):
            self.sender.sendto(bundle, ('127.0.0.1', 6662))

    def set_value(self, data, owner):
        if not self.allowed or self.source != 'simulated':
            raise ValueError('Performance' if self.dashboard.state.performance else 'invalid-arguments')
        if data.get('generation') != self.dashboard.state.data['editor']['generation']:
            raise ValueError('invalid-arguments')
        name, index, value = data.get('name'), data.get('index'), data.get('value')
        desc = self.modules().get(name)
        if (not desc or type(index) is not int or not 0 <= index < len(desc['inputs'])
                or type(value) not in (float, int) or not math.isfinite(value)
                or not desc['inputs'][index]['range'][0] <= value <= desc['inputs'][index]['range'][1]):
            raise ValueError('invalid-arguments')
        self.values[name][index] = float(value)
        key = (name, index)
        rest = data.get('rest')
        if (type(rest) in (float, int) and math.isfinite(rest)
                and desc['inputs'][index]['range'][0] <= rest <= desc['inputs'][index]['range'][1]):
            self.held[key] = (owner, float(rest))
        else:
            self.held.pop(key, None)

    def release(self, owner):
        for (name, index), (client, rest) in list(self.held.items()):
            if client is owner:
                if name in self.values and index < len(self.values[name]):
                    self.values[name][index] = rest
                del self.held[name, index]

    def pump(self):
        self.timer = None
        if not self.allowed or self.source != 'simulated':
            return
        bundle = OSCBundle()
        for name, values in self.values.items():
            message = OSCMessage('/' + name)
            for value in values:
                message.append(float(value))
            bundle.append(message)
        try:
            self.sender.sendto(bundle.getBinary(), ('127.0.0.1', 6662))
        except OSError:
            pass
        self.publish()
        self.timer = asyncio.get_running_loop().call_later(self.period, self.pump)

    def publish(self):
        for client in self.dashboard.monitor_transport.clients:
            module = client.selection['modules']
            if module and module['uid'] == 'simulated':
                client.coalesce('editor_io', {
                    'generation': self.dashboard.state.data['editor']['generation'],
                    'values': {name: row for name, row in self.values.items() if name in module['names']},
                    'outputs': {name: row for name, row in self.outputs.items() if name in module['names']}})

    def datagram_received(self, data, address):
        if not self.allowed or self.source != 'simulated' or address[0] != '127.0.0.1':
            return
        try:
            for row in OscPacket(data).messages:
                message = row.message
                args = message.params
                if message.address == '/io/poll':
                    if len(args) == 1 and type(args[0]) in (int, float) and math.isfinite(args[0]) and args[0] > 0:
                        self.period = 1 / max(.1, float(args[0]))
                    continue
                parts = message.address.split('/')
                if len(parts) != 3 or parts[1] != 'io' or not args:
                    continue
                name = parts[2]
                desc = self.modules().get(name)
                if not desc or not isinstance(args[0], str) or args[0] not in {item['command'] for item in desc['outputs']}:
                    continue
                write = io_protocol.validate_write({'name': name, 'command': args[0], 'args': args[1:]})
                outputs = self.outputs.setdefault(name, {})
                outputs[write['command']] = write['args']
                if self.types.get(name) == 'ssd1306':
                    preview = outputs.setdefault('preview', {'lines': [''] * 6, 'invert': False, 'contrast': 255})
                    command, values = write['command'], write['args']
                    if command in ('clear', 'text'):
                        preview['lines'] = [''] * 6
                        if command == 'text':
                            preview['lines'][0] = ' '.join(str(v) for v in values)[:128]
                    elif command == 'line' and values and type(values[0]) in (int, float):
                        index = int(values[0])
                        if 0 <= index < 6:
                            preview['lines'][index] = ' '.join(str(v) for v in values[1:])[:128]
                    elif command == 'invert' and values:
                        preview['invert'] = bool(values[0])
                    elif command == 'contrast' and values and type(values[0]) in (int, float):
                        preview['contrast'] = max(0, min(255, values[0]))
                reply = OSCMessage('/io/written')
                reply.append(name)
                reply.append(write['command'])
                self.sender.sendto(reply.getBinary(), ('127.0.0.1', 6662))
            self.publish()
        except (ParseError, ValueError, TypeError, IndexError, OSError):
            pass

    def close(self):
        self.clear()
