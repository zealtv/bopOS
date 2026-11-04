# sys_input.py
"""
Always-on USB/Bluetooth key and pointer input (thread 84-key-input).

A headless node runs Pd -nogui, so [key] hears nothing and the kernel hands
keystrokes to the tty1 login prompt. This reads /dev/input directly, grabs
each device so the console stops seeing it, and reports:

  /io/key <name> <1|0>          a key went down or up (autorepeat ignored)
  /io/mouse <button> <1|0>      left, right, middle, side, extra, touch
  /io/mouse xy <x> <y>          pointer position, 0-1 each, origin top-left
  /io/mouse move <dx> <dy>      raw relative counts in one report
  /io/mouse wheel <steps>       vertical wheel (hwheel for horizontal)

Relative devices share one virtual pointer that starts centred and spans
SURFACE_COUNTS counts per axis; absolute devices (touchscreens, tablets) set
it from their own axis range. Unplugging releases anything still held.
"""

import fcntl
import os
import select
import struct
import time

SYS_INPUT = '/sys/class/input'
DEV_INPUT = '/dev/input'
RESCAN_S = 2.0
SURFACE_COUNTS = 2000   # relative counts across the virtual surface, per axis

# struct input_event: timeval (two native longs) then type, code, value.
EVENT = struct.Struct('llHHi')
EVIOCGRAB = 0x40044590
EVIOCGABS = 0x80184540  # + axis; struct input_absinfo is six int32s
ABSINFO = struct.Struct('6i')

EV_SYN, EV_KEY, EV_REL, EV_ABS = 0, 1, 2, 3
SYN_REPORT = 0
REL_X, REL_Y, REL_HWHEEL, REL_WHEEL = 0, 1, 6, 8
ABS_X, ABS_Y = 0, 1
BUSES = {0x03, 0x05}    # USB and Bluetooth; skips HDMI-CEC and GPIO keys

BUTTONS = {0x110: 'left', 0x111: 'right', 0x112: 'middle', 0x113: 'side',
           0x114: 'extra', 0x14a: 'touch'}

# Linux input-event-codes.h names, lowercased without KEY_. Number-row keys
# keep the prefix (key_1): a bare "1" reaches Pd as a symbol [route 1] can't
# match. Codes not listed arrive as code_<n>.
KEYS = {1: 'esc', 12: 'minus', 13: 'equal', 14: 'backspace', 15: 'tab',
        26: 'leftbrace', 27: 'rightbrace', 28: 'enter', 29: 'leftctrl',
        39: 'semicolon', 40: 'apostrophe', 41: 'grave', 42: 'leftshift',
        43: 'backslash', 51: 'comma', 52: 'dot', 53: 'slash',
        54: 'rightshift', 55: 'kpasterisk', 56: 'leftalt', 57: 'space',
        58: 'capslock', 69: 'numlock', 70: 'scrolllock', 74: 'kpminus',
        78: 'kpplus', 83: 'kpdot', 87: 'f11', 88: 'f12', 96: 'kpenter',
        97: 'rightctrl', 98: 'kpslash', 99: 'sysrq', 100: 'rightalt',
        102: 'home', 103: 'up', 104: 'pageup', 105: 'left', 106: 'right',
        107: 'end', 108: 'down', 109: 'pagedown', 110: 'insert',
        111: 'delete', 113: 'mute', 114: 'volumedown', 115: 'volumeup',
        119: 'pause', 125: 'leftmeta', 126: 'rightmeta', 127: 'compose'}
KEYS.update({2 + i: f'key_{(i + 1) % 10}' for i in range(10)})
KEYS.update(zip(range(16, 26), 'qwertyuiop'))
KEYS.update(zip(range(30, 39), 'asdfghjkl'))
KEYS.update(zip(range(44, 51), 'zxcvbnm'))
KEYS.update({59 + i: f'f{i + 1}' for i in range(10)})
KEYS.update(zip((71, 72, 73, 75, 76, 77, 79, 80, 81, 82),
                ('kp7', 'kp8', 'kp9', 'kp4', 'kp5', 'kp6', 'kp1', 'kp2', 'kp3', 'kp0')))


def key_name(code):
    return KEYS.get(code, f'code_{code}')


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _bits(text):
    """A sysfs capability bitmap: space-separated hex words, most significant first."""
    value = 0
    for word in (text or '0').split():
        value = (value << 64) | int(word, 16)
    return value


def candidates(sys_input=SYS_INPUT):
    """Event device names for external devices that report keys or pointer motion."""
    found = []
    try:
        names = sorted(os.listdir(sys_input))
    except OSError:
        return found
    for name in names:
        if not name.startswith('event'):
            continue
        device = os.path.join(sys_input, name, 'device')
        bustype = _read(os.path.join(device, 'id', 'bustype'))
        try:
            if bustype is None or int(bustype, 16) not in BUSES:
                continue
        except ValueError:
            continue
        ev = _bits(_read(os.path.join(device, 'capabilities', 'ev')))
        if ev & ((1 << EV_KEY) | (1 << EV_REL) | (1 << EV_ABS)):
            found.append(name)
    return found


