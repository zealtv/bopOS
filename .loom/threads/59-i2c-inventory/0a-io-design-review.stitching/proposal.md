# IO design: proposal for ratification

**Status:** proposed 2026-10-04, from Bob's direction in session (`rulings.md`).
Nothing here is built, and the contract text in §8 is not written into the
contract.

One design for the I2C/peripheral layer: transport, streaming, ownership,
workflow, simulation and scope. Plus Performance mode, which the streaming
decision needs but which reaches beyond IO.

## 1. Transport

**Decision.** `bopos.py` is the device's only process facing the network, for
IO as for everything else.

- **Control** (scan, module status, operator writes, errors) uses the existing
  exact-device admin envelope: `/all/os/to <uid> io-… <json>` →
  `/os/io-… <uid> …`. Low rate, request/reply.
- **Values** use a **dedicated stream port**, device → host, unicast to the
  dashboard that opened the stream. Streams never share a port with control or
  heartbeats.
- **Bridge ↔ `bopos.py`, on the device.** A new localhost port, **7771**:
  `io/main.py` sends its control replies (`/io/error`, scan results, the
  registry) there as well as to the engine, and while a stream is open a copy
  of each value bundle. `bopos.py` already reaches the bridge's 8880 to send
  commands. The bridge stays localhost-only.
- The bridge's reply model: every reply goes to the engine (6662, unchanged) and
  to `bopos.py` (7771). Value bundles go to 7771 only while `bopos.py` has
  told the bridge a stream is open.

**Errors** (folds in `67-repair-pass/3-io-bridge-hardening` wire-proposal,
option 2). `/io/error <name> <reason>` with the reasons documented:
`no-bus`, `create-failed` (already shipped), `invalid-arguments`,
`unknown-command`, `write-failed`. Errors not about one module use the
reserved name **`bridge`**; poll and scan argument errors use `bridge`, not
`poll`/`scan`. Errors relay to the dashboard as `/os/io-error <uid> <name>
<reason>` and show on the Device tab and in the module's panel, instead of only
in `io.log`.

**Rejected.**
- *The bridge sends to several destinations itself*: it would put network
  code, lease handling and Performance enforcement in a second process.
- *`bopos.py` scans the bus itself*: it can't skip live peripherals, and two
  processes touching one chip is the contention bug the registry exists to
  prevent. The scan stays in the bridge.
- *Streams on the admin port*: Bob ruled them onto their own port.

## 2. Streaming and Performance mode

**Streaming.** For development, §6's "no streamed telemetry" is relaxed. Bob:
*"strict adherence to it has made debugging sensors and development difficult
if not impossible."*

- **One device at a time, all of its modules.** The dashboard opens a stream on
  a device; that device sends every module's values.
- **Rate:** at most the bridge's poll rate (default 10 Hz). A bundle for a
  handful of modules is a few hundred bytes.
- **Lease:** a stream lasts 10 s unless renewed. The dashboard renews while a
  panel or the editor feed is open, so closing the tab, leaving Patch Edit or a
  dashboard crash ends it within seconds.
- **Destination:** the dashboard. It shows values in module panels, and in
  Patch Edit it can forward them to the editor's audition engine on its 6662,
  the same door `tools/iosim.py` uses.

**Performance mode.** One global toggle, **Performance**, separate from Live /
Simulation / Patch Edit (those say where audio runs; this says what kind of
session it is). An explicit switch in the header, not inferred from show
playback.

- **Locked in Performance:**
  - sensor streaming and stream-to-editor;
  - logging to the SD card (logs go to RAM and the dashboard only), to protect
    the card from a hard shutdown;
  - probes and Monitor sends;
  - operator writes to modules;
  - Wi-Fi changes;
  - patch changes: pushes, Set Live, New Version, manifest saves and
    entering Patch Edit.
- **Devices enforce it**, and it **fails safe**. A device boots in
  Performance and stays there until a dashboard tells it otherwise. The
  dashboard repeats the mode every 10 s; a device that hears nothing for 60 s
  goes back to Performance. Development therefore needs a dashboard present,
  and an unattended fleet can't be left streaming or writing logs to SD.
- The dashboard starts in development, so Performance is chosen deliberately
  (Bob). On a fleet already in Performance (e.g. the dashboard restarted
  mid-show), the dashboard shows what the devices report before you change it.

**Rejected.**
- *Tie restrictions to show playback*: you play shows in rehearsal and want
  debugging then.
- *Dashboard-only enforcement*: a bug or a stale tab could put sensor traffic
  on a show network.
- *A fourth execution mode*: Performance is independent of where audio runs.

## 3. Ownership

