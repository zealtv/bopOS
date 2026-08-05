# io_rgb.py
"""
PiicoDev 3x RGB LED module.
Output-only peripheral: PD drives the three LEDs with colour commands over OSC.
default address: 0x08 (ID switches move it up to 0x17)
"""

from PiicoDev_RGB import PiicoDev_RGB, wheel

NUM_LEDS = 3


class IO_RGB:
    """PiicoDev 3x RGB LED - colour output driven by OSC commands from PD."""

    def __init__(self, bus=None, address=None):
        self.name = "rgb"
        self.address = address or 0x08
        self.leds = None

    def setup(self):
        """Initialize the module dark, at a modest brightness."""
        # note: this driver's keyword is `addr`, not `address` like
        # PiicoDev_Switch and PiicoDev_SSD1306 use
        self.leds = PiicoDev_RGB(addr=self.address, bright=50)
        self.leds.clear()
        print(f"  {self.name}: PiicoDev 3x RGB ready at 0x{self.address:02X}")

    def read_data(self):
        """Output-only: return [] so the poll loop emits a bare /rgb heartbeat."""
        return []

    def write_data(self, **kwargs):
        """Handle PD commands: /rgb/<command> [args...]."""
        command = kwargs.get('command', '')
        args = kwargs.get('args', [])
        if self.leds is None:
            return

        # /rgb/pixel <n> <r> <g> <b>  - one LED (0-2), 0-255 each
        if command == 'pixel' and len(args) >= 4:
            n = int(args[0])
            if 0 <= n < NUM_LEDS:
                self.leds.setPixel(n, self._colour(args[1:4]))
                self.leds.show()

        # /rgb/fill <r> <g> <b>  - all three the same colour
        elif command == 'fill' and len(args) >= 3:
            self.leds.fill(self._colour(args[0:3]))

        # /rgb/all <r g b r g b r g b>  - all three at once, one I2C write,
        # so a whole-strip change lands in a single frame with no tearing
        elif command == 'all' and len(args) >= 9:
            for n in range(NUM_LEDS):
                self.leds.setPixel(n, self._colour(args[n * 3:n * 3 + 3]))
            self.leds.show()

        # /rgb/hsv <n> <hue> [sat] [val]  - hue/sat/val 0-1; n = -1 fills
        # (PD side is usually a phasor~ or a fader, so 0-1 beats 0-255 here)
        elif command == 'hsv' and len(args) >= 2:
            n = int(args[0])
            colour = wheel(float(args[1]) % 1.0,
                           float(args[2]) if len(args) >= 3 else 1.0,
                           float(args[3]) if len(args) >= 4 else 1.0)
            if n < 0:
                self.leds.fill(self._colour(colour))
            elif n < NUM_LEDS:
                self.leds.setPixel(n, self._colour(colour))
                self.leds.show()

        # /rgb/clear  - blank all three
        elif command == 'clear':
            self.leds.clear()

        # /rgb/bright <0-255>  - global brightness
        elif command == 'bright' and len(args) >= 1:
            self.leds.setBrightness(self._byte(args[0]))

        # /rgb/power <0|1>  - onboard green power LED
        elif command == 'power' and len(args) >= 1:
            self.leds.pwrLED(bool(int(args[0])))

    @staticmethod
    def _byte(value):
        """Clamp to 0-255. PD sends floats, and the driver packs raw bytes()
        which raises on anything outside that range."""
        return max(0, min(255, int(round(float(value)))))

    @classmethod
    def _colour(cls, args):
        return [cls._byte(args[0]), cls._byte(args[1]), cls._byte(args[2])]

    def cleanup(self):
        """Go dark on shutdown."""
        if self.leds is not None:
            try:
                self.leds.clear()
            except Exception:
                pass
