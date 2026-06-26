# io_switch.py
"""
PiicoDev Switch / momentary button.
Input peripheral: reports press state to PD each poll.
default address: 0x42
"""

from PiicoDev_Switch import PiicoDev_Switch


class IO_Switch:
    """PiicoDev button - outputs [pressed, was_pressed, was_double_pressed]."""

    def __init__(self, bus=None, address=None):
        self.name = "button"
        self.address = address or 0x42
        self.sw = None

    def setup(self):
        """Initialize the button."""
        self.sw = PiicoDev_Switch(address=self.address)
        print(f"  {self.name}: PiicoDev button ready at 0x{self.address:02X}")

    def read_data(self):
        """
        Returns [pressed, was_pressed, was_double_pressed] as ints.
        - pressed: instantaneous level (1 while held)
        - was_pressed / was_double_pressed: latched edges since last poll
          (reading them clears the latch, so quick taps between polls aren't missed)
        """
        return [
            int(self.sw.is_pressed),
            int(self.sw.was_pressed),
            int(self.sw.was_double_pressed),
        ]

    def write_data(self, **kwargs):
        """Handle PD commands: /button/<command> [args...]."""
        command = kwargs.get('command', '')
        args = kwargs.get('args', [])
        if self.sw is None:
            return

        # /button/led <0|1>  - onboard LED
        if command == 'led' and len(args) >= 1:
            self.sw.led = bool(int(args[0]))

        # /button/double_ms <ms>  - max gap counted as a double-press
        elif command == 'double_ms' and len(args) >= 1:
            self.sw.double_press_duration = int(args[0])

    def cleanup(self):
        """Turn the LED off on shutdown."""
        if self.sw is not None:
            try:
                self.sw.led = False
            except Exception:
                pass