**Decision.** Modules are declared in the **manifest**, fleet-wide, and
satisfied per device on the asset-slot pattern:

```json
"io_modules": [
  {"name": "adc",  "type": "ads1115", "address": "0x48"},
  {"name": "tilt", "type": "lis3dh",  "address": "0x19", "optional": true}
]
```

- When the engine starts with a patch, `bopos.py` tells the bridge to create
  each declared module. Each device reports, per module: present and running,
  missing (an optional one is fine; a required one is flagged), or errored.
- The patch hooks into modules by name, as it does today (`/adc …` values;
  commands via `to-bopos-io`).
- **Writes: last write wins.** There's only ever one engine per device (Bob),
  so no writer field is needed. Operator writes from module panels are
  development-only.
- **Transition:** patches that create on `loadbang` keep working. A create
  matching a declared module (same name, type and address) is a no-op that
  succeeds; one that conflicts is `create-failed`. Removing the patch-side
  creates is a Pd edit for Bob (`64`), not urgent.

**Rejected.**
- *Patch-owned (today)*: the dashboard can't know what should be there, so
  it can't say what's missing.
- *Operator-owned*: modules are part of the piece, so they belong with the
  patch.
- *Per-instance ownership for split elements*: there's one engine per device.

## 4. Workflow

From a chip arriving to patching against it:

1. **Wire it, then scan.** On the Device tab, scan the bus. Addresses are
   listed hex and sorted, with hints (`0x48 · ADS1x15?`), never claims. "No
   bus", "bus but empty" and "not scanned yet" are three visible states;
   kernel-claimed addresses (`UU`, e.g. the DAC) are marked as such.
2. **Declare it.** Add the module to the patch manifest (the Patches tab's
   manifest editor gains an IO modules section). Push the patch.
3. **Know it worked.** The Device tab lists the manifest's modules for that
   device: running, missing, or errored with the bridge's reason
   (`create-failed`, `write-failed`, …). Re-init on that row.
4. **See values and drive outputs.** Tick **Show in Monitor** beside a module.
   Its live panel appears in the Monitor dock's **Modules** tab (opening a
   stream on that device). Inputs show in units and exactly as the patch
   receives them; outputs are controls (OLED text, touch thresholds). The
   dock can pop out to its own window to sit beside Pd.
5. **Patch against it.** In Patch Edit, pick a device as the editor's input
   source. Its stream feeds the audition engine, and the patch can't tell it
   from the real thing.

This replaces `ads.py` and `watch.py`. `4-sensor-test-window`'s summary (rest,
min, max, swing, edges over a window) becomes a panel feature only if the live
view turns out not to answer "am I getting presses?" (see §7).

**Where things live.** Interactive panels live **only in the Monitor dock**:
it stays visible on every tab, including Patch Edit, and pops out. The Device
tab is the inventory (scan, declared modules, status, errors, a snapshot of
values) with the "Show in Monitor" checkbox. One panel implementation, one
place.

## 5. Simulation and module panels

**Each driver describes itself.** Each module type (`ads1115`, `lis3dh`,
`mpr121`, the OLED, …) declares its **inputs** (channels, units, ranges) and
**outputs** (commands and their arguments) in its driver in `python/io/`. The
dashboard reads the same descriptions from the host's copy of the drivers, so
it can draw panels with no device present. A new chip type means a driver
plus its description, with no UI code.

**One panel component, arrows reversed:**

| | inputs | outputs |
|---|---|---|
| **Live** (a device) | what the device reports | controls that write to the module |
| **Simulated** (no hardware) | sliders and pads you drive | what the patch wrote (e.g. OLED preview) |

- The panel header always names its source: *Ciro Toast · live* or
  *simulated*.
- Simulated inputs go to the editor's audition engine on its 6662, streaming
  continuously at poll rate, with presses going to the opposite rail from each
  channel's rest (`iosim.py`'s two fidelity rules). The patch can't tell
  simulated from live.
- Simulated values reset each session (Bob).
- Modules tab in the Monitor dock, with a pop-out to an ordinary browser window
  (cross-platform; Bob ruled out Chrome-only Picture-in-Picture).

## 6. Out of scope

- Raw register reads and writes (drivers only).
- Buses other than I2C, for now (§11 already allows SPI/GPIO/serial later
  through the same registry).
- Recording or replaying streams.
- Streaming more than one device at once.
- **Future, recorded:**
  - **Cross-device / server-side sensor use.** Bob foresees the server making
    decisions from aggregate or specific readings. That would be a separate,
    deliberate show-time sensor feed (low rate, chosen modules, allowed in
    Performance), not the development stream relaxed. The dedicated stream
    port doesn't prevent it.
  - **Fake input into a real device's engine.** Deferred: if a real sensor is
    present too, the two fight, and the bridge would need an override mode. No
    current need.

