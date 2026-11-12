"""Socket-free fixtures exercising all three production datagram adapters."""
import contextlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('python', 'tools')]
FILES = ('python/bopos.py', 'tools/simfleet.py', 'tools/audition.py')

class Capture:
    def __init__(self):
        self.calls = []
    def sendto(self, packet, target):
        from pyOSC3 import decodeOSC
        decoded = decodeOSC(packet)
        params = []
        for value in decoded[2:]:
            if isinstance(value, str) and value.startswith(('{', '[')):
                try:
                    value = json.loads(value)
                except ValueError:
                    pass
            params.append(value)
        self.calls.append(dict(address=decoded[0], tags=decoded[1], params=params,
                               target=list(target)))


class NoTimer:
    def __init__(self, *args, **kwargs):
        pass
    def start(self):
        pass
    def cancel(self):
        pass


class InlineThread:
    def __init__(self, target, args=(), **kwargs):
        self.target, self.args = target, args
    def start(self):
        self.target(*self.args)


def load_node():
    import pyOSC3
    import store
    import nodelog
    spec = importlib.util.spec_from_file_location('protocol_probe_bopos', ROOT / FILES[0])
    node = importlib.util.module_from_spec(spec)
    # Prevent import-time localhost bind, client creation, persisted migration,
    # hardware module import and atexit/global logging changes.
    with patch.object(pyOSC3, 'OSCServer', Mock()), patch.object(pyOSC3, 'OSCClient', Mock()), \
         patch.object(store.Store, 'put', return_value=True), \
         patch.object(nodelog, 'configure'), patch('atexit.register'), \
         patch.dict(sys.modules, {'sys_i2c': None, 'sys_wireless': None}), \
         patch.object(sys, 'argv', ['bopos.py', 'probe-node']):
        spec.loader.exec_module(node)
    return node


def probe(node, label, address, params, performance=False, types=None, datagram=None):
    import simfleet
    import audition
    import io_control
    import io_stream
    import io_protocol
    from store import Store
    uid, source = 'probe-node', ('127.0.0.1', 4000)
    from pythonosc.osc_message_builder import OscMessageBuilder
    builder = OscMessageBuilder(address=address)
    for index, value in enumerate(params):
        builder.add_arg(value, arg_type=types[index] if types else None)
    packet = builder.build().dgram if datagram is None else datagram
    captures = {name: Capture() for name in ('node', 'simfleet', 'audition')}
    controls = []
    state = SimpleNamespace(uid=uid, id=0, version='probe', release='1.0.0', update_model='ephemeral',
        config={}, groups=(), performance=performance, device_enabled=True, mute_all=False,
        store=Store('unused', persistent=False), reports={}, reports_lock=threading.Lock(),
        performance_path='unused', audio_status='active', audio_error=None)
    control = io_control.IOControl(uid, Mock(), Mock(), timer_factory=NoTimer,
                                   write_allowed=lambda: not state.performance)
    def bridge_reply(address, values):
        if address == '/io/scan':
            result = io_protocol.empty_io()
            result['scanned'] = True
            control.handle('/io/scanned', [json.dumps(result)])
    control.send_bridge = bridge_reply
    state.io_control = control
    state.io_stream = io_stream.NodeStream(uid, Mock(), Mock(), lambda: not state.performance,
                                          timer=NoTimer)
    controls.extend([control, state.io_stream])
    device = simfleet.Device(uid, uid, 0, 'probe', wired=True, ephemeral=True,
                            release='1.0.0')
    device.state = 'running'
    device.performance = performance
    fleet = object.__new__(simfleet.SimFleet)
    fleet.args = SimpleNamespace(report_port=5550, state_dir=None, target='127.0.0.1', drop=0)
    fleet.devices, fleet.sock = [device], captures['simfleet']
    fleet.protocol = simfleet.ContractProtocol()
    fleet.start_monotonic = time.monotonic()
    fleet.manifest_text = None
    fleet.log = Mock()
    fleet.schedule = Mock()
    fleet.device_now_ns = Mock(return_value=123456)
    rig = object.__new__(audition.AuditionRig)
    virtual = audition.VirtualNode(0, 0, uid, 16661, name=uid)
    rig.nodes, rig.sock = [virtual], captures['audition']
    rig.args = SimpleNamespace(report_port=5550, target='127.0.0.1', no_engine=True)
    rig.started = time.monotonic()
    rig.local_target = '127.0.0.1'
    rig.param_declarations = {}
    rig._load_patch = lambda: ('/fixture/demo-pd', {'engine': 'pd', 'params': []})
    rig.send_engine = Mock()
    rig.send_groups = Mock()
    rig.send_id = Mock()
    rig.send_matrix = Mock()
    rig.send_point_values = Mock()
    rig.send_heartbeat = Mock()
    fleet.heartbeat = Mock()
    # Successful mixer/persistence and deterministic no-hardware observations.
    # Report facts that genuinely differ by host are retained in raw output.
    audio = dict(configured=dict(device.audio_config), active=dict(device.audio_active),
                 cards=[dict(id='Simulated', index=0, label='Simulated stereo output',
                             mixer_controls=['Master'])], status='active', error=None)
    errors = {}

    def unavailable_wifi(_payload, receipt=None):
        result = ('err', 'unavailable', {'managed': False})
        if receipt is not None:
            receipt(*result)
        return result

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(node, 'monotonic_ns', return_value=123456))
        stack.enter_context(patch.object(node, 'enforce_mute', return_value=True))
        stack.enter_context(patch.object(node, 'audio_report', return_value=audio))
        stack.enter_context(patch.object(node, 'active_patch_path', return_value=None))
        stack.enter_context(patch.object(node.socket, 'gethostname', return_value=uid))
        stack.enter_context(patch.object(node.wifi_config, 'helper_status', return_value={'managed': False}))
        stack.enter_context(patch.object(node.wifi_config, 'apply', side_effect=unavailable_wifi))
        stack.enter_context(patch.object(node.log_config, 'usb_present', return_value=False))
        stack.enter_context(patch.object(node.performance_mode, 'save', return_value=True))
        stack.enter_context(patch.object(node.nodelog, 'change_destination', side_effect=lambda callback: callback()))
        stack.enter_context(patch.object(node.threading, 'Thread', InlineThread))
        stack.enter_context(patch.object(device, 'save_assignment', return_value=True))
        stack.enter_context(patch.object(node.manifest, 'raw', return_value=None))
        calls = {
            'node': lambda: node.handle_lan_datagram(packet, source, captures['node'], state),
            'simfleet': lambda: fleet.receive_contract(packet, source),
            'audition': lambda: rig.relay(packet, source),
        }
        for name, call in calls.items():
            try:
                call()
            except Exception as error:
                errors[name] = type(error).__name__ + ': ' + str(error)
    for item in controls:
        item.close()
    replies = {name: cap.calls for name, cap in captures.items()}
    equal = replies['node'] == replies['simfleet'] == replies['audition']
    return dict(case=label, address=address, input=params, input_tags=types, initial_performance=performance,
                replies_equal=equal and not errors, errors=errors, replies=replies,
                mode_after=dict(node=state.performance, simfleet=device.performance,
                                audition=getattr(virtual, 'performance', None)),
                assignment_after=dict(node=dict(id=state.id, elements=getattr(state, 'elements', [])),
                    simfleet=dict(id=device.device_id, elements=device.elements),
                    audition=dict(id=virtual.device_id, elements=[list(position)
                                  for position in virtual.positions])))


