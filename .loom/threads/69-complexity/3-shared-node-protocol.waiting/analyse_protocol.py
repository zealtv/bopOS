#!/usr/bin/env python3
"""Read-only census and direct-datagram parity probe; no sockets or hardware.

Run with the project venv. Output is evidence, not a production test suite.
Only hardware observations and side effects are substituted; the three real
datagram handlers, validation functions and receipt builders execute unchanged.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / p) for p in ('python', 'tools')]
FILES = ('python/bopos.py', 'tools/simfleet.py', 'tools/audition.py')
SURFACE = {
    FILES[0]: ['dispatch_uid_admin', 'report_reply', 'handle_lan_datagram',
               'dispatch_admin_verb', 'rev_reply', 'installed_patches', 'installed_assets'],
    FILES[1]: ['uid_admin', 'send_report', 'receive_contract', 'admin_verb',
               'send_rev', 'send_patch_list', 'send_asset_list'],
    FILES[2]: ['uid_admin', 'send_report', 'relay', 'send_rev', 'patch_listing'],
}


def census():
    result = {}
    for relative in FILES:
        text = (ROOT / relative).read_text()
        tree = ast.parse(text)
        functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        selected = {}
        for name in SURFACE[relative]:
            n = functions[name]
            selected[name] = {'line': n.lineno, 'lines': n.end_lineno - n.lineno + 1}
        report = functions['report_reply' if relative == FILES[0] else 'send_report']
        fields = next([k.value for k in n.value.keys if isinstance(k, ast.Constant)]
                      for n in ast.walk(report) if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'report' for t in n.targets)
                      and isinstance(n.value, ast.Dict))
        uid = functions['dispatch_uid_admin' if relative == FILES[0] else 'uid_admin']
        verbs = set()
        for n in ast.walk(uid):
            if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == 'member':
                for rhs in n.comparators:
                    if isinstance(rhs, ast.Constant) and isinstance(rhs.value, str):
                        verbs.add(rhs.value)
            if isinstance(n, (ast.Set, ast.Call)):
                # UID_ADMIN_VERBS lives outside the real node's dispatch body.
                if isinstance(n, ast.Set):
                    verbs.update(c.value for c in n.elts if isinstance(c, ast.Constant)
                                 and isinstance(c.value, str))
        if relative == FILES[0]:
            for n in tree.body:
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'UID_ADMIN_VERBS' for t in n.targets):
                    verbs.update(c.value for c in ast.walk(n.value)
                                 if isinstance(c, ast.Constant) and isinstance(c.value, str))
        imports = sorted({n.names[0].name for n in tree.body if isinstance(n, ast.Import)
                          and n.names[0].name in ('identity', 'manifest', 'pointfield', 'relay',
                          'groups', 'paramgen', 'audio_config', 'log_config', 'wifi_config',
                          'osc_contract', 'io_protocol', 'io_control', 'io_stream', 'performance_mode',
                          'asset_slots', 'runcontext')})
        result[relative] = dict(sha256=hashlib.sha256(text.encode()).hexdigest(),
            file_lines=len(text.splitlines()), selected=selected,
            selected_lines=sum(v['lines'] for v in selected.values()),
            report_fields=fields, uid_verbs=sorted(verbs), shared_imports=imports)
    return result


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


def probe(node, label, address, params, performance=False, types=None):
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
    packet = builder.build().dgram
    captures = {name: Capture() for name in ('node', 'simfleet', 'audition')}
    controls = []
    state = SimpleNamespace(uid=uid, id=0, version='probe', update_model='ephemeral',
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
    device = simfleet.Device(uid, uid, 0, 'probe', wired=True, ephemeral=True)
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
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(node, 'enforce_mute', return_value=True))
        stack.enter_context(patch.object(node, 'audio_report', return_value=audio))
        stack.enter_context(patch.object(node, 'active_patch_path', return_value=None))
        stack.enter_context(patch.object(node.socket, 'gethostname', return_value=uid))
        stack.enter_context(patch.object(node.wifi_config, 'helper_status', return_value={'managed': False}))
        stack.enter_context(patch.object(node.wifi_config, 'apply', return_value=('err', 'unavailable', {'managed': False})))
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
    return dict(case=label, address=address, input=params, input_tags=__import__('pyOSC3').decodeOSC(packet)[1], initial_performance=performance,
                replies_equal=equal and not errors, errors=errors, replies=replies,
                mode_after=dict(node=state.performance, simfleet=device.performance,
                                audition=getattr(virtual, 'performance', None)),
                assignment_after=dict(node=dict(id=state.id, elements=getattr(state, 'elements', [])),
                    simfleet=dict(id=device.device_id, elements=device.elements),
                    audition=dict(id=virtual.device_id, elements=[list(position)
                                  for position in virtual.positions])))


def manifest_probe():
    import manifest
    import simfleet
    import audition
    with tempfile.TemporaryDirectory(prefix='manifest-probe-', dir=Path(__file__).parent) as directory:
        root = Path(directory)
        (root / 'main.scd').write_text('// inert entrypoint fixture\n')
        candidate = dict(engine='sc', entrypoint='main.scd',
                         params=[dict(name='gain', kind='not-a-kind')])
        path = root / manifest.MANIFEST_NAME
        path.write_text(json.dumps(candidate))
        validated, error = manifest.load(directory)
        text, declarations = simfleet.load_manifest(str(path))
        rig = object.__new__(audition.AuditionRig)
        rig.args = SimpleNamespace(manifest=str(path))
        try:
            rig._load_patch()
            audition_error = None
        except ValueError as problem:
            audition_error = str(problem)
        return dict(candidate=candidate, node_error=error, node_accepted=validated is not None,
                    simfleet_accepted=text is not None, simfleet_declarations=sorted(declarations),
                    audition_error=audition_error)


def codec_probe():
    from pyOSC3 import OSCMessage, decodeOSC
    from pythonosc.osc_message_builder import OscMessageBuilder
    from pythonosc.osc_message import OscMessage
    cases = [('i', 2147483647), ('f', .25), ('s', '1234567890123456789'),
             ('s', 'caf\u00e9'), ('b', b'\x00\xff\x01\x02')]
    results = []
    for tag, value in cases:
        legacy = OSCMessage('/probe')
        legacy.append(value, tag)
        modern = OscMessageBuilder(address='/probe')
        modern.add_arg(value, arg_type=tag)
        old_bytes, new_bytes = legacy.getBinary(), modern.build().dgram
        legacy_decoded = decodeOSC(new_bytes)
        modern_decoded = OscMessage(old_bytes)
        results.append(dict(tag=tag, bytes_equal=old_bytes == new_bytes,
            legacy_tags=legacy_decoded[1], legacy_value=repr(legacy_decoded[2]),
            modern_value=repr(modern_decoded.params[0])))
    return results


def main():
    output = {'census': census(), 'python': sys.version,
              'libraries': {p: dict(version=importlib.metadata.version(p),
                   requires_python=importlib.metadata.metadata(p).get('Requires-Python'))
                   for p in ('pyOSC3', 'python-osc')}}
    cases = [
        ('report', '/all/os/to', ['probe-node', 'report'], False),
        ('wrong-uid', '/all/os/to', ['other', 'report'], False),
        ('unknown-verb', '/all/os/to', ['probe-node', 'future-verb'], False),
        ('enabled', '/all/os/to', ['probe-node', 'enabled', 0], False),
        ('enabled-fraction', '/all/os/to', ['probe-node', 'enabled', .5], False),
        ('log-invalid', '/all/os/to', ['probe-node', 'log-config', '{}'], False),
        ('wifi-unmanaged', '/all/os/to', ['probe-node', 'wifi-config', '{}'], False),
        ('wifi-performance', '/all/os/to', ['probe-node', 'wifi-config', '{}'], True),
        ('write-invalid', '/all/os/to', ['probe-node', 'io-write', '{}'], False),
        ('write-performance', '/all/os/to', ['probe-node', 'io-write', '{"name":"adc","command":"clear","args":[]}'], True),
        ('reinit-invalid', '/all/os/to', ['probe-node', 'io-reinit', 'a/b'], False),
        ('stream-invalid', '/all/os/to', ['probe-node', 'io-stream', .5], False),
        ('stream-performance', '/all/os/to', ['probe-node', 'io-stream', 1], True),
        ('stream-close', '/all/os/to', ['probe-node', 'io-stream', 0], False),
        ('scan-no-bus', '/all/os/to', ['probe-node', 'io-scan'], False),
        ('reinit-extra', '/all/os/to', ['probe-node', 'io-reinit', 'adc', 'extra'], False),
        ('scan-extra', '/all/os/to', ['probe-node', 'io-scan', 'extra'], False),
        ('performance-enter', '/all/os/performance', [1], False),
        ('performance-invalid', '/all/os/performance', ['1'], False),
        ('groups', '/all/os/groups', ['probe-node', 2, 0], False),
        ('groups-invalid', '/all/os/groups', ['probe-node', 2, 2], False),
        ('assign-fraction', '/all/os/assign', ['probe-node', 3.5, 'probe'], False),
        ('assign-valid', '/all/os/assign', ['probe-node', 3, 'probe', 1.0, 2.0], False),
        ('assign-string', '/all/os/assign', ['probe-node', '3', 'probe'], False),
        ('assign-odd-positions', '/all/os/assign', ['probe-node', 3, 'probe', 1.0], False),
        ('ping', '/all/os/ping', ['nonce'], False),
        ('ping-float', '/all/os/ping', [.5], False),
        ('ping-double', '/all/os/ping', [.5], False, ['d']),
        ('sync-invalid-seq', '/sync/ping', ['bad', '123'], False),
        ('probe-id', '/all/os/probe', ['id'], False),
        ('probe-performance', '/all/os/probe', ['id'], True),
        ('params-absent', '/all/os/params', [], False),
    ]
    # Keep import warnings out of machine-readable evidence.
    with contextlib.redirect_stdout(io.StringIO()):
        node = load_node()
        output['parity'] = [probe(node, *case) for case in cases]
        output['manifest_probe'] = manifest_probe()
        output['codec_probe'] = codec_probe()
        node.param_generator.close()
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
