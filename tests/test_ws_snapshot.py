#!/usr/bin/env python3
"""The client's snapshot list must match the server's connect burst (51).

`Dashboard.websocket` opens every connection with a burst of full-state
messages so a fresh client can draw itself. `js/ws.js` remembers the latest of
each and replays it to handlers that register after the burst has already been
delivered — which is what stops a consumer loaded in a later `<script>` from
missing it forever.

The two lists are genuinely coupled, and the coupling is invisible from either
side. If the server starts sending an eighth snapshot and `ws.js` does not know
it is one, that message silently reverts to the old behaviour: whoever
registers first gets it, everyone later gets nothing, with no error anywhere.
That is exactly the defect 51 diagnosed, so it is pinned rather than trusted.
"""

import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

SERVER = ROOT / "dashboard" / "server.py"
WS_JS = ROOT / "dashboard" / "static" / "js" / "ws.js"


def connect_burst():
    """The message types `Dashboard.websocket` sends before its receive loop."""
    source = SERVER.read_text()
    start = source.index("async def websocket(self, ws):")
    # The burst ends where the connection starts listening.
    end = source.index("while True:", start)
    return [match.group(1) for match in
            re.finditer(r'send_json\(\{"type": "([a-z_]+)"', source[start:end])]


def declared_snapshots():
    """`SNAPSHOT_TYPES` as `js/ws.js` declares it."""
    source = WS_JS.read_text()
    start = source.index("const SNAPSHOT_TYPES")
    body = source[start:source.index("]", start)]
    return set(re.findall(r'"([a-z_]+)"', body))


class WebSocketSnapshotContractTests(unittest.TestCase):
    def test_client_knows_every_snapshot_the_server_sends_on_connect(self):
        burst = set(connect_burst())
        self.assertTrue(burst, "could not parse the connect burst")
        missing = burst - declared_snapshots()
        self.assertEqual(
            missing, set(),
            "js/ws.js SNAPSHOT_TYPES is missing connect-burst message types "
            f"{sorted(missing)} — a late-registering handler will never "
            "receive them; see tests/test_ws_snapshot.py")

    def test_client_claims_no_snapshot_the_server_does_not_send(self):
        """A type listed here but never sent on connect is replayed from
        whatever arrived last, which is only correct for a full snapshot."""
        extra = declared_snapshots() - set(connect_burst())
        self.assertEqual(
            extra, set(),
            f"js/ws.js declares {sorted(extra)} as snapshots, but the server "
            "does not send them on connect")

    def test_events_still_queue_for_a_first_handler(self):
        """The pending path must survive: it covers a different case.

        A snapshot supersedes; an event must not be dropped just because no
        handler has registered yet. Both branches have to remain in `emit`.
        """
        source = WS_JS.read_text()
        self.assertIn("this.pending[type] ||= []", source)
        self.assertIn("this.latest[type] = data", source)


if __name__ == "__main__":
    unittest.main()
