"""Development-only IO leases and byte-preserving OSC bundle forwarding."""
import json
import threading
import time

from pyOSC3 import OSCMessage, OSCServer, decodeOSC

LEASE_SECONDS = 10.0
STREAM_PORT = 5551


class Lease:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.until = 0.0
        self.destination = None

    @property
    def active(self):
        return self.destination is not None and self.clock() < self.until

    def close(self):
        self.destination = None
        self.until = 0.0

    def request(self, args, requester, allowed=True):
        error = None
        if len(args) != 1 or type(args[0]) is not int or args[0] not in (0, 1):
            error = 'invalid-arguments'
        elif not allowed:
            self.close()
            error = 'performance'
        elif args[0]:
            self.destination = requester
            self.until = self.clock() + LEASE_SECONDS
        else:
            self.close()
        return {'active': self.active, 'error': error}


def decode_bundle(packet):
    """Accept only a poll bundle of flat module messages, never control replies."""
    if not isinstance(packet, bytes) or not packet.startswith(b'#bundle\x00'):
        raise ValueError('expected an OSC bundle')
    try:
        decoded = decodeOSC(packet)
    except Exception as error:
        raise ValueError('invalid OSC bundle') from error
    if len(decoded) < 2 or decoded[0] != '#bundle':
        raise ValueError('invalid OSC bundle')
    for message in decoded[2:]:
        if (len(message) < 2 or not isinstance(message[0], str)
                or not message[0].startswith('/')
                or len(message[0].split('/')) != 2
                or not message[0][1:]):
            raise ValueError('expected module value messages')
    return decoded[2:]


def stream_packet(uid, bundle):
    message = OSCMessage('/io/stream')
    message.append(uid, 's')
    message.append(bundle, 'b')
    return message.getBinary()


class NodeStream:
    def __init__(self, uid, send_bridge, send_value, allowed,
                 clock=time.monotonic, timer=threading.Timer):
        self.uid = uid
        self.send_bridge = send_bridge
        self.send_value = send_value
        self.allowed = allowed
        self.lease = Lease(clock)
        self.lock = threading.RLock()
        self.timer_factory = timer
        self.timer = None

    def _bridge(self, value):
        try:
            self.send_bridge('/io/stream', [value])
        except OSError as error:
            # The independent bridge timeout bounds copying even after a lost close.
            print('WARNING: IO stream bridge command failed:', error)

    def _cancel_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def close(self):
        with self.lock:
            self.lease.close()
            self._cancel_timer()
            self._bridge(0)

    def _expire(self):
        with self.lock:
            # A canceled timer may already be waiting for the lock. A renewal
            # has its own timer and must not be closed by the old callback.
            if not self.lease.active:
                self.close()

    def request(self, args, reply_socket, requester):
        with self.lock:
            result = self.lease.request(args, requester, self.allowed())
            if result['error'] != 'invalid-arguments':
                self._cancel_timer()
                self._bridge(int(result['active']))
                if result['active']:
                    self.timer = self.timer_factory(LEASE_SECONDS, self._expire)
                    self.timer.daemon = True
                    self.timer.start()
            message = OSCMessage('/os/io-stream')
            for value in (self.uid, 'err' if result['error'] else 'ok',
                          json.dumps(result)):
                message.append(value, 's')
            reply_socket.sendto(message.getBinary(), (requester, 5550))

    def forward(self, packet):
        with self.lock:
            if not self.allowed() or not self.lease.active:
                return
            try:
                decode_bundle(packet)
                self.send_value(stream_packet(self.uid, packet),
                                (self.lease.destination, STREAM_PORT))
            except (ValueError, TypeError, IndexError, OSError) as error:
                print('WARNING: IO stream packet dropped:', error)


class BridgeReplyServer(OSCServer):
    """Keep value bundle bytes intact; dispatch ordinary IO control as before."""
    def __init__(self, address, stream):
        self.stream = stream
        super().__init__(address)

    def finish_request(self, request, client_address):
        if request[0].startswith(b'#bundle\x00'):
            self.stream.forward(request[0])
        else:
            super().finish_request(request, client_address)
