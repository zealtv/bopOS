"""A socket the transport closed ends the read loop quietly (67/28)."""
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
import monitor_transport as transport  # noqa: E402
from server import Dashboard  # noqa: E402


class Socket:
    """Starlette's rule: after this side sends close, receive raises RuntimeError."""
    client = ('192.0.2.9', 6000)

    def __init__(self):
        self.closed = False
        self.receiving = asyncio.Event()

    async def accept(self):
        pass

    async def send_text(self, payload):
        pass

    async def close(self, code):
        self.closed = True

    async def receive_json(self):
        if self.closed:
            raise RuntimeError('WebSocket is not connected. Need to call "accept" first.')
        self.receiving.set()
        await asyncio.Event().wait()


def dashboard():
    async def value():
        await asyncio.sleep(0)   # as the real snapshot builders do
        return {}
    released = []
    stub = SimpleNamespace(
        clients=set(), wifi_confirmations={}, public_state=value, catalog=value,
        osc=SimpleNamespace(send_audition_listener=lambda: None),
        show={}, show_warnings=lambda: [], show_engine=SimpleNamespace(snapshot=lambda: {}),
        state=SimpleNamespace(devices={}),
        editor_input=SimpleNamespace(release=released.append, owner=None))
    stub.monitor_transport = transport.MonitorTransport(stub)
    return stub, released


class SelfCloseTests(unittest.IsolatedAsyncioTestCase):
    async def test_oversized_snapshot_ends_the_loop_without_an_error(self):
        stub, released = dashboard()
        socket = Socket()
        with patch.object(transport, 'SNAPSHOT_BYTES', 10), \
                self.assertLogs('bopos.dashboard', 'WARNING') as logs:
            await asyncio.wait_for(Dashboard.websocket(stub, socket), 1)
        self.assertTrue(socket.closed)
        self.assertFalse(socket.receiving.is_set())
        self.assertEqual(stub.clients, set())
        self.assertEqual(len(released), 1)
        self.assertIn('192.0.2.9:6000: state snapshot is', logs.output[0])
        await stub.monitor_transport.close()


if __name__ == '__main__':
    unittest.main()
