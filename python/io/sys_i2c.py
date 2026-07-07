# sys_i2c.py
"""
I2C bus enumeration for /io/scan -- report what hardware is attached without
SSH. Discovery, not assumption: the bridge doesn't know device types from
addresses, it just reports which addresses respond.

Mirrors i2cdetect's probe strategy (read for the 0x30-0x37 / 0x50-0x5F
ranges, quick-write elsewhere). EBUSY means a kernel driver owns the address
(i2cdetect's "UU", e.g. a bound DAC) -- still reported as present.
"""

import os

try:
    from smbus2 import SMBus, i2c_msg
    HAVE_SMBUS = True
except ImportError:
    HAVE_SMBUS = False


def have_bus(bus=1):
    return os.path.exists("/dev/i2c-{}".format(bus)) or bool(os.environ.get("BLINKA_MCP2221"))


def scan_bus(bus=1, skip=()):
    """
    Probe addresses 0x03-0x77 on `bus`; return a sorted list of present
    addresses (ints). `skip` addresses are reported present WITHOUT probing
    -- pass the addresses of live peripherals so we don't poke a chip the
    poll loop is already reading.
    """
    if not HAVE_SMBUS:
        return []
    try:
        b = SMBus(bus)
    except OSError:
        return []
    skip = set(skip)
    found = []
    with b:
        for addr in range(0x03, 0x78):
            if addr in skip:
                found.append(addr)
                continue
            try:
                if 0x30 <= addr <= 0x37 or 0x50 <= addr <= 0x5F:
                    b.read_byte(addr)                       # read-probe
                else:
                    b.i2c_rdwr(i2c_msg.write(addr, []))     # quick-write probe
                found.append(addr)
            except OSError as e:
                if e.errno == 16:                           # EBUSY = claimed (UU)
                    found.append(addr)
    return sorted(found)
