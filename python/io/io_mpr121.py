# io_mpr121.py
"""
MPR121 Capacitive Touch Sensor
12-channel capacitive touch sensor with filtered data (0-1023)

The MPR121 supports 8 possible I2C addresses, set by connecting the ADDR pin as follows:
ADDR Connection   | I2C Address
------------------|------------
GND               | 0x5A
VDD               | 0x5B
SDA               | 0x5C
SCL               | 0x5D
GND via 10kΩ      | 0x5E
VDD via 10kΩ      | 0x5F
SDA via 10kΩ      | 0x60
SCL via 10kΩ      | 0x61

"""

import board
import busio
import adafruit_mpr121

class IO_MPR121:
    """MPR121 capacitive sensor - reads filtered analog values from 12 electrodes."""
    
    # --- Advanced MPR121 Configuration (Low-Level Register Access) ---
    # Register base addresses (see MPR121 datasheet)
    _CDC_BASE = 0x5C   # Charge Discharge Current, per electrode (E0_CDC ... E11_CDC)
    _CDT_BASE = 0x5E   # Charge Discharge Time, per electrode (E0_CDT ... E11_CDT)
    _FFI_BASE = 0x5D   # First Filter Iteration, per electrode (E0_FFI ... E11_FFI)
    _SFI_BASE = 0x5F   # Second Filter Iteration, per electrode (E0_SFI ... E11_SFI)
    _ESI      = 0x5B   # Electrode Sample Interval (global)
    
    def __init__(self, bus=None, address=0x5A):
        self.address = address
        self.name = "touch"
        self.mpr121 = None
        self.num_electrodes = 12
    
    def setup(self):
        """Initialize the MPR121 hardware."""
        i2c = busio.I2C(board.SCL, board.SDA)
        self.mpr121 = adafruit_mpr121.MPR121(i2c, address=self.address)
        print(f"  {self.name}: 12-channel capacitive touch ready")
    
    def read_data(self):
        """
        Read filtered capacitance from all 12 electrodes.
        Returns: [ch0, ch1, ch2, ..., ch11] values 0-1023
        Higher values = more capacitance/closer proximity
        """
        return [self.mpr121.filtered_data(i) for i in range(self.num_electrodes)]
    
    def write_data(self, **kwargs):
        """
        Configure touch sensor settings.
        Expects kwargs['command'] and kwargs['args']

        Commands:
            threshold: Set touch/release thresholds
                args: [touch_threshold, release_threshold]
            cdc: Set charge/discharge current for an electrode
                args: [electrode (0-11), value (0-255)]
            cdt: Set charge/discharge time for an electrode
                args: [electrode (0-11), value (0-255)]
            ffi: Set first filter iteration for an electrode
                args: [electrode (0-11), value (0-255)]
            sfi: Set second filter iteration for an electrode
                args: [electrode (0-11), value (0-255)]
            esi: Set global electrode sample interval
                args: [value (0-255)]
        """
        command = kwargs.get('command', '').lower()
        args = kwargs.get('args', [])

        if command == 'threshold' and len(args) >= 2:
            touch = int(args[0])
            release = int(args[1])
            self.mpr121.set_thresholds(touch, release)
            print(f"  {self.name}: thresholds set to touch={touch}, release={release}")
        elif command == 'cdc' and len(args) >= 2:
            electrode = int(args[0])
            value = int(args[1])
            self.set_charge_discharge_current(electrode, value)
            print(f"  {self.name}: CDC set for electrode {electrode} to {value}")
        elif command == 'cdt' and len(args) >= 2:
            electrode = int(args[0])
            value = int(args[1])
            self.set_charge_discharge_time(electrode, value)
            print(f"  {self.name}: CDT set for electrode {electrode} to {value}")
        elif command == 'ffi' and len(args) >= 2:
            electrode = int(args[0])
            value = int(args[1])
            self.set_first_filter_iteration(electrode, value)
            print(f"  {self.name}: FFI set for electrode {electrode} to {value}")
        elif command == 'sfi' and len(args) >= 2:
            electrode = int(args[0])
            value = int(args[1])
            self.set_second_filter_iteration(electrode, value)
            print(f"  {self.name}: SFI set for electrode {electrode} to {value}")
        elif command == 'esi' and len(args) >= 1:
            value = int(args[0])
            self.set_electrode_sample_interval(value)
            print(f"  {self.name}: ESI set to {value}")
        else:
            print(f"  {self.name}: Unknown or malformed command '{command}' with args {args}")

    def set_register(self, reg_addr, value):
        """
        Write a byte value to a specific MPR121 register.
        Args:
            reg_addr (int): Register address
            value (int): Value to write (0-255)
        """
        if self.mpr121 is not None:
            self.mpr121._device.write(bytes([reg_addr, value]))
            print(f"Set register 0x{reg_addr:02X} to 0x{value:02X}")
        else:
            print("MPR121 not initialized.")

    def set_charge_discharge_current(self, electrode, value):
        """Set charge/discharge current for a given electrode (0-11)."""
        self.set_register(self._CDC_BASE + electrode, value)

    def set_charge_discharge_time(self, electrode, value):
        """Set charge/discharge time for a given electrode (0-11)."""
        self.set_register(self._CDT_BASE + electrode, value)

    def set_first_filter_iteration(self, electrode, value):
        """Set first filter iteration for a given electrode (0-11)."""
        self.set_register(self._FFI_BASE + electrode, value)

    def set_second_filter_iteration(self, electrode, value):
        """Set second filter iteration for a given electrode (0-11)."""
        self.set_register(self._SFI_BASE + electrode, value)

    def set_electrode_sample_interval(self, value):
        """Set global electrode sample interval."""
        self.set_register(self._ESI, value)

    def cleanup(self):
        """Cleanup on shutdown."""
        pass
