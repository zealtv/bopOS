# Outside OSC input

Send outside apps (qtable, Max, Ableton, TouchOSC) to **UDP 5552 on the
dashboard machine**. Any source may send. Messages follow the active target:
Live, Simulation or Patch Edit. The dashboard owns the clock and stamps events
before fan-out, so the sender supplies only fields.

The normative rules are [OSC-CONTRACT.md §4.3](OSC-CONTRACT.md#43-outside-app-input);
[PORTS.md](PORTS.md) lists all transport ports. Tests can override the input
with `--input-port` (default 5552).

| Address | Arguments | Effect |
|---|---|---|
| `/<target>/<identity>` | declared event fields or parameter arguments | short form, when unambiguous |
| `/<target>/e/<identity>` | declared event fields | event, stamped with now + event lead |
| `/<target>/p/<identity>` | parameter arguments | parameter, including fades, loop and lfo grammar |
| `/pt`, `/point`, `/pt/clear` | point arguments from §4.1 | unchanged point messages |
| `/bop/master` | `<0..1> [duration]` | immediate master or linear fade |
| `/bop/mute` | `<0|1>` | execution MUTE ALL |
| `/bop/lead` | `<whole ms: 0..10000>` | persistent event lead |

A target is `all`, a seat number (for example `12`), a group selector (`g3`),
or its group name (`spot1`). Group names resolve to selectors before sending.
Identities are slash-separated paths from the active patch's `bopos.patch.json`.
Only declared messages are accepted. Live and Simulation use the fleet patch;
Patch Edit uses the edited patch.

Use explicit `/e/` or `/p/` if an identity occurs in both planes, or starts
with `os`, `io`, `sync`, `e` or `p`. For example, a declared event with identity "os/play"
is addressed as `/all/e/os/play`.

Events accept up to 16 declared float/int/toggle/enum/text fields, in order.
Numbers coerce to their declared OSC type; integer kinds require whole numbers.
Out-of-range finite numbers clamp to the declared range. Omitted trailing
optional fields take their defaults; required omissions, extra fields, invalid
types or invalid text are rejected. Text is 1–255 printable ASCII bytes without
whitespace; integers have magnitude at most 2^24. Do not include a time or the
`"0"` sentinel on this input. Lead zero makes the dashboard send fire-on-arrival;
otherwise it stamps a shared deadline. Sender bundle timetags are ignored.

Parameters retain their argument grammar, including node-side automation.
Their values and automation are recorded for dashboard UI and catch-up.
Point frames pass through; the dashboard pauses its own motion and catch-up
frames until outside points have been silent for two seconds.

Master duration accepts milliseconds as a number or a duration such as `250ms`,
`10s`, `1.5m`. The dashboard sends steps at about 25 Hz and the UI follows.
Any new master value cancels a fade. The destination is saved at fade start.
Mute follows execution state; lead persists in the project.

Examples using `oscsend` (replace `192.168.1.10` with the dashboard IP, and
identities/fields with declarations in your patch):

```sh
# Declared event hit with one float field; dashboard supplies the time.
oscsend 192.168.1.10 5552 /all/e/hit f 0.8
# Same event for a named group, using the short form.
oscsend 192.168.1.10 5552 /spot1/hit f 0.8
# Typed fields: text, float, toggle. No timestamp.
oscsend 192.168.1.10 5552 /all/e/trig/play sfi samples/spot1 0.75 1
# Declared parameter automation.
oscsend 192.168.1.10 5552 /12/p/gain fs 0.5 2s
oscsend 192.168.1.10 5552 /bop/master fs 0.25 3s
oscsend 192.168.1.10 5552 /bop/mute i 1
oscsend 192.168.1.10 5552 /bop/lead i 500
```

There are no OSC error replies. Recent rejections and clamps are kept in an
in-memory ring of 50 entries, available in dashboard state (`osc_input.recent`),
with time, sender, address and reason. Restart clears it.

Device administration remains on node port 6660, as specified in
[the contract](OSC-CONTRACT.md). For example,
`/all/os/to <uid> enabled <0|1>` sets one physical device's output permission;
its receipt is `/os/enabled <uid> <device-enabled> <output-enabled>` on 5550. The input intentionally accepts only the
commands above. Low-level device-wire events on 6660 still require the exact
string `"0"` for fire-on-arrival or a dashboard-clock nanosecond timestamp.
Outside clients should use 5552 for synchronized events.

Typed fields require all nodes updated to v1.22 or later and migrated `fields`
manifests pushed with the framework update; older nodes silently drop them.
