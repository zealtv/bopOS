"""One device's leased IO stream, shared by server-side consumers.

subscribe(uid, consumer, callback) registers a synchronous callback receiving
(original_bundle_bytes, {module_name: [values...]}). Reusing a consumer key
replaces its callback. unsubscribe(uid, consumer) releases it; the last release
closes the stream. Calls and callbacks run on the dashboard's asyncio loop.
"""
import asyncio
import logging

from pythonosc.osc_message import OscMessage
from python.io_stream import decode_bundle

log = logging.getLogger('bopos.io-stream')
RENEW_SECONDS = 3.0


class IOStreams(asyncio.DatagramProtocol):
    def __init__(self, state, command):
        self.state = state
        self.command = command
        self.uid = None
        self.consumers = {}
        self.renewal = None

    def subscribe(self, uid, consumer, callback):
        if getattr(self.state, 'performance', False):
            raise ValueError('performance')
        if uid not in self.state.devices or not callable(callback):
            raise ValueError('unknown device or invalid callback')
        if self.uid is not None and self.uid != uid:
            raise ValueError('another device already has stream consumers')
        self.consumers[consumer] = callback
        if self.uid is None:
            self.uid = uid
            self._renew()

    def _renew(self):
        self.renewal = None
        if not self.consumers or getattr(self.state, 'performance', False):
            self.close()
            return
        self.command(self.uid, 'io-stream', [1])
        self.renewal = asyncio.get_running_loop().call_later(RENEW_SECONDS, self._renew)

    def unsubscribe(self, uid, consumer):
        if uid != self.uid:
            return
        self.consumers.pop(consumer, None)
        if not self.consumers:
            self.close()

    def close(self, send=True):
        uid, self.uid = self.uid, None
        self.consumers.clear()
        if self.renewal is not None:
            self.renewal.cancel()
            self.renewal = None
        if uid is not None and send:
            self.command(uid, 'io-stream', [0])

    def datagram_received(self, data, addr):
        try:
            message = OscMessage(data)
            if (message.address != '/io/stream' or len(message.params) != 2
                    or message.params[0] != self.uid or not self.consumers
                    or getattr(self.state, 'performance', False)):
                return
            device = self.state.devices.get(self.uid)
            if device is None or device.get('ip') != addr[0]:
                return
            bundle = message.params[1]
            values = {row[0][1:]: row[2:] for row in decode_bundle(bundle)}
        except Exception:
            log.debug('invalid IO stream datagram', exc_info=True)
            return
        for callback in tuple(self.consumers.values()):
            try:
                callback(bundle, values)
            except Exception:
                log.exception('IO stream consumer failed')
