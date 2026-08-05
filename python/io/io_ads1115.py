# io_ads1115.py
"""
ADS1115 16-bit Analog-to-Digital Converter
Reads 4 analog channels (A0-A3) and returns voltages
"""

import board
import busio
import adafruit_ads1x15.ads1115 as ADS1115
import adafruit_ads1x15.ads1x15 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

DATA_RATE = 860     # samples per second; see setup() for why not the default


class IO_ADS1115:
    """Simple ADS1115 ADC - reads 4 analog channels."""

    def __init__(self, bus=None, address=0x48):
        self.address = address
        self.name = "adc"
        self.ads = None
        self.channels = []

    def setup(self):
        """Initialize the ADC hardware."""
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS1115.ADS1115(i2c, address=self.address)

        # The library defaults to 128 SPS, which costs 40 ms to read all four
        # channels and caps the whole bridge at 25 Hz -- slower than a quick
        # button press, which is then never sampled at all. At 860 SPS the same
        # read is 12.6 ms (measured on a real board). The trade is per-sample
        # noise, which does not matter for full-rail switch inputs but would
        # for smooth analog sensing on the same chip.
        self.ads.data_rate = DATA_RATE

        # Create 4 analog input channels
        self.channels = [
            AnalogIn(self.ads, ADS.Pin.A0),
            AnalogIn(self.ads, ADS.Pin.A1),
            AnalogIn(self.ads, ADS.Pin.A2),
            AnalogIn(self.ads, ADS.Pin.A3)
        ]

        print(f"  {self.name}: 4-channel ADC ready")

    def read_data(self):
        """
        Read all 4 channels.
        Returns: [ch0, ch1, ch2, ch3] in volts (0.0-3.3V)
        """
        return [ch.voltage for ch in self.channels]

    def write_data(self, **kwargs):
        """ADC is read-only."""
        pass

    def cleanup(self):
        """Cleanup on shutdown."""
        pass
