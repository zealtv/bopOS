"""Simulated /io/key and /io/mouse validation and the editor door (84-key-input)."""
from pathlib import Path
import sys
import types
import unittest

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
for path in (REPO, REPO / 'dashboard'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from python import io_protocol  # noqa: E402
from editor_input import EditorInput  # noqa: E402
from pythonosc.osc_message import OscMessage  # noqa: E402
from pyOSC3 import OSCBundle, OSCMessage  # noqa: E402

sys.path.insert(0, str(REPO / 'python' / 'io'))
import sys_input  # noqa: E402


class Sender:
    def __init__(self):
        self.sent = []

    def sendto(self, data, address):
        message = OscMessage(data)
        self.sent.append((message.address, message.params))

    def close(self):
        pass


class ValidateInputTests(unittest.TestCase):
    def test_accepts_the_bridge_forms(self):
        for address, args, expected in [
                ('key', ['space', 1], ('/io/key', ['space', 1])),
                ('key', ['key_1', 0], ('/io/key', ['key_1', 0])),
                ('mouse', ['left', 1], ('/io/mouse', ['left', 1])),
                ('mouse', ['xy', 0, 1], ('/io/mouse', ['xy', 0.0, 1.0])),
                ('mouse', ['move', -4, 9], ('/io/mouse', ['move', -4, 9])),
                ('mouse', ['wheel', -1], ('/io/mouse', ['wheel', -1]))]:
            with self.subTest(args=args):
                self.assertEqual(io_protocol.validate_input(address, args), expected)

    def test_rejects_anything_else(self):
        for address, args in [('key', ['Space', 1]), ('key', ['a/b', 1]), ('key', ['a', 2]),
                              ('key', ['a', True]), ('key', ['a']), ('mouse', ['xy', 1.5, 0]),
                              ('mouse', ['xy', float('nan'), 0]), ('mouse', ['left', 1, 1]),
                              ('mouse', ['wheel', 1.5]), ('mouse', ['bogus', 1]), ('pad', ['a', 1]),
                              ('key', 'space 1'), ('mouse', [])]:
            with self.subTest(address=address, args=args):
                with self.assertRaises(ValueError):
                    io_protocol.validate_input(address, args)

    def test_buttons_match_what_the_bridge_sends(self):
        self.assertEqual(set(sys_input.BUTTONS.values()), io_protocol.INPUT_BUTTONS)
        for name in sys_input.KEYS.values():
            io_protocol.validate_input('key', [name, 1])


class EditorDoorTests(unittest.TestCase):
    def setUp(self):
        self.state = types.SimpleNamespace(performance=False, data={'editor': {'generation': 3}})
        self.editor = EditorInput(types.SimpleNamespace(supervisor_mode='edit', state=self.state))
        self.editor.source = 'simulated'
        self.editor.sender = self.sender = Sender()

    def send(self, owner, address, *args, generation=3):
        self.editor.send_input({'generation': generation, 'address': address, 'args': list(args)}, owner)

    def test_events_go_out_at_once_and_owner_loss_releases_only_its_presses(self):
        a, b = object(), object()
        self.send(a, 'key', 'space', 1)
        self.send(a, 'mouse', 'left', 1)
        self.send(b, 'key', 'w', 1)
        self.send(a, 'mouse', 'xy', .25, .75)
        self.assertEqual(self.sender.sent, [('/io/key', ['space', 1]), ('/io/mouse', ['left', 1]),
                                            ('/io/key', ['w', 1]), ('/io/mouse', ['xy', .25, .75])])
        self.sender.sent.clear()
        self.editor.release(a)
        self.assertEqual(sorted(self.sender.sent), [('/io/key', ['space', 0]), ('/io/mouse', ['left', 0])])
        self.sender.sent.clear()
        self.send(b, 'key', 'w', 0)
        self.editor.release(b)
        self.assertEqual(self.sender.sent, [('/io/key', ['w', 0])])

    def test_session_end_releases_everything(self):
        self.send(object(), 'key', 'a', 1)
        self.editor.clear()
        self.assertEqual(self.sender.sent[-1], ('/io/key', ['a', 0]))
        self.assertEqual(self.editor.pressed, {})

    def test_refused_outside_a_simulated_session(self):
        cases = [('stale generation', lambda: self.send(None, 'key', 'a', 1, generation=2))]
        for label, change in [('performance', lambda: setattr(self.state, 'performance', True)),
                              ('live source', lambda: setattr(self.editor, 'source', 'uid-a'))]:
            cases.append((label, change))
        for label, action in cases:
            with self.subTest(label):
                self.setUp()
                if label == 'stale generation':
                    with self.assertRaises(ValueError):
                        action()
                else:
                    action()
                    with self.assertRaises(ValueError):
                        self.send(None, 'key', 'a', 1)
                self.assertEqual(self.sender.sent, [])



class LiveDeviceInputTests(unittest.TestCase):
    """A device's keys arrive in its leased stream bundle (v1.25)."""
    def setUp(self):
        self.state = types.SimpleNamespace(performance=False, data={'editor': {'generation': 3}})
        self.editor = EditorInput(types.SimpleNamespace(supervisor_mode='edit', state=self.state))
        self.editor.source = 'uid-a'
        self.editor.sender = self.sender = BundleSender()

    def forward(self, *messages):
        bundle = OSCBundle()
        for address, values in messages:
            message = OSCMessage(address)
            for value in values:
                message.append(value)
            bundle.append(message)
        self.editor.forward(bundle.getBinary(), {})

    def test_bundles_pass_unchanged_and_held_keys_release_with_the_source(self):
        self.forward(('/io/key', ['q', 1]), ('/io/mouse', ['left', 1]), ('/io/mouse', ['xy', .5, .5]))
        self.forward(('/io/key', ['w', 1]), ('/io/key', ['w', 0]), ('/io/mouse', ['wheel', 1]))
        self.assertEqual(len(self.sender.bundles), 2)
        self.assertEqual(set(self.editor.pressed), {('/io/key', 'q'), ('/io/mouse', 'left')})
        self.editor.release_input()
        self.assertEqual(sorted(self.sender.sent), [('/io/key', ['q', 0]), ('/io/mouse', ['left', 0])])
        self.assertEqual(self.editor.pressed, {})


class BundleSender(Sender):
    def __init__(self):
        super().__init__()
        self.bundles = []

    def sendto(self, data, address):
        if data.startswith(b'#bundle'):
            self.bundles.append(data)
        else:
            super().sendto(data, address)


if __name__ == '__main__':
    unittest.main()
