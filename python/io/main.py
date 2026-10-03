#!/usr/bin/env python3
"""
BopOS I2C to OSC Bridge
Simple interface between I2C sensors and Pure Data via OSC
"""

import time
import math
import threading
import signal
from pyOSC3 import OSCClient, OSCMessage, OSCBundle, OSCServer

from sys_wireless import read_wireless
from sys_i2c import have_bus, scan_bus
from sys_info import (get_hostname, get_ip, get_uptime,
                      get_git_rev, get_active_patch)

# Settings
PYTHON_PORT = 8880      # This script listens here for commands from Pure Data
PD_PORT = 6662          # Pure Data listens here for messages from this script
DEFAULT_POLL_RATE = 10  # Hz

# Peripherals are addressed as /io/<name>, the same namespace the management
# verbs live in, so these names cannot be used for a peripheral.
RESERVED_NAMES = ('create', 'poll', 'report', 'scan')

# Available peripheral types
PERIPHERAL_TYPES = {
    'ads1015': ('io_ads1015', 'IO_ADS1015'), # 4 channel 12-bit ADC
    'ads1115': ('io_ads1115', 'IO_ADS1115'), # 4 channel 16-bit ADC
    'lis3dh': ('io_lis3dh', 'IO_LIS3DH'), # 3-axis accelerometer
    'mpr121': ('io_mpr121', 'IO_MPR121'), # 12-channel capacitive touch sensor
    'rgb': ('io_rgb', 'IO_RGB'), # PiicoDev 3x RGB LED module
    'ssd1306': ('io_ssd1306', 'IO_SSD1306'), # 128x64 OLED display
    'switch': ('io_switch', 'IO_Switch'), # PiicoDev momentary button
}

