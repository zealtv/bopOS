# io_ssd1306.py
"""
SSD1306 OLED display (PiicoDev / generic 128x64 I2C).
Output-only peripheral: PD drives it with text/draw commands over OSC.
default address: 0x3C
"""

from PiicoDev_SSD1306 import create_PiicoDev_SSD1306, WIDTH, HEIGHT

LINE_HEIGHT = 10  # px between text rows; font is 8px tall, so 6 rows fit on 64px


class IO_SSD1306:
    """SSD1306 OLED - text display driven by OSC commands from PD."""

    def __init__(self, bus=None, address=None):
        self.name = "oled"
        self.address = address or 0x3C
        self.display = None

    def setup(self):
        """Initialize the OLED and show a boot splash."""
        self.display = create_PiicoDev_SSD1306(address=self.address)
        self.display.fill(0)
        self.display.text("bopOS", 0, 0, 1)
        self.display.text(self.name, 0, LINE_HEIGHT, 1)
        self.display.show()
        print(f"  {self.name}: SSD1306 OLED ready at 0x{self.address:02X}")

    def read_data(self):
        """Output-only: return [] so the poll loop emits a bare /oled heartbeat."""
        return []

    def write_data(self, **kwargs):
        """Handle PD commands: /oled/<command> [args...]."""
        command = kwargs.get('command', '')
        args = kwargs.get('args', [])
        if self.display is None:
            return

        # /oled/clear
        if command == 'clear':
            self.display.fill(0)
            self.display.show()

        # /oled/text <words...>  -> clear screen, draw on the top row
        elif command == 'text':
            self.display.fill(0)
            self.display.text(self._join(args), 0, 0, 1)
            self.display.show()

        # /oled/line <row> <words...>  -> draw one row, leave the rest (build multi-line)
        elif command == 'line' and len(args) >= 1:
            y = int(args[0]) * LINE_HEIGHT
            self.display.fill_rect(0, y, WIDTH, LINE_HEIGHT, 0)
            self.display.text(self._join(args[1:]), 0, y, 1)
            self.display.show()

        # /oled/invert <0|1>
        elif command == 'invert' and len(args) >= 1:
            self.display.invert(int(args[0]))

        # /oled/contrast <0-255>
        elif command == 'contrast' and len(args) >= 1:
            self.display.setContrast(int(args[0]))

    @staticmethod
    def _join(args):
        return ' '.join(str(a) for a in args)

    def cleanup(self):
        """Blank and power down the panel on shutdown."""
        if self.display is not None:
            self.display.fill(0)
            self.display.show()
            self.display.poweroff()