class Pointer:
    """One virtual pointer, shared by every relative device."""
    def __init__(self):
        self.x = self.y = 0.5


class Device:
    """Turns one device's events into /io/key and /io/mouse messages."""
    def __init__(self, name, send, pointer, ranges=None):
        self.name = name
        self.send = send
        self.pointer = pointer
        self.ranges = ranges or {}   # axis -> (minimum, maximum)
        self.held = set()            # (address, name) still down
        self.dx = self.dy = 0
        self.absolute = {}

    def event(self, kind, code, value):
        if kind == EV_KEY:
            if value == 2:           # autorepeat
                return
            address = '/io/mouse' if code in BUTTONS else '/io/key'
            label = BUTTONS.get(code) or key_name(code)
            (self.held.add if value else self.held.discard)((address, label))
            self.send(address, label, 1 if value else 0)
        elif kind == EV_REL:
            if code == REL_X:
                self.dx += value
            elif code == REL_Y:
                self.dy += value
            elif code == REL_WHEEL:
                self.send('/io/mouse', 'wheel', value)
            elif code == REL_HWHEEL:
                self.send('/io/mouse', 'hwheel', value)
        elif kind == EV_ABS and code in (ABS_X, ABS_Y) and code in self.ranges:
            low, high = self.ranges[code]
            if high > low:
                self.absolute[code] = min(1.0, max(0.0, (value - low) / (high - low)))
        elif kind == EV_SYN and code == SYN_REPORT:
            self._report()

    def _report(self):
        p = self.pointer
        if self.dx or self.dy:
            self.send('/io/mouse', 'move', self.dx, self.dy)
            p.x = min(1.0, max(0.0, p.x + self.dx / SURFACE_COUNTS))
            p.y = min(1.0, max(0.0, p.y + self.dy / SURFACE_COUNTS))
            self.dx = self.dy = 0
            self.send('/io/mouse', 'xy', p.x, p.y)
        if self.absolute:
            p.x = self.absolute.pop(ABS_X, p.x)
            p.y = self.absolute.pop(ABS_Y, p.y)
            self.send('/io/mouse', 'xy', p.x, p.y)

    def release(self):
        """A device that vanished mid-press must not leave a note held."""
        for address, label in sorted(self.held):
            self.send(address, label, 0)
        self.held.clear()


class InputReader:
    """Opens, grabs and reads every candidate device; rescans for hotplug."""
    def __init__(self, send, sys_input=SYS_INPUT, dev_input=DEV_INPUT):
        self.send = send
        self.sys_input = sys_input
        self.dev_input = dev_input
        self.pointer = Pointer()
        self.open = {}   # fd -> Device
        self.running = True

    def _label(self, name):
        return _read(os.path.join(self.sys_input, name, 'device', 'name')) or name

    def rescan(self):
        known = {device.name for device in self.open.values()}
        for name in candidates(self.sys_input):
            if name in known:
                continue
            try:
                fd = os.open(os.path.join(self.dev_input, name), os.O_RDONLY | os.O_NONBLOCK)
            except OSError as error:
                # Usually permissions: pi needs the input group.
                print(f"Input {name} ({self._label(name)}) not readable: {error}")
                continue
            try:
                fcntl.ioctl(fd, EVIOCGRAB, 1)
            except OSError as error:
                print(f"Input {name}: could not grab ({error}); the console sees it too")
            ranges = {}
            for axis in (ABS_X, ABS_Y):
                try:
                    info = ABSINFO.unpack(fcntl.ioctl(fd, EVIOCGABS + axis, bytes(ABSINFO.size)))
                    ranges[axis] = (info[1], info[2])
                except OSError:
                    pass
            self.open[fd] = Device(name, self.send, self.pointer, ranges)
            print(f"Input {name} ({self._label(name)}) open")

    def close(self, fd):
        device = self.open.pop(fd)
        device.release()
        try:
            os.close(fd)
        except OSError:
            pass
        print(f"Input {device.name} closed")

    def read(self, fd):
        try:
            data = os.read(fd, EVENT.size * 64)
        except BlockingIOError:
            return
        except OSError:
            self.close(fd)   # ENODEV: unplugged
            return
        if not data:
            self.close(fd)
            return
        device = self.open[fd]
        for offset in range(0, len(data) - EVENT.size + 1, EVENT.size):
            _, _, kind, code, value = EVENT.unpack_from(data, offset)
            device.event(kind, code, value)

    def run(self):
        next_scan = 0.0
        while self.running:
            if time.monotonic() >= next_scan:
                self.rescan()
                next_scan = time.monotonic() + RESCAN_S
            if not self.open:
                time.sleep(RESCAN_S)
                continue
            ready, _, _ = select.select(list(self.open), [], [], RESCAN_S)
            for fd in ready:
                if fd in self.open:
                    self.read(fd)
        for fd in list(self.open):
            self.close(fd)
