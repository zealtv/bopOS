# 0a-io-design-review

The I2C/peripheral layer gets one design pass — architecture **and** operator
workflow together — before any more of this thread is built.

**Raised by Bob 2026-08-05**, after setting up an ADS1115 on Ciro Toast by
hand: *"the io being localhost only came up at the beginning of this major
sweep of redevelopment — i had questions regarding debugging sensors, getting
them to readout on the dash (or elsewhere) — this was the same friction i felt
today during setting up the adc … we need to be able to simulate i2c devices
locally to aid patching, as well as read / debug i2c devices in some kind of
usable workflow while keeping the system architecture clean. requires some
thorough thought and clear thinking."*

This is a **design gate**: it ends in a written proposal Bob ratifies, and it
is marked `.waiting` when the proposal is ready to read. Do not implement past
it.

## Why this exists rather than four independent stitches

The friction is the same friction twice, months apart, and every child of this
thread pays for it separately. The cause is one architectural fact and one
missing surface:

- **The io bridge is localhost-only and one-directional in practice.** It
  listens on `127.0.0.1:8880` and constructs exactly one OSC client,
  hardcoded to `127.0.0.1:6662` — the *engine*
  (`python/io/main.py:40-41`). So everything the bridge knows goes to Pure
  Data and nowhere else, and `bopos.py` — the only process on the LAN — can
  neither ask it anything nor hear its replies. `docs/PORTS.md` and the
  contract's §Ports carry the boundary as designed.
- **Consequently there is no readout anywhere but PD.** `/io/error` is sent
  where no patch routes it; `/io/report` and the create's `✓` are `print()`
  calls into an unredirected, block-buffered stdout; a bus scan exists and is
  unreachable. Each child of this thread is, in part, a workaround for that.

`1-scan-transport` currently frames the transport as its own local choice
between three options. That framing is too narrow now: the same relay
question is answered by `3-peripheral-lifecycle` (create/destroy + result),
`4-sensor-test-window` (a bounded capture returning a verdict) and
`5-simulated-input` (injection, on the device or on a laptop). Four stitches
each deciding a piece of one transport is how architectures get muddy.

## What the design must settle

**1. The transport.** One answer, serving scan, create/destroy, registry
report, error, test-capture and injection. The candidates are already written
up in `1-scan-transport` (a `bopos.py`-side scan; a `bopos.py` ↔ bridge relay
on 8880; a field in the `/os/report` JSON) — but decide them as one surface,
not per-feature. Constraints already measured and binding:

- `bopos.py` cannot see the bridge's peripheral registry, so anything it
  scans alone cannot populate `skip` and will probe addresses the poll loop
  owns. Whether that actually disturbs a live peripheral is a **measurement
  owed on the rig**, not a judgement call.
- A relay needs a *reply route*. `io/main.py`'s single hardcoded client is
  the obstacle; changing it is a small change with architectural
  consequences, so state what the bridge's reply model becomes.
- Nothing here streams. Contract §6 deleted the meter plane and declined the
  leased probe deliberately; a bounded window returning one summary needs
  none of that reopened.

**2. Ownership.** Who owns a peripheral — the patch or the operator? Today the
patch is the only creator, via `io create` message boxes on `loadbang`, and an
engine restart re-runs them. If the dashboard can create too, the two
authorities collide on every restart. `3-peripheral-lifecycle` raises this;
it belongs here, because the answer shapes what the Device tab may offer.

**3. The debugging workflow, as a workflow.** Bob's is the use case: a chip
arrives, he wants it on the bus, instantiated, producing numbers he can see,
and then patched against. Today that is SSH, `i2cdetect`, a hand-written
`ads.py`, a hand-written `watch.py` and a tail of a logfile that only exists
if you relaunch the process yourself. Walk the whole path end to end and say
what the operator does at each step and where it is surfaced — Device tab,
Monitor dock, or elsewhere. The two things he named specifically are
**readout** (see the live values, in the peripheral's units *and* verbatim as
PD receives them) and **identification** (an address is not a chip;
`sys_i2c.py`'s own docstring is the standing rule).

**4. Local simulation.** A first-class answer to "develop a patch with no
hardware", not a bolt-on. `tools/iosim.py` already exists and is verified
audible on Bob's laptop, and `5-simulated-input` records two fidelity findings
that any design must respect: it must stream continuously at the poll rate
(not only during a press), and rest polarity is **per channel** — on the real
rig A1 rests low and rises while A0/A2 rest at rail and fall. Say where
simulation runs (laptop, device, dashboard-driven relay), how a simulated
peripheral is distinguished from a real one so nobody debugs a ghost, and
whether the simulator and the bridge share a definition of a peripheral or
merely a wire format. Note that simfleet answers a flat `"has_i2c": False`
today (`tools/simfleet.py:480`) and has no peripheral model at all.

**5. What stays out.** Say plainly what this layer will *not* become. The
contract has repeatedly declined streaming planes; this is the moment to
decide whether that holds under a "watch this sensor" workflow, and to say so
in the amendment rather than letting a leased probe arrive by accident.

## Evidence to work from

- `../session-2026-08-05-ciro-toast.md` — the transcript of the friction, with
  `../ads.py` and `../watch.py`, the scripts that actually answered the
  questions. This is the primary source; the workflow proposal should be
  legible as a replacement for exactly those scripts.
- `../instructions.md` — the thread's measured starting state.
- `feature-backlog/60-io-dispatch-silence` — the just-closed silent-dispatch
  defect, which is the same failure family (the bridge knew and told no one)
  and a good test of whether a proposed design would have surfaced it.
- `python/io/README.md` — the current namespace model (`/io/<verb>` for
  management, `/io/<name> <command>` for peripherals) as it stands after the
  2026-08-05 rework.

## Deliver

- `proposal.md` in this stitch: the transport decision with its alternatives
  and why they lost, the ownership ruling, the workflow walkthrough, the
  simulation model, and the explicit out-of-scope list.
- A note of which contract amendment falls out of it, at whatever version is
  current — the wire is Bob's to ratify, so the amendment is proposed here
  and written by the stitch that implements it.
- A revised sequencing note for this thread's children, since the design may
  merge, split or retire some of them.

Then mark `.waiting` and surface it.

## What is NOT gated on this

Deliberately kept claimable, because neither touches transport, protocol or
UX:

- **`0-bridge-logging`** — redirection and `-u` in `bash/start.sh`. One line,
  node-side, and it makes the design work easier by making the bridge audible.
  Worth landing first.
- **`7-poll-timing`** — the ADS1115 `data_rate` default and the
  `sleep(1/rate)`-on-top-of-the-read period bug. Node-side sampling
  arithmetic; a design pass changes nothing about it.

Everything else in the thread (`1-scan-transport`, `2-device-tab-inventory`,
`3-peripheral-lifecycle`, `4-sensor-test-window`, `5-simulated-input`) is
downstream of this and carries a `needs/` edge, directly or through `1`.
