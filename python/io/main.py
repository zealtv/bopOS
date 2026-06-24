#!/usr/bin/env python3
"""
BopOS I2C to OSC Bridge
Simple interface between I2C sensors and Pure Data via OSC
"""

import time
import threading
import signal
from pyOSC3 import OSCClient, OSCMessage, OSCBundle, OSCServer

# Settings
PYTHON_PORT = 8880      # This script listens here for commands from Pure Data
PD_PORT = 6662          # Pure Data listens here for messages from this script
DEFAULT_POLL_RATE = 10  # Hz

# Available peripheral types
PERIPHERAL_TYPES = {
    'ads1015': ('io_ads1015', 'IO_ADS1015'), # 4 channel 12-bit ADC
    'ads1115': ('io_ads1115', 'IO_ADS1115'), # 4 channel 16-bit ADC
    'lis3dh': ('io_lis3dh', 'IO_LIS3DH'), # 3-axis accelerometer
    'mpr121': ('io_mpr121', 'IO_MPR121'), # 12-channel capacitive touch sensor
}

class IOManager:
    def __init__(self):
        self.peripherals = {}  # name -> peripheral instance
        self.poll_rate = DEFAULT_POLL_RATE
        self.running = True
        
        # OSC client for sending to PD
        self.osc_client = OSCClient()
        self.osc_client.connect(("127.0.0.1", PD_PORT))
    
    def create_peripheral(self, name, device_type, address):
        """
        Dynamically create a peripheral.
        
        Args:
            name: Unique name for this peripheral (e.g., 'adc1', 'tilt')
            device_type: Type from PERIPHERAL_TYPES (e.g., 'ads1015')
            address: I2C address as int (e.g., 0x48)
        """
        if name in self.peripherals:
            print(f"Warning: {name} already exists, replacing...")
        
        if device_type not in PERIPHERAL_TYPES:
            print(f"Error: Unknown device type '{device_type}'")
            print(f"Available types: {list(PERIPHERAL_TYPES.keys())}")
            return False
        
        try:
            # Import the peripheral class
            module_name, class_name = PERIPHERAL_TYPES[device_type]
            module = __import__(module_name)
            peripheral_class = getattr(module, class_name)
            
            # Create instance
            peripheral = peripheral_class(bus=None, address=address)
            peripheral.name = name  # Override name with custom name
            peripheral.setup()
            
            self.peripherals[name] = peripheral
            print(f"✓ Created {name} ({device_type} @ 0x{address:02X})")
            return True
            
        except Exception as e:
            print(f"✗ Failed to create {name}: {e}")
            return False
    
    def poll_and_send(self):
        """
        Poll all peripherals and send single OSC bundle to PD.
        """
        if not self.peripherals:
            return
        
        # Build OSC bundle
        bundle = OSCBundle()
        
        # Read data from each peripheral
        for name, peripheral in list(self.peripherals.items()):
            try:
                data = peripheral.read_data()
                
                # Add message to bundle
                msg = OSCMessage(f"/{name}")
                
                # Handle different return types
                if isinstance(data, dict):
                    # Send dict values in order
                    for value in data.values():
                        msg.append(value)
                elif isinstance(data, (list, tuple)):
                    for value in data:
                        msg.append(value)
                else:
                    msg.append(data)
                
                bundle.append(msg)
                
            except Exception as e:
                print(f"Error reading {name}: {e}")
        
        # Send bundle to PD
        try:
            self.osc_client.send(bundle)
        except Exception as e:
            print(f"Error sending OSC: {e}")
    
    def handle_command(self, address, tags, args, source):
        """
        Handle OSC commands from PD.
        """
        parts = address.strip('/').split('/')
        
        # /create <name> <type> <address>
        if parts[0] == 'create':
            if len(args) >= 3:
                name = str(args[0])
                device_type = str(args[1])
                i2c_addr = int(args[2], 16) if isinstance(args[2], str) else int(args[2])
                self.create_peripheral(name, device_type, i2c_addr)
        
        # /poll <rate>
        elif parts[0] == 'poll':
            if len(args) > 0:
                self.poll_rate = max(0.1, float(args[0]))
                print(f"Poll rate set to {self.poll_rate} Hz")
        
        # /list
        elif parts[0] == 'report':
            print("\nActive peripherals:")
            for name, peripheral in self.peripherals.items():
                print(f"  {name}: {peripheral.__class__.__name__}")
        
        # /<peripheral>/<command> - send to specific peripheral
        elif len(parts) >= 2 and parts[0] in self.peripherals:
            peripheral_name = parts[0]
            command = '/'.join(parts[1:])
            peripheral = self.peripherals[peripheral_name]
            
            try:
                peripheral.write_data(command=command, args=args)
            except Exception as e:
                print(f"Error writing to {peripheral_name}: {e}")
    
    def run(self):
        """
        Main loop: poll sensors and send OSC bundle.
        """
        print(f"\nBopOS I/O Bridge Running")
        print(f"Python listening on port {PYTHON_PORT}")
        print(f"Sending to PD on port {PD_PORT}")
        print(f"Poll rate: {self.poll_rate} Hz")
        print(f"\nCommands:")
        print(f"  /create <name> <type> <address>")
        print(f"  /poll <rate>")
        print(f"  /report")
        print(f"\nPress Ctrl+C to quit\n")
        
        # Setup OSC server in separate thread
        server = OSCServer(("127.0.0.1", PYTHON_PORT))
        server.addMsgHandler("default", self.handle_command)
        
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        # Handle SIGTERM to ensure cleanup runs on external termination
        def signal_handler(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Main polling loop
        try:
            while self.running:
                self.poll_and_send()
                time.sleep(1.0 / self.poll_rate)
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.running = False
            server.close()
            
            # Cleanup all peripherals
            for peripheral in self.peripherals.values():
                peripheral.cleanup()


def main():
    manager = IOManager()
    
    # Optional: Auto-create some peripherals at startup
    # manager.create_peripheral('adc', 'ads1015', 0x48)
    # manager.create_peripheral('tilt', 'lis3dh', 0x19)
    # manager.create_peripheral('touch', 'mpr121', 0x5A)
    
    manager.run()


if __name__ == "__main__":
    import sys
    if "--monitor" in sys.argv:
        from io_mpr121_debug import monitor
        monitor()
    else:
        main()
