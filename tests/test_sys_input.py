"""Key and pointer input checks without /dev/input or hardware (84-key-input)."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
IO_DIR = Path(__file__).resolve().parents[1] / 'python' / 'io'
spec = importlib.util.spec_from_file_location('sys_input_under_test', IO_DIR / 'sys_input.py')
sys_input = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sys_input)

KEY, REL, ABS, SYN = sys_input.EV_KEY, sys_input.EV_REL, sys_input.EV_ABS, sys_input.EV_SYN


def device(root, name, bustype, ev):
    base = Path(root, name, 'device')
    (base / 'id').mkdir(parents=True)
    (base / 'capabilities').mkdir()
    (base / 'id' / 'bustype').write_text(bustype + '\n')
    (base / 'capabilities' / 'ev').write_text(ev + '\n')
    (base / 'name').write_text(f'{name} device\n')


class InputTests(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.pointer = sys_input.Pointer()
        self.device = sys_input.Device('event0', lambda *m: self.sent.append(m), self.pointer,
                                       {sys_input.ABS_X: (0, 100), sys_input.ABS_Y: (0, 200)})

    def feed(self, *events):
        for event in events:
            self.device.event(*event)

    def test_key_names_follow_kernel_names_with_number_row_prefixed(self):
        self.assertEqual([sys_input.key_name(c) for c in (57, 17, 103, 2, 11, 59, 68, 82, 999)],
                         ['space', 'w', 'up', 'key_1', 'key_0', 'f1', 'f10', 'kp0', 'code_999'])

    def test_keys_and_buttons_split_by_address_and_autorepeat_is_ignored(self):
        self.feed((KEY, 57, 1), (KEY, 57, 2), (KEY, 57, 0), (KEY, 0x110, 1), (KEY, 0x111, 0))
        self.assertEqual(self.sent, [('/io/key', 'space', 1), ('/io/key', 'space', 0),
                                     ('/io/mouse', 'left', 1), ('/io/mouse', 'right', 0)])

    def test_relative_motion_reports_once_per_sync_and_clamps(self):
        self.feed((REL, 0, 100), (REL, 1, -50), (REL, 0, 100), (SYN, 0, 0))
        self.assertEqual(self.sent, [('/io/mouse', 'move', 200, -50),
                                     ('/io/mouse', 'xy', 0.6, 0.475)])
        self.sent.clear()
        self.feed((SYN, 0, 0), (REL, 0, 10 ** 6), (SYN, 0, 0))
        self.assertEqual(self.sent[-1], ('/io/mouse', 'xy', 1.0, 0.475))

    def test_wheel_and_absolute_axes(self):
        self.feed((REL, 8, -1), (REL, 6, 2), (ABS, 0, 25), (ABS, 1, 300), (SYN, 0, 0))
        self.assertEqual(self.sent, [('/io/mouse', 'wheel', -1), ('/io/mouse', 'hwheel', 2),
                                     ('/io/mouse', 'xy', 0.25, 1.0)])

    def test_unplug_releases_held_keys_and_buttons(self):
        reader = sys_input.InputReader(lambda *m: self.sent.append(m))
        read, write = os.pipe()
        os.set_blocking(read, False)
        reader.open[read] = sys_input.Device('event3', reader.send, reader.pointer)
        os.write(write, b''.join(sys_input.EVENT.pack(0, 0, kind, code, value) for kind, code, value in
                                 [(KEY, 30, 1), (KEY, 0x110, 1), (SYN, 0, 0)]))
        os.close(write)
        with contextlib.redirect_stdout(io.StringIO()):
            reader.read(read)
            reader.read(read)   # EOF stands in for ENODEV
        self.assertEqual(self.sent, [('/io/key', 'a', 1), ('/io/mouse', 'left', 1),
                                     ('/io/key', 'a', 0), ('/io/mouse', 'left', 0)])
        self.assertEqual(reader.open, {})

    def test_candidates_are_external_devices_with_keys_or_pointers(self):
        with tempfile.TemporaryDirectory() as root:
            device(root, 'event0', '0003', '120013')    # USB keyboard
            device(root, 'event1', '0005', '17')        # Bluetooth mouse
            device(root, 'event2', '0019', '3')         # GPIO power key
            device(root, 'event3', '0003', '1')         # USB, sync only
            Path(root, 'mouse0').mkdir()
            self.assertEqual(sys_input.candidates(root), ['event0', 'event1'])
        self.assertEqual(sys_input.candidates('/nonexistent'), [])

    def test_bitmaps_join_words_most_significant_first(self):
        self.assertEqual(sys_input._bits('1 0'), 1 << 64)
        self.assertEqual(sys_input._bits(None), 0)


if __name__ == '__main__':
    unittest.main()
