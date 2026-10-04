"""Node-side IO control cache and FIFO attribution on the localhost boundary.

The local protocol has no request IDs: keep one scan and one write outstanding,
and advance each queue on its terminal reply or after 3 seconds without one.
Timeouts drop the request silently on the wire. Value bundles are not
handled here (the development stream is a separate stitch).
"""
from collections import deque
import copy
import json
import threading

from pyOSC3 import OSCMessage
import io_protocol

BRIDGE_REPLY_TIMEOUT_SECONDS = 3.0


class IOControl:
    def __init__(self, uid, send_bridge, broadcast_error, timer_factory=None):
        self.uid = uid
        self.send_bridge = send_bridge
        self.broadcast_error = broadcast_error
        self.lock = threading.RLock()
        self.io = io_protocol.empty_io()
        self.pending = {'scan': deque(), 'write': deque()}
        self.timeouts = {}
        self.timer_factory = timer_factory or threading.Timer

    def close(self):
        with self.lock:
            for timer in self.timeouts.values():
                timer.cancel()
            self.timeouts.clear()
            for jobs in self.pending.values():
                jobs.clear()

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.io)

    def refresh(self):
        self.send_bridge('/io/report', [])

    def _reply(self, kind, job, error=None):
        payload, reply_socket, requester = job
        message = OSCMessage('/os/io-' + kind)
        message.append(self.uid, 's')
        if kind == 'write':
            message.append('err' if error else 'ok', 's')
            result = {key: payload[key] for key in ('name', 'command')}
            result['error'] = error
        else:
            result = self.io
        message.append(json.dumps(result), 's')
        try:
            reply_socket.sendto(message.getBinary(), (requester, 5550))
        except OSError as failure:
            print('IO admin reply dropped:', failure)

    def request(self, kind, raw, reply_socket, requester):
        payload = None
        if kind == 'write':
            value = None
            try:
                value = json.loads(raw)
                payload = io_protocol.validate_write(value)
            except (ValueError, TypeError):
                value = value if isinstance(value, dict) else {}
                payload = {key: value.get(key) if isinstance(value.get(key), str)
                           else ('bridge' if key == 'name' else '')
                           for key in ('name', 'command')}
                self._reply(kind, (payload, reply_socket, requester), 'invalid-arguments')
                return
        with self.lock:
            jobs = self.pending[kind]
            jobs.append((payload, reply_socket, requester))
            if len(jobs) == 1:
                self._start(kind)

    def _start(self, kind):
        job = self.pending[kind][0]
        payload = job[0]
        timer = self.timer_factory(BRIDGE_REPLY_TIMEOUT_SECONDS, self._expire,
                                   args=(kind, job))
        timer.daemon = True
        self.timeouts[kind] = timer
        timer.start()
        try:
            if kind == 'scan':
                self.send_bridge('/io/scan', [])
            else:
                self.send_bridge('/io/' + payload['name'],
                                 [payload['command'], *payload['args']])
        except OSError as failure:
            print('IO bridge send dropped:', failure)

    def _expire(self, kind, job):
        with self.lock:
            # A cancelled callback may already be waiting for the lock. It
            # must not expire the next request after a receipt advances FIFO.
            if self.pending[kind] and self.pending[kind][0] is job:
                self._finish(kind, reply=False)

    def _finish(self, kind, error=None, reply=True):
        timer = self.timeouts.pop(kind, None)
        if timer is not None:
            timer.cancel()
        jobs = self.pending[kind]
        job = jobs.popleft()
        if reply:
            self._reply(kind, job, error)
        if jobs:
            self._start(kind)

    def handle(self, address, args):
        with self.lock:
            if address in ('/io/scanned', '/io/registry') and len(args) == 1:
                try:
                    self.io = io_protocol.validate_io(json.loads(args[0]))
                except (ValueError, TypeError):
                    return
                if address == '/io/scanned' and self.pending['scan']:
                    self._finish('scan')
            elif address == '/io/written' and len(args) == 2:
                jobs = self.pending['write']
                if jobs and (args[0], args[1]) == (
                        jobs[0][0]['name'], jobs[0][0]['command']):
                    self._finish('write')
            elif address == '/io/error' and len(args) == 2:
                name, reason = args
                if (not isinstance(name, str) or not isinstance(reason, str)
                        or reason not in io_protocol.ERRORS):
                    return
                row = self.io['modules'].get(name)
                if row is not None:
                    row.update(state='errored', error=reason)
                try:
                    self.broadcast_error(name, reason)
                except OSError as failure:
                    print('IO error broadcast dropped:', failure)
                jobs = self.pending['write']
                if jobs and jobs[0][0]['name'] == name:
                    self._finish('write', reason)
