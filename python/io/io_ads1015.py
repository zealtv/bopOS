# io_ads1015.py
"""
ADS1015 12-bit Analog-to-Digital Converter
Reads 4 analog channels (A0-A3) and returns voltages
"""

import board
import busio
import adafruit_ads1x15.ads1015 as ADS1015
import adafruit_ads1x15.ads1x15 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

class IO_ADS1015:
    """Simple ADS1015 ADC - reads 4 analog channels."""

    def __init__(self, bus=None, address=0x48):
        self.address = address
        self.name = "adc"
        self.ads = None
        self.channels = []
    
    def setup(self):
        """Initialize the ADC hardware."""
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS1015.ADS1015(i2c, address=self.address)
        
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
        # The raw value is a 12-bit integer (0-4095).
        # Divide by 4095.0 to normalize to a 0.0-1.0 float.
        return [ch.voltage  for ch in self.channels]
    
    def write_data(self, **kwargs):
        """ADC is read-only."""
        pass
    
    def cleanup(self):
        """Cleanup on shutdown."""
        pass
