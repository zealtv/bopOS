# io_lis3dh.py
"""
LIS3DH 3-Axis Accelerometer
Reads tilt angles and acceleration in x, y, z axes
default address: 0x19 
"""

from math import atan2, degrees

from PiicoDev_LIS3DH import PiicoDev_LIS3DH

class IO_LIS3DH:
    """LIS3DH accelerometer - outputs x, y, z tilt angles in degrees, then
    x, y, z acceleration in m/s^2."""
    
    def __init__(self, bus=None, address=None):
        self.address = 0x19 if address is None else address
        self.name = "tilt"
        self.motion = None
    
    def setup(self):
        """Initialize the LIS3DH hardware."""
        self.motion = PiicoDev_LIS3DH(address=self.address)
        print(f"  {self.name}: 3-axis accelerometer ready")
    
    def read_data(self):
        """
        Read angle and acceleration on all 3 axes from one sample.
        Returns: [x, y, z] in degrees, then [x, y, z] in m/s^2
        """
        # One read for both: the angles are the library's `angle` formulas,
        # applied here so they match the acceleration they came from.
        x, y, z = self.motion.acceleration
        return [
            degrees(atan2(y, z)),
            degrees(atan2(z, x)),
            degrees(atan2(x, y)),
            x,
            y,
            z
        ]
    
    def write_data(self, **kwargs):
        """Accelerometer is read-only."""
        pass
    
    def cleanup(self):
        """Cleanup on shutdown."""
        pass


# Literal metadata is read by the host without importing this driver.
DESCRIPTION = {
    "inputs": [
        {"channel":"x","unit":"degrees","range":[-180,180]},
        {"channel":"y","unit":"degrees","range":[-180,180]},
        {"channel":"z","unit":"degrees","range":[-180,180]},
        # +/-2 g, the library's default range.
        {"channel":"accel_x","unit":"m/s^2","range":[-19.62,19.62]},
        {"channel":"accel_y","unit":"m/s^2","range":[-19.62,19.62]},
        {"channel":"accel_z","unit":"m/s^2","range":[-19.62,19.62]},
    ],
    "outputs": [

    ],
}
