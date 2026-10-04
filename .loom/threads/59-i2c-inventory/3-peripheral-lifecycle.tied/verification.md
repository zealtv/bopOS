# 59/3 verification

Software checks (2026-10-04):

- `./tools/run-tests.sh fast`: PASS, 497 tests.
- `./tools/run-tests.sh browser`: PASS, all 30 journeys, including
  `tests/verify_io_control.py`, `tests/verify_log_destination.py`,
  `tests/verify_manifest_param_visibility.py` and Performance mode.
- `node --check dashboard/static/js/dashboard.js` and `git diff --check`: PASS.
- `tests/test_manifest.py`: IO schema validation, malformed types, duplicate
  names, reserved names, address normalization and atomic round-trip.
- `tests/test_engine_ready_replay.py`: engine-ready/config creates use the
  existing grammar; transport failure cannot kill config and readiness retries.
- `tests/test_io_bridge.py`: matching declared create is a no-op; wrong
  type/address preserves the live chip; missing required/optional addresses;
  present chip setup failure; retirement and legacy-name ownership; all driver
  descriptions readable without importing hardware. Mocked vendor diagnostics,
  TypeError, NaN and None give one bus-failure line; reads recover; another
  thread's output is preserved.
- `tests/test_io_control.py`: registry health survives rejected creates;
  simulator resolves the same fleet declaration separately per device.
- `tests/verify_io_control.py`: real localhost OSC bridge/node sockets relay
  wrong-type/wrong-address create failures to unsolicited LAN errors. Chip
  operations are faked; this is transport evidence, not hardware evidence.
- `tests/verify_manifest_param_visibility.py`: add/save/reload/invalid edit/
  removal of IO modules alongside params and events. Screenshot:
  `manifest-io.png`.

Driver audit: all seven supported wrappers are polled through the common
read-failure boundary. ADS wrappers return volts, MPR121 filtered counts,
switch three flags, RGB/OLED no inputs. LIS3DH uses the vendor `angle`
property, not acceleration in g; the wrapper docstring now agrees. The
[vendor source](https://github.com/CoreElectronics/CE-PiicoDev-Accelerometer-LIS3DH-MicroPython-Module/blob/main/PiicoDev_LIS3DH.py)
confirms degree conversion and the printed-error/NaN/secondary-TypeError path.

## Pending hardware checks

- Pi boot/restart/switch with real declared chips, including a patch with its
  old matching loadbang creates; confirm there is no second setup or reset.
- Per-device required versus optional absence and no usable bus; confirm probe
  compatibility, kernel-claimed addresses and driver setup classification.
- Wrong driver at a physically populated address and wrong physical address:
  confirm the driver detects the fault and `/os/io-error` reaches the dashboard.
- Unplug/replug LIS3DH: confirm exactly one peripheral/address/bus-failure line
  per failed poll, no secondary TypeError, no invalid values, and recovery.
  Repeat read failure/recovery for ADC, MPR121 and switch.
- Confirm nominal input ranges and actual output actions on all seven modules;
  ADC descriptions use the existing wrappers' 0–3.3 V convention. No range,
  chip action, bus timing or physical recovery was measured here.

No physical hardware result is claimed.
