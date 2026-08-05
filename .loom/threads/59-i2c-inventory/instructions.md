# 59-i2c-inventory

Show the I2C devices actually connected to a physical device, in the Device
tab, without SSH.

Raised by Bob on 2026-08-05: *"it would be useful if in the device tab you
could see the connected i2c devices"*.

## Starting state — measured, not assumed

Most of this already exists; what is missing is a path from the bus to the
dashboard.

- **The scanner is written and used.** `python/io/sys_i2c.py` probes
  `0x03–0x77` with i2cdetect's own strategy (read-probe for `0x30–0x37` and
  `0x50–0x5F`, quick-write elsewhere) and treats `EBUSY` as present — that is
  i2cdetect's `UU`, an address a kernel driver already owns, e.g. a bound DAC.
  It takes a `skip` set so the poll loop's live peripherals are reported
  without being poked.
- **The io bridge already exposes it on the wire**: `/io/scan [bus]` →
  `/io/scan <addr>…` (`python/io/main.py:178-184`), and it passes the live
  peripherals' addresses as `skip`. But the io bridge is **localhost only** —
  it listens on 8880 and replies to 6662, which is the *engine*, not
  `bopos.py` (`docs/PORTS.md`, contract §"Ports"). The dashboard cannot reach
  it, and nothing forwards it.
- **`bopos.py` already imports `sys_i2c`** (`python/bopos.py:50-53`) and
  answers a boolean `has_i2c` in the `/os/report` JSON
  (`python/bopos.py:1282-1303`), which the Device tab already renders as one
  `<dl>` row (`dashboard/static/js/dashboard.js:1746`). So today the operator
  can see *that there is a bus* and nothing about what is on it.

So the work is: pick how the address list travels device → dashboard, then
render it. The bus scan itself needs no new code.

## The question the first stitch answers

`/os/probe <what>` (contract §6) is the obvious vehicle — it exists precisely
for "demand-driven, one-shot inspection", it is unicast to the requester, and
an unknown `what` is silently unanswered. But it currently answers only from
values `bopos.py` **already holds** (patch-authored `/report` values plus a
four-entry held-fact set, `python/bopos.py:1554-1571`); a bus scan is work
performed on request, which widens what `/os/probe` means. The alternative — an
`i2c` array in the `/os/report` JSON — makes the scan happen on every report
instead of on demand.

Two constraints that must survive whichever is chosen:

- **Addresses are not device types.** `sys_i2c.py` says it in its own
  docstring: discovery, not assumption. The UI may hint at well-known
  addresses, but it must not claim a chip it has not talked to.
- **`bopos.py` does not know the io bridge's peripheral registry**, so a scan
  it runs itself cannot populate `skip` — it would probe addresses the io
  bridge's poll loop is actively reading. Whether that is harmful in practice,
  and what to do about it, is the substance of `1-scan-transport`. It is the
  reason this is two stitches and not one.

## Widened 2026-08-05, same day, by a live session

Bob brought an ADS1115 up on Ciro Toast in a terminal and asked for that
workflow in the Device tab. The transcript and findings are in
`session-2026-08-05-ciro-toast.md` beside this file; `ads.py` and `watch.py`
are the scripts that ran. It changes the shape of this thread from "show the
addresses" to **"detect and test a sensor on a device"**, in four moves:

1. **Scan** — what is on the bus (`1-scan-transport`, `2-device-tab-inventory`).
2. **Identify** — an address is not a chip. The session needed a register read
   to tell `0x4b` from `0x1a`.
3. **Instantiate and know it worked** (`3-peripheral-lifecycle`). The session's
   real failure was a create with **both** arguments wrong — `io create adc
   ads1015 0x48` against an ads1115 at `0x4b` — whose only symptom was silence,
   because `/io/error` is sent to the engine and no patch routes it.
4. **Test it** (`4-sensor-test-window`) — a bounded capture returning a
   rest/min/max/swing verdict *and* the payload verbatim as PD receives it,
   because Bob also needs to patch thresholds against real numbers.

Two constraints came out of it and bind the children:

- **Moves 3 and 4 must go through `io/main.py`**, which owns the peripheral
  registry and holds the chip open — two processes driving one ADS1115 is a
  contention problem nobody should invent. So `1-scan-transport` should build
  the relay rather than have `bopos.py` scan alone; it is needed either way.
  The obstacle is measured: `io/main.py:40-41` constructs one OSC client
  hardcoded to `127.0.0.1:6662`, so a relay needs a reply route, not just a
  request route.
- **Nothing here streams.** Contract §6 deleted the meter plane and declined
  the leased probe deliberately. A bounded window returning one summary needs
  none of that reopened, and it is also the better instrument — see
  `4-sensor-test-window`.

## Children

1. `1-scan-transport` — the device→dashboard path for the address list, and
   the relay everything else rides. Touches the OSC contract, so it ends in a
   Bob-ratifiable proposal, however small the amendment.
2. `2-device-tab-inventory` — the Device tab scan surface, plus simfleet
   parity. Anchored on `1`.
3. `3-peripheral-lifecycle` — create/destroy a peripheral from the dashboard
   and surface the result. Anchored on `1`. Contains a defect fix that stands
   alone: a failed `io create` is currently invisible.
4. `4-sensor-test-window` — "test this sensor for N seconds", returning a
   verdict and the PD-shaped values. Anchored on `3`.

Not queued: `57-preset-drift-honesty` and `58-patch-push-workflow` hold the
queue. But note this stopped being purely a new capability when the session
found the silent-create-failure defect in `3` — Bob's standing principle
(*"I want to fix and simplify things before making them more complicated"*)
arguably pulls that one forward on its own.
