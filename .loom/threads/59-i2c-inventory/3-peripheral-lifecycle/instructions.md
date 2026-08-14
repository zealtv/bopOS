# 3-peripheral-lifecycle

Let the operator instantiate a peripheral from the Device tab, and — the part
that matters — **see whether it worked**.

Anchored on `1-scan-transport`: that stitch builds the `bopos.py` ↔
`io/main.py` relay this one sends over.

## The defect this fixes, which exists with or without a UI

`io/main.py` replies `/io/error <name> no-bus|create-failed` when a create
fails (`python/io/main.py:156-165`). Its OSC client is constructed once,
hardcoded to `127.0.0.1:6662` (`python/io/main.py:40-41`), so that reply goes
to the engine — where, in `patches/fire-button/main.pd` and every other patch
in the repo, nothing routes it. On 2026-08-05 Bob's create failed twice over
(wrong type *and* wrong address, see `../session-2026-08-05-ciro-toast.md`)
and the only symptom available to him was silence.

**A failed create must be observable.** That is true independently of this
thread's UI and is the first thing to fix.

**The bridge's own diagnostics are discarded too**, for a different reason —
`bash/start.sh` launches it with no redirection and no `-u`. That half was
split out as `0-bridge-logging`, which is a one-line change with no dependency
on anything here and should land first. This stitch owns only the OSC side:
`/io/error` reaching the operator who triggered the create.

## Deliver

- **Create / destroy from the dashboard**, relayed to `io/main.py`, with the
  result reported back rather than assumed. `create` already exists;
  `io/main.py` has **no destroy verb at all** — adding one is in scope,
  because an operator who creates the wrong thing from a button must be able
  to take it back without restarting the stack.
- **The registry as state, not as a print.** `/io/report` currently prints the
  active peripherals to the bridge's stdout (`python/io/main.py:172-177`),
  which is unreachable. Make it a reply: name, type, address, and whether its
  last read succeeded.
- **Surface `/io/error`** wherever the operator triggered the create.

## Design questions to settle in-stitch

- **Who owns a peripheral — the patch or the operator?** Today the patch
  authors `io create` message boxes and is the only creator. If the dashboard
  can create too, an engine restart re-runs the patch's creates and the two
  can disagree. The honest v1 answer is probably that dashboard creates are
  **ephemeral test instruments** that do not persist across an engine restart,
  and the Device tab says so; a persisted operator-owned peripheral list is a
  much larger design (it is patch configuration, and patch configuration is
  distributed and fingerprinted). Recommend the small one and record why.
- **Type from address?** `python/io/` knows each module's default address, so
  the scan can *suggest* `ads1115` for `0x48–0x4b`, `mpr121` for `0x5A`, etc.
  It must stay a suggestion — the standing rule from `sys_i2c.py` is
  discovery, not assumption — but a suggestion would have saved this session,
  where the type was as wrong as the address.
- **Address override.** The board that prompted this sits at `0x4b`, not the
  module default `0x48`, so whatever the UI suggests must be editable.

## Verify

Browser journey against simfleet, plus a real create/destroy of the ADS1115 at
`0x4b` on Ciro Toast — the failure paths (`no-bus`, wrong address, wrong type)
are the ones worth exercising, since they are what actually happened.

## Read-error path defect — measured 2026-08-14, handed over from `0-bridge-logging`

With the bridge's output finally reaching a file, verifying that stitch on Finn
Jet meant pulling a live LIS3DH off the bus. Every failed poll logs **two**
lines, and the second one is wrong:

```
12:02:42.122+10:00 Error reading from LIS3DH at address 0x19
12:02:42.122+10:00 Error reading tilt: a bytes-like object is required, not 'float'
```

The first is the peripheral reporting the bus failure, which is right. The
second is `main.py`'s per-poll handler catching a **`TypeError` raised inside
the failure path itself** — `io_lis3dh` returns something (a float? `-1`?)
where a caller expects bytes — rather than a clean "this read failed". So the
operator-facing message names a Python type error instead of the bus, and the
duplication doubles the fault-case log rate to ~20 lines/s at the 10 Hz poll
rate (1670 B/s, 5.7 MiB/hour, measured).

Neither is fatal. But the far more serious finding is what happens on
**reconnection**, and it is a second thing this stitch must handle. But this is the exact log an unattended cable soak is read
from, so a read failure should say *which peripheral, which address, and that
the bus did not answer*, once per cycle.

Two notes. This presumably has always been broken and could not be seen,
because the line went to a closed stdout — which is the case for `0` made by
accident. And the fix likely belongs with whatever this stitch does about
`no-bus`/wrong-address handling, since it is the same failure path; check the
other `io_*.py` modules for the same shape rather than fixing LIS3DH alone.


## Reconnection leaves the LIS3DH silently dead — measured 2026-08-14

Continuing the session above: the sensor was plugged back in, the error lines
stopped instantly, and `/io/report` still listed `tilt: IO_LIS3DH`. That looks
like recovery and is not. Read straight off the chip a few minutes later:

```
CTRL_REG1(0x20)=0x07   CTRL_REG4(0x23)=0x00   WHO_AM_I=0x33
OUT_X=0x00 0x00   OUT_Z=0x00 0x00   STATUS(0x27)=0x00   (x3, 1 s apart)
```

`0x07` is the power-down reset default and `STATUS=0x00` means no sample has
ever been ready. The chip lost power with the cable and came back in its reset
state; `PiicoDev_LIS3DH()` is constructed once in `setup()` at create time and
never again, so nothing reconfigures it. The bridge then polls a chip that
answers perfectly and emits **frozen zeros at 10 Hz with no error at all**.

So the peripheral lifecycle needs a re-init path, not just create/destroy: a
read-failure burst that ends should re-run `setup()` rather than assume the
device came back as it left. Note the ordering problem — the bridge cannot see
"it came back", it can only see "errors stopped", which is indistinguishable
from a peripheral that is answering wrongly.

**Scope note from Bob (2026-08-14):** the LIS3DH is the installation's sensor
and the one on the pole cable, so it is the one that must work. Other modules
will differ — some are stateless per read, others configure registers at setup
— and nothing here is claimed for them; check each rather than generalising
from this one, which is the mistake that produced the retracted claim above.

This matters beyond the bridge: it is the failure mode
`i2c-cable-run-validation` in **kite-choir-brains** is trying to detect. A
marginal 1 m Cat-5 run that momentarily drops the sensor leaves the
installation reading a constant zero tilt, and the log — read naively — says
the errors stopped.