class IOManager:
    def __init__(self):
        # One lock covers the registry and all chip operations, including
        # scan/setup/cleanup and aliases that happen to share an address.
        self.io_lock = threading.RLock()
        self.peripherals = {}  # name -> peripheral instance
        self.poll_rate = DEFAULT_POLL_RATE
        self.running = True
        
        # OSC client for sending to PD
        self.osc_client = OSCClient()
        self.osc_client.connect(("127.0.0.1", PD_PORT))
    
    def create_peripheral(self, name, device_type, address):
        with self.io_lock:
            return self._create_peripheral(name, device_type, address)

    def _create_peripheral(self, name, device_type, address):
        """
        Dynamically create a peripheral.
        
        Args:
            name: Unique name for this peripheral (e.g., 'adc1', 'tilt')
            device_type: Type from PERIPHERAL_TYPES (e.g., 'ads1015')
            address: I2C address as int (e.g., 0x48)
        """
        if name in RESERVED_NAMES:
            print(f"Error: '{name}' is a reserved /io verb - "
                  f"peripherals share that namespace, pick another name")
            return False

        if name in self.peripherals:
            print(f"Warning: {name} already exists, replacing...")

        if device_type not in PERIPHERAL_TYPES:
            print(f"Error: Unknown device type '{device_type}'")
            print(f"Available types: {list(PERIPHERAL_TYPES.keys())}")
            return False
        
        peripheral = None
        try:
            # Import the peripheral class
            module_name, class_name = PERIPHERAL_TYPES[device_type]
            module = __import__(module_name)
            peripheral_class = getattr(module, class_name)
            
            # Retire the old instance before setup touches the same chip.
            old = self.peripherals.get(name)
            if old is not None:
                old.cleanup()
                del self.peripherals[name]

            # Create instance
            peripheral = peripheral_class(bus=None, address=address)
            peripheral.name = name  # Override name with custom name
            peripheral.setup()
            
            self.peripherals[name] = peripheral
            print(f"✓ Created {name} ({device_type} @ 0x{address:02X})")
            return True
            
        except Exception as e:
            print(f"✗ Failed to create {name}: {e}")
            if peripheral is not None:
                try:
                    peripheral.cleanup()
                except Exception as cleanup_error:
                    print(f"Error cleaning failed create {name}: {cleanup_error}")
            return False
    
    def poll_and_send(self):
        with self.io_lock:
            self._poll_and_send()

    def _poll_and_send(self):
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
    
    def _send(self, address, *values):
        """Send a reply message to PD."""
        msg = OSCMessage(address)
        for v in values:
            msg.append(v)
        self.osc_client.send(msg)

    def handle_command(self, address, tags, args, source):
        """
        Handle OSC commands from PD. Namespaces:
          /io/<verb>   - bridge management (create, poll, report, scan)
          /io/<name>   - control the peripheral called <name>; the first
                         value is the command, the rest are its arguments
          /system/*    - device facts (rssi, id, ip, uptime, rev, patch, info)
        """
        parts = address.strip('/').split('/')

        if parts[0] == 'io':
            self.handle_io(parts[1:], args)

        elif parts[0] == 'system':
            self.handle_system(parts[1] if len(parts) >= 2 else 'rssi')

        # Anything else is a message nobody claimed. Say so: a silently
        # dropped command is indistinguishable from a dead peripheral, and
        # that ambiguity has cost real debugging time.
        else:
            print(f"Unrouted OSC: {address} {list(args)} "
                  f"(peripherals: {list(self.peripherals)})")

    def handle_io(self, parts, args):
        with self.io_lock:
            self._handle_io(parts, args)

    def _handle_io(self, parts, args):
        """Bridge management: /io/create|poll|report|scan."""
        verb = parts[0] if parts else ''

        # /io/create <name> <type> <address>
        if verb == 'create':
            if len(args) < 3:
                print(f"Invalid /io/create arguments: {list(args)}")
                # Missing-name/error-token semantics await wire ratification.
                return
            name = str(args[0])
            if not have_bus():
                self._send("/io/error", name, "no-bus")
                return
            device_type = str(args[1])
            try:
                value = args[2]
                i2c_addr = int(value, 16) if isinstance(value, str) else int(value)
                if not 0x03 <= i2c_addr <= 0x77 or (
                        not isinstance(value, str) and i2c_addr != value):
                    raise ValueError("expected a usable 7-bit I2C address")
            except (TypeError, ValueError, OverflowError) as e:
                print(f"Invalid /io/create address for {name}: {e}")
                # Extending create-failed to argument errors needs ratification.
                return
            if not self.create_peripheral(name, device_type, i2c_addr):
                self._send("/io/error", name, "create-failed")

        # /io/poll <rate>
        elif verb == 'poll':
            try:
                rate = float(args[0])
                if not math.isfinite(rate):
                    raise ValueError("poll rate must be finite")
            except (IndexError, TypeError, ValueError, OverflowError) as e:
                print(f"Invalid /io/poll arguments {list(args)}: {e}")
                return  # Error name/reason await wire ratification.
            self.poll_rate = max(0.1, rate)
            print(f"Poll rate set to {self.poll_rate} Hz")

        # /io/report
        elif verb == 'report':
            print("\nActive peripherals:")
            for name, peripheral in self.peripherals.items():
                print(f"  {name}: {peripheral.__class__.__name__}")

        # /io/scan [bus] -> reply /io/scan <addr> <addr> ... (present, ints)
        # Skips probing live peripherals (reports them from the registry).
        elif verb == 'scan':
            try:
                bus = int(args[0]) if args else 1
                if bus < 0 or (args and not isinstance(args[0], str)
                               and bus != args[0]):
                    raise ValueError("bus must be a nonnegative integer")
            except (TypeError, ValueError, OverflowError) as e:
                print(f"Invalid /io/scan arguments {list(args)}: {e}")
                return
            skip = [p.address for p in self.peripherals.values()
                    if getattr(p, 'address', None)]
            self._send("/io/scan", *scan_bus(bus, skip=skip))

        # /io/<peripheral> <command> [args...] - control a peripheral.
        #
        # Exactly one address segment names the target and everything after
        # it is a value. The alternative -- putting the command in the
        # address as /<name>/<command> -- cannot be produced by a generic
        # sender: bopos~.pd's io path receives a flat list and has no way to
        # know how many leading atoms are address and how many are values.
        # Splitting a fixed number would only work by coincidence.
        #
        # Matched after the verbs above, which is why RESERVED_NAMES exists.
        # len(parts) == 1: a trailing segment means the sender put the
        # command in the address, and dispatching args[0] as the command
        # would silently misread the first value as one.
        elif len(parts) == 1 and verb in self.peripherals and args:
            command = str(args[0])
            try:
                self.peripherals[verb].write_data(command=command,
                                                  args=list(args[1:]))
            except Exception as e:
                print(f"Error writing to {verb}: {e}")

        else:
            print(f"Unknown /io verb: {verb} {list(args)}")

    def handle_system(self, query):
        """Device facts: /system/rssi|id|ip|uptime|rev|patch|info.
        Each replies on its own address; /system/info emits them all."""
        if query in ('rssi', 'info'):
            rssi, quality = read_wireless()
            self._send("/system/rssi", rssi if rssi is not None else 0,
                       quality if quality is not None else 0)
        if query in ('id', 'info'):
            self._send("/system/id", get_hostname())
        if query in ('ip', 'info'):
            self._send("/system/ip", get_ip())
        if query in ('uptime', 'info'):
            self._send("/system/uptime", get_uptime())
        if query in ('rev', 'info'):
            self._send("/system/rev", get_git_rev())
        if query in ('patch', 'info'):
            self._send("/system/patch", get_active_patch())

    def run(self):
        """
        Main loop: poll sensors and send OSC bundle.
        """
        print("\nBopOS I/O Bridge Running")
        print(f"Python listening on port {PYTHON_PORT}")
        print(f"Sending to PD on port {PD_PORT}")
        print(f"Poll rate: {self.poll_rate} Hz")
        print("\nCommands:")
        print("  /io/create <name> <type> <address>")
        print("  /io/poll <rate>   /io/report   /io/scan [bus]")
        print("  /system/rssi|id|ip|uptime|rev|patch|info")
        print("\nPress Ctrl+C to quit\n")
        
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
                # Sleep the REMAINDER of the period, not a flat interval on top
                # of the read. A 4-channel ADS1115 read is ~13 ms, so sleeping
                # 1/rate as well made poll_rate 10 mean 7.1 Hz -- and the error
                # grew silently with every peripheral added. Clamped at zero:
                # if a read outruns the period the loop free-runs, which cannot
                # spin, because the I2C reads are themselves the rate limit.
                started = time.time()
                self.poll_and_send()
                time.sleep(max(0.0, (1.0 / self.poll_rate) - (time.time() - started)))
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.running = False
            server.close()
            
            # Cleanup all peripherals
            server_thread.join()
            with self.io_lock:
                for name, peripheral in self.peripherals.items():
                    try:
                        peripheral.cleanup()
                    except Exception as e:
                        print(f"Error cleaning {name}: {e}")
                self.peripherals.clear()


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