## 7. Sequencing for `59`

Order: `1` → `2`, `3` → `perf` → `4` → `5` → `6`.

| # | stitch | was | needs |
|---|---|---|---|
| `1` | **io-control-path**: bridge replies to 7771, the `io-*` admin verbs, `/os/io-error`, error vocabulary, the `io` object in `/os/report`, simfleet | `1-scan-transport` | `0a` |
| `2` | **device-tab-inventory**: scan states, declared modules with status and errors, Re-init, the "Show in Monitor" checkbox (wired up in `5`) | same, wider | `1` |
| `3` | **manifest-modules**: `io_modules` in the manifest and its editor, create at engine start, the no-op transition, driver input/output descriptions, plus the two defects from `3-peripheral-lifecycle` | `3-peripheral-lifecycle` | `1` |
| `perf` | **Performance mode**, its own thread (it reaches logging, Wi-Fi, patches): header toggle, `/all/os/performance`, fail-safe on the device, the lock list, RAM-only logging | new | — |
| `4` | **stream-port**: leases, the stream port, the dashboard receiver, simfleet streams; refused in Performance | new (absorbs `4-sensor-test-window`) | `1`, `perf` |
| `5` | **module-panels**: the Modules tab in the Monitor dock, live panels (watch inputs, drive outputs), pop-out | new | `2`, `3`, `4` |
| `6` | **editor-input**: in Patch Edit, pick a device stream or a simulated panel as the editor's input; simulated panels | `5-simulated-input` + `6-live-sensor-in-patch-edit` | `5` |

`4-sensor-test-window` is retired into `5`; its windowed summary is a panel
feature only if live values prove not enough.

## 8. Contract amendment (proposed v1.21, additive; not written)

**§4 Ports**: two rows:

| Port | Listener | Sender | Scope |
|---|---|---|---|
| 5551 | dashboard | bopos.py | LAN unicast, device → the dashboard that opened a stream: IO value streams (development only) |
| 7771 | bopos.py | io/main.py | localhost: IO control replies; value bundles while a stream is open |

The §4 sentence "the six ports stay exactly as deployed" becomes "eight ports;
5551 and 7771 added in v1.21".

**§6**: new subsections:

```
/all/os/performance <0|1>            dash → fleet, repeated every 10 s
    device boots in Performance (1); with no message for 60 s it returns to 1.
    In Performance the device refuses: io-stream, io-write, probe, wifi-config,
    and patch distribution/switch requests; it logs to RAM only.
/all/os/to <uid> io-scan              → /os/io-scan <uid> <json>
/all/os/to <uid> io-modules           → /os/io-modules <uid> <json>
/all/os/to <uid> io-write <json>      → /os/io-write <uid> <ok|err> <json>
/all/os/to <uid> io-stream <0|1>      → /os/io-stream <uid> <ok|err> <json>
    1 opens or renews a 10 s lease; values flow to the requester on 5551 as
    /io/stream <uid> followed by the bridge's bundle; 0 closes. One stream per
    device; refused in Performance.
/os/io-error <uid> <name> <reason>    unsolicited, relayed from the bridge
```

The paragraph saying there is no streamed telemetry gains: "except IO value
streams (§11): development-only, leased, one device, refused in
Performance".

**§8 Manifest**: `io_modules`, as in §3 above (name, type, address,
optional). Satisfied per device; the device reports presence.

**§11 IO plane**:
- Modules are manifest-declared; `bopos.py` creates them at engine start; a
  matching patch-side create is a no-op.
- The reply model: replies go to 6662 and 7771.
- The error vocabulary, and the reserved name `bridge`.
- "No subscription stream" becomes: demand-driven `/report` + `/os/probe`
  stays for patch-retained values; the development stream is the one
  sanctioned stream.
- `/os/report` gains `io`: `{bus, scanned, modules: {name: {type, address,
  state, error}}}`.

**§15**: a v1.21 row.

## Questions for Bob (for ratification)

1. Ports **5551** and **7771**: any clash with your setups, or a preference?
2. **Fail-safe:** devices boot in Performance and fall back to it after 60 s
   without a dashboard. OK? It means development needs the dashboard
   running; a box on the bench with no dashboard behaves like a show box (no
   SD logging, no streams).
3. **Patch Edit locked in Performance**: confirmed as you said. Note it also
   covers opening the editor to *look* at a patch mid-show.
4. Retiring `4-sensor-test-window` into the panels, OK?
