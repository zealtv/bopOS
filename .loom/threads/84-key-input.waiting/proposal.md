# 84-key-input: proposal for Bob, 2026-11-04

Bob ruled the key wire in chat (see `instructions.md`). The agent shipped that,
plus the mouse forms Bob asked for ("XY positions and clicks would all be
good"), with details the agent chose and Bob has not yet seen. This lists them.

## 1. What shipped (uncommitted to the contract)

`python/io/sys_input.py`, started by the bridge as a daemon thread, sends on
localhost 6662 as each event happens (not on the poll loop):

```
/io/key <name:s> <1|0:i>          key down/up; autorepeat ignored
/io/mouse <button:s> <1|0:i>      left right middle side extra touch
/io/mouse xy <x:f> <y:f>          pointer, 0-1 each, origin top-left
/io/mouse move <dx:i> <dy:i>      raw relative counts in one report
/io/mouse wheel <steps:i>         hwheel for horizontal
```

- Devices: every `/dev/input/event*` on USB or Bluetooth that reports keys,
  relative or absolute axes. HDMI-CEC and GPIO keys are skipped. Rescanned
  every 2 s; each one grabbed so tty1 stops seeing it.
- Mouse buttons go on `/io/mouse` even though the kernel reports them as keys.
  A Makey Makey's clicks arrive as `/io/mouse left 1`.
- Relative mice share one virtual pointer: starts at 0.5 0.5, 2000 counts
  span an axis (the agent's estimate, not measured). Absolute devices
  (touchscreens, tablets) map their axis range to 0–1.
- `xy` and `move` go out once per kernel report, unthrottled. A 1000 Hz
  gaming mouse would mean ~1000 messages/s into the engine; a Makey Makey's
  rate hasn't been measured.
- Unplugging sends a release for anything held, so no note sticks.
- Values reach the engine only. The leased dev stream (§6) and Device tab
  don't see them; they're not modules.
- `key` and `mouse` join the reserved peripheral names.
- `provision.sh` adds `pi` to `input`. Existing nodes aren't reprovisioned;
  Raspberry Pi OS normally gives its first user `input` already (not checked
  on the rig). If not, the bridge log says `not readable`.

## 2. Key names (Bob to confirm)

Kernel names, lowercased, `KEY_` stripped: `space`, `w`, `up`, `enter`, `f1`,
`kp0`. Number-row keys keep the prefix, `key_1`…`key_0`: a bare `1` reaches Pd
as a symbol, which `[route 1]` won't match. Unknown codes arrive as
`code_<n>`. Real Pd 0.55 `-nogui` routed `space`, `w`, `key_1`, `left` and `xy`
through `[route io] → [route key mouse] → [route …]` on 2026-11-04 (laptop,
`iosim.py` as sender, no device).

## 3. Contract amendment (draft, v1.24, for ratification)

§11 now says the engine owns "audio, MIDI, HID, display". Proposed:

> - **Framework owns keyboard and pointer input** (v1.24). Pd runs headless, so
>   engines cannot hear USB/Bluetooth keyboards and mice; the bridge reads
>   them always, outside the manifest, and sends `/io/key` and `/io/mouse` (the
>   grammar above) to the engine on localhost 6662 as events, not poll values.
>   `key` and `mouse` are reserved module names.
> - **Engine owns its native media IO** — audio, MIDI, display.

§15 row: *1.24 · Keyboard and pointer input on the IO plane (§11): always-on
`/io/key`, `/io/mouse` to the engine; `key`, `mouse` reserved; HID moves from
engine to framework. Localhost only; no LAN wire, port or manifest change.*

## 4. Simulator (Bob raised it mid-session, 2026-11-04)

Shipped now: `tools/iosim.py --key space`, `--click left`, `--xy X,Y`,
`--move DX,DY`, `--wheel N`. Each sends the bridge's exact bytes once (checked
against a socket), on the laptop or over SSH on a node, beside the running
bridge — the same way iosim already fakes I2C.

Not built, Bob's call (user-facing):

- **A. Patch Edit panel.** A "Keys & mouse" simulated panel in the Monitor
  dock's Modules tab, feeding the audition engine's 6662 like the simulated
  I2C panels: key pads, buttons, an XY pad. No new wire. This is the I2C
  pattern exactly.
- **B. Into a real device's engine from the dashboard.** Needs a new
  exact-device verb through `bopos.py` to the bridge. In 59/0a (2026-10-04)
  Bob deferred "fake input into a real device's engine"; this would reopen
  that, and it would have to be locked in Performance.

Recommendation: A when it's wanted; iosim covers device-side checks until then.

## 5. Hardware check owed (Bob's list)

A Makey Makey on a rig node (Finn Jet or Ciro Toast): keys and clicks reach
the patch, the console stops echoing, unplug/replug recovers, and check the
`input` group on an existing install.
