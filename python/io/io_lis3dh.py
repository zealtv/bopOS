# io_lis3dh.py
"""
LIS3DH 3-Axis Accelerometer
Reads tilt/acceleration in x, y, z axes
default address: 0x19 
"""

from PiicoDev_LIS3DH import PiicoDev_LIS3DH

class IO_LIS3DH:
    """LIS3DH accelerometer - outputs x, y, z acceleration in g-forces."""
    
    def __init__(self, bus=None, address=None):
        self.name = "tilt"
        self.motion = None
    
    def setup(self):
        """Initialize the LIS3DH hardware."""
        self.motion = PiicoDev_LIS3DH()
        print(f"  {self.name}: 3-axis accelerometer ready")
    
    def read_data(self):
        """
        Read angle on all 3 axes.
        Returns: [x, y, z] in degrees
        """
        angle = self.motion.angle # This returns a tuple: (x, y, z)
        return [
            angle[0],
            angle[1],
            angle[2]
        ]
    
    def write_data(self, **kwargs):
        """Accelerometer is read-only."""
        pass
    
    def cleanup(self):
        """Cleanup on shutdown."""
        pass
