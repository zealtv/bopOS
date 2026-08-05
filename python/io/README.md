# BopOS I2C to OSC Bridge

Simple Python bridge for interfacing I2C sensors with Pure Data via OSC.

## Architecture

**Super Simple Design:**
- Python polls all sensors at a defined rate (default 10 Hz)
- Sends a single OSC bundle containing data from all peripherals
- PD sends OSC commands to Python to control peripherals
- Peripherals can be created dynamically via OSC


### From Pure Data, create peripherals dynamically

Message boxes into `[s to-bopos-io]`:
```
[create adc1 ads1015 0x48(  ← Create ADC at address 0x48
[create tilt lis3dh 0x19(   ← Create tilt sensor
[create touch mpr121 0x5A(  ← Create touch sensor
```

### Receive data bundle in PD

All sensor data arrives in a single OSC bundle at the poll rate:
```
/adc1 3.3 1.2 0.0 0.5
/tilt 0.1 -0.5 0.9
/touch 512 234 789 ... (12 values)
```

### Control poll rate
```
[poll 20(  ← Poll at 20 Hz
[poll 5(   ← Poll at 5 Hz
```

### Send commands to peripherals
```
[touch threshold 15 8(  ← Set touch thresholds
```

## File Structure

```
main.py                    # Main OSC bridge 
io_ads1015.py          # ADS1015 ADC module
io_lis3dh.py         # LIS3DH accelerometer
io_mpr121.py        # MPR121 touch sensor
io_template.py     # Template for new peripherals
```

## How It Works

### Main Loop (main.py)
```python
while running:
    poll_and_send()  # Read all peripherals, send OSC bundle
    sleep(1.0 / poll_rate)
```

### Peripheral Interface
Every peripheral has these simple methods:

```python
class MyPeripheral:
    def setup(self):
        # Initialize hardware
        
    def read_data(self):
        # Return list, dict, or value
        return [value1, value2, value3]
    
    def write_data(self, **kwargs):
        # Handle commands from PD
        command = kwargs.get('command')
        args = kwargs.get('args')
        # Shutdown cleanup
```

## OSC Commands

Two namespaces by first path segment: `/io/*` = the bridge (management verbs
and peripherals alike), `/system/*` = device facts.

**A peripheral is addressed as `/io/<name>`, with the command as the first
value** — `/io/lights fill 0 255 0`, not `/io/lights/fill 0 255 0`. Exactly
one segment is address; everything after it is a value. Putting the command
in the address cannot work for a generic sender: `bopos~.pd`'s io path
receives a flat list of atoms and has no way to know how many leading ones
are address and how many are values, and splitting a fixed number would only
be right by coincidence.

Because peripherals share the namespace with the management verbs, the names
`create`, `poll`, `report` and `scan` are reserved and rejected at creation.

### Bridge management (`/io/*`)
```
/io/create <name> <type> <address>   Create a peripheral
/io/poll <rate>                      Set poll rate in Hz
/io/report                           Log active peripherals
/io/scan [bus]                       Reply /io/scan <addr>... (present I2C addrs)
```

### Device facts (`/system/*`) — request/reply, manually polled
```
/system/rssi      -> /system/rssi <dbm> <quality>   (quality 0 = no link)
/system/id        -> /system/id <hostname>
/system/ip        -> /system/ip <ip>
/system/uptime    -> /system/uptime <seconds>
/system/rev       -> /system/rev <git-sha>
/system/patch     -> /system/patch <active-patch>
/system/info      -> emits all of the above (one message each)
```

### Peripheral commands
```
/io/<peripheral> <command> [args...]   Send command to peripheral
```

From a patch, `[s to-bopos-io]` takes the same thing as a flat message —
`lights fill 0 255 0` — and `bopos~.pd` turns the first atom into the
address segment.

## Available Peripheral Types

| Type | Module | Class | Description |
|------|--------|-------|-------------|
| `ads1015` | io_ads1015 | IO_ADS1015 | 4-channel 12-bit ADC |
| `ads1115` | io_ads1115 | IO_ADS1115 | 4-channel 16-bit ADC |
| `lis3dh` | io_lis3dh | IO_LIS3DH | 3-axis accelerometer |
| `mpr121` | io_mpr121 | IO_MPR121 | 12-channel capacitive touch |
| `rgb` | io_rgb | IO_RGB | PiicoDev 3x RGB LED (output) |
| `ssd1306` | io_ssd1306 | IO_SSD1306 | 128x64 OLED display (output) |
| `switch` | io_switch | IO_Switch | PiicoDev momentary button |

### `rgb` commands

Created with `[create lights rgb 0x08(`. Three LEDs, indexed 0-2. Shown as
patch messages; on the wire each is `/io/lights` with the rest as values.

```
[lights pixel <n> <r> <g> <b>(     One LED, 0-255 per channel
[lights fill <r> <g> <b>(          All three the same colour
[lights all <r g b r g b r g b>(   All three in one I2C write (no tearing)
[lights hsv <n> <hue> [sat] [val>( HSV 0-1; n = -1 fills all three
[lights clear(                     Blank
[lights bright <0-255>(            Global brightness
[lights power <0|1>(               Onboard green power LED
```

## Creating New Peripherals

1. Copy `io_template.py` to `io_yourdevice.py`
2. Fill in `setup()`, `read_data()`, and `write_data()`
3. Add to `PERIPHERAL_TYPES` in `main.py`:
```python
PERIPHERAL_TYPES = {
    'ads1015': ('io_ads1015', 'IO_ADS1015'),
    'yourdevice': ('io_yourdevice', 'IO_YOURDEVICE'),
}
```
4. Create from PD: `[create dev1 yourdevice 0x48(` to `[s to-bopos-io]`


## Peripheral lifecycle (design decision)

Peripherals are **created and managed over OSC by the active patch** (`/io/create …`),
**not** from a device-level config file. The bridge starts with **no peripherals** — the
patch declares the ones it needs (the auto-create lines in `main()` stay commented as
examples only).

This is deliberate:

- **Different patches may handle hardware differently** — so it's fine, and expected, for a
  patch to (re)instantiate peripherals its own way on load. The hardware complement is a
  property of the *patch*, not baked into the device.
- **Keeps the device fully remote-controllable** — anything reachable over OSC can create,
  reconfigure, or query peripherals at runtime; nothing is locked in at boot.

A patch typically issues its `/io/create` calls on `loadbang`. Peripherals persist until
replaced or until the bridge restarts (for example, on a device reboot or framework
update). An engine-only patch switch leaves the bridge running.


## Dependencies

Dependencies are listed in `requirements.txt` and should be updated automatically when update.sh is run.

## Design Principles

✅ **Simple** - One polling loop, one OSC bundle
✅ **Readable** - Minimal code, clear structure  
✅ **Dynamic** - Create peripherals at runtime
✅ **Consistent** - All peripherals use same interface
✅ **Modular** - Easy to add new devices
