#!/usr/bin/env python3
"""
MPR121 Debug Monitor
Live terminal display of electrode 0 capacitance values from MPR121 sensors.

Usage:
    python io_mpr121_debug.py                  # use default addresses
    python io_mpr121_debug.py 0x5A             # single sensor
    python io_mpr121_debug.py 0x5A 0x5B        # two sensors (default)
    python io_mpr121_debug.py 0x5A 0x5B 0x5C   # three sensors

Works on Pi (native I2C) and laptop (set BLINKA_MCP2221=1 for MCP2221A USB adapter).
"""

import sys
import time
from io_mpr121 import IO_MPR121

# --- Default I2C addresses (edit these) ---
DEFAULT_ADDRESSES = [0x5A, 0x5B]

BAR_WIDTH = 30
POLL_HZ = 10


def monitor(addresses=None):
    """Run the live MPR121 monitor."""
    if addresses is None:
        addresses = DEFAULT_ADDRESSES

    # Create and setup sensors
    sensors = []
    for i, addr in enumerate(addresses):
        s = IO_MPR121(address=addr)
        s.name = f"touch{i+1}"
        try:
            s.setup()
            sensors.append(s)
        except Exception as e:
            print(f"  Could not init touch{i+1} at 0x{addr:02X}: {e}")

    if not sensors:
        print("No MPR121 sensors found. Check wiring and addresses.")
        sys.exit(1)

    print(f"\n  MPR121 Monitor — {len(sensors)} sensor(s) (Ctrl+C to quit)\n")

    # Print blank lines to reserve space for in-place updates
    for _ in sensors:
        print()

    try:
        while True:
            # Move cursor up to overwrite
            sys.stdout.write(f"\033[{len(sensors)}A")

            for s in sensors:
                try:
                    val = s.read_data()[0]  # electrode 0 only
                except Exception:
                    val = 0
                filled = int(val / 1023 * BAR_WIDTH)
                bar = "#" * filled + "." * (BAR_WIDTH - filled)
                line = f"  {s.name} (0x{s.address:02X}) e0  [{bar}]  {val:>4}"
                sys.stdout.write(f"\r{line}\n")

            sys.stdout.flush()
            time.sleep(1.0 / POLL_HZ)

    except KeyboardInterrupt:
        print("\n")


if __name__ == "__main__":
    # Parse addresses from CLI args, or use defaults
    if len(sys.argv) > 1:
        addrs = [int(a, 16) for a in sys.argv[1:]]
    else:
        addrs = None
    monitor(addrs)
