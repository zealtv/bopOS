# BopOS I2C to OSC Bridge

Simple Python bridge for interfacing I2C sensors with Pure Data via OSC.

## Architecture

**Super Simple Design:**
- Python polls all sensors at a defined rate (default 10 Hz)
- Sends a single OSC bundle containing data from all peripherals
- PD sends OSC commands to Python to control peripherals
- Peripherals can be created dynamically via OSC


### From Pure Data, create peripherals dynamically

```
[io/create adc1 ads1015 0x48(  ← Create ADC at address 0x48
[io/create tilt lis3dh 0x19(   ← Create tilt sensor
[io/create touch mpr121 0x5A(  ← Create touch sensor
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
[touch/threshold 15 8(  ← Set touch thresholds
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

### System Commands
```
/io/create <name> <type> <address>   Create a peripheral
/io/list                             List active peripherals
/poll <rate>                         Set poll rate in Hz
```

### Peripheral Commands
```
/<peripheral>/<command> [args...]    Send command to peripheral
```

## Available Peripheral Types

| Type | Module | Class | Description |
|------|--------|-------|-------------|
| `ads1015` | peripheral_adc | IO_ADS1015 | 4-channel 12-bit ADC |
| `lis3dh` | peripheral_tilt | IO_LIS3DH | 3-axis accelerometer |
| `mpr121` | peripheral_touch | IO_MPR121 | 12-channel capacitive touch |

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
4. Create from PD: `[io/create dev1 yourdevice 0x48(`


## Dependencies

Dependencies are listed in `requirements.txt` and should be updated automatically when update.sh is run.

## Design Principles

✅ **Simple** - One polling loop, one OSC bundle
✅ **Readable** - Minimal code, clear structure  
✅ **Dynamic** - Create peripherals at runtime
✅ **Consistent** - All peripherals use same interface
✅ **Modular** - Easy to add new devices