# io_template.py
"""
Template for creating new peripheral modules.

Copy this file and rename it (e.g., 'io_leds.py')
Fill in the methods below with your device-specific code.
"""

class PeripheralTemplate:
    """
    Template for I2C peripherals.
    Replace 'PeripheralTemplate' with your device name (e.g., 'LEDMatrix').
    """
    
    def __init__(self, bus=None, address=0x00):
        """
        Args:
            bus: Not used (kept for compatibility)
            address: I2C address of your device
        """
        self.address = address
        self.name = "mydevice"  # Used in OSC paths: /mydevice/data
        
        # Add device-specific variables here
        self.device = None
    
    def setup(self):
        """
        Initialize the hardware - called once at startup.
        
        This is where you:
        - Create I2C connection
        - Configure device settings
        - Perform calibration
        """
        # Example using Adafruit library:
        # import board
        # import busio
        # import adafruit_yourdevice
        # 
        # i2c = busio.I2C(board.SCL, board.SDA)
        # self.device = adafruit_yourdevice.YourDevice(i2c, address=self.address)
        
        print(f"  {self.name}: initialized at 0x{self.address:02X}")
    
    def read_data(self):
        """
        Read current values from the device.
        
        Returns:
            Can return:
            - A list/tuple: [value1, value2, value3]
            - A dict: {"temperature": 25.3, "humidity": 60}
            - A single value: 123
        
        The data will be sent to PD as: /mydevice/data [values...]
        """
        # Example: Read temperature sensor
        # temperature = self.device.temperature
        # return [temperature]
        
        # Example: Read multi-value sensor
        # return {
        #     "x": self.device.acceleration.x,
        #     "y": self.device.acceleration.y,
        #     "z": self.device.acceleration.z
        # }
        
        return [0]  # Replace with actual reading
    
    def write_data(self, **kwargs):
        """
        Write values to the device (for outputs/actuators).
        
        Args:
            **kwargs: Contains 'command' (str) and 'args' (list)
        
        This is called when PD sends: /mydevice/command [args...]
        """
        command = kwargs.get('command', '')
        args = kwargs.get('args', [])
        
        # Example: Set LED brightness
        # if command == 'brightness' and len(args) > 0:
        #     brightness = int(args[0])
        #     self.device.brightness = brightness
        
        # Example: Set RGB color
        # if command == 'color' and len(args) >= 3:
        #     r, g, b = int(args[0]), int(args[1]), int(args[2])
        #     self.device.fill((r, g, b))
        
        pass
    
    def cleanup(self):
        """
        Clean up when shutting down (optional).
        
        Use this to:
        - Turn off LEDs
        - Put device in low power mode
        """
        pass


# ============================================================
# EXAMPLE: Temperature Sensor
# ============================================================
# 
# import board
# import busio
# import adafruit_tmp102
# 
# class Temperature:
#     def __init__(self, bus=None, address=0x48):
#         self.address = address
#         self.name = "temp"
#         self.sensor = None
#     
#     def setup(self):
#         i2c = busio.I2C(board.SCL, board.SDA)
#         self.sensor = adafruit_tmp102.TMP102(i2c, address=self.address)
#         print(f"  {self.name}: temperature sensor ready")
#     
#     def read_data(self):
#         celsius = self.sensor.temperature
#         return [round(celsius, 2)]
#     
#     def write_data(self, **kwargs):
#         pass  # Read-only sensor
#     
#     def cleanup(self):
#         pass


# ============================================================
# EXAMPLE: LED Strip (Output)
# ============================================================
# 
# import board
# import neopixel
# 
# class LEDStrip:
#     def __init__(self, bus=None, address=None):
#         self.name = "leds"
#         self.pixels = None
#         self.num_leds = 10
#     
#     def setup(self):
#         self.pixels = neopixel.NeoPixel(
#             board.D18, self.num_leds, brightness=0.2
#         )
#         print(f"  {self.name}: {self.num_leds} LEDs ready")
#     
#     def read_data(self):
#         # Return current state if needed
#         return [0]
#     
#     def write_data(self, **kwargs):
#         command = kwargs.get('command', '')
#         args = kwargs.get('args', [])
#         
#         # /leds/fill r g b
#         if command == 'fill' and len(args) >= 3:
#             r, g, b = int(args[0]), int(args[1]), int(args[2])
#             self.pixels.fill((r, g, b))
#         
#         # /leds/pixel n r g b
#         elif command == 'pixel' and len(args) >= 4:
#             n = int(args[0])
#             r, g, b = int(args[1]), int(args[2]), int(args[3])
#             if 0 <= n < self.num_leds:
#                 self.pixels[n] = (r, g, b)
#     
#     def cleanup(self):
#         self.pixels.fill((0, 0, 0))
