# 0-bridge-logging

Give `io/main.py` a logfile and unbuffered output, so the diagnostics it
already prints reach someone.

Split out of `3-peripheral-lifecycle` on 2026-08-05 at Bob's call. It has no
dependency on `1-scan-transport` and no protocol implications — it is a change
to one line of `bash/start.sh` — so it should not sit behind the rest of this
thread.

## The problem

`bash/start.sh:63-66`:

```sh
( cd "$BOPOS_DIR/python/io" && exec "$PYTHON_BIN" "$BOPOS_DIR/python/io/main.py" ) &
```

No redirection and no `-u`. So the bridge's output is lost twice over: it goes
to whatever stdout `start.sh` inherited at boot, and Python block-buffers it
because that is not a tty — meaning even a process someone thought to attach to
prints nothing for a long time.

What is being thrown away is not noise. It already prints the startup banner
and port map, `✓ Created <name> (<type> @ <addr>)` on success, `<name>:
4-channel ADC ready` from the peripheral itself, and `Error reading <name>` per
failed poll.

## What it is worth — measured, 2026-08-05 on Ciro Toast

Relaunching the identical process as `python -u main.py > /tmp/io.log` turned a
silent box into a running commentary, with **no code change at all**. Within
the same session that log:

- confirmed a create had succeeded against the real chip
  (`✓ Created adc (ads1115 @ 0x4B)`), which had until then been unknowable
  from outside;
- captured 24 × `Error sending OSC: while sending: [Errno 111] Connection
  refused` during a patch push — the window in which the engine was down and
  the bridge was polling the ADC into a dead port. Self-healing and harmless,
  but on the shipped configuration that window is completely invisible.

## Deliver

- Redirect to a logfile beside the other run state (`$RUN_DIR` holds the pid
  files) and add `-u`. Decide on rotation or a size cap — a bridge erroring
  every poll cycle writes continuously, and this must not fill a node's card.
- Do the same for `bopos.py` if it has the same shape, but check rather than
  assume; do not widen this into a general logging design. `42-node-logging`
  is the thread that owns the append-only log destination and is Bob-gated —
  this stitch is a redirection, not that.
- Keep the pid-file contract intact: `bash/stop.sh:21` stops the bridge by
  `$RUN_DIR/io.pid`, with the full script path as its matching pattern.

## ⚠️ The cap is not optional — land it with the redirect (2026-08-14)

The size cap above reads like a nice-to-have. It stops being one immediately,
because the Kite Choir I2C cable-run validation is about to create exactly the
scenario that fills a card.

The spool pole puts the LIS3DH ~1 m from the Pi over Cat-5/6, and
`i2c-cable-run-validation` in **kite-choir-brains** is the soak that decides
whether that run is sound. `tools/i2c_soak.py` tests the cable standalone with
the stack stopped — but the natural follow-up is to run the **real stack** on
that cable for a working day and read this log. If the run is marginal, every
poll cycle produces `Error reading <name>`. At the true poll rate that
`7-poll-timing` restored (`poll_rate 10` now means 10 Hz, not 7.1), a marginal
bus writes a log line ~10× a second for 8 hours, unattended, on an SD card.

Worse, the fault this is meant to catch is **intermittent**, so the run has to
be long to be worth anything — which is precisely the run that must not die of
a full card partway through, taking the evidence with it.

So: **a size cap or rotation ships in the same change as the redirect**, not as
a follow-up. Two further asks that fall out of the same use case:

- **Prefer capping over truncation on rotation.** The valuable part of a
  soak log is the *distribution of errors over time* — clusters are the
  diagnosis. A scheme that keeps only the newest bytes throws away the onset,
  which is the half that says what triggered it.
- **Timestamp the lines.** Unbuffered output alone gives ordering, not
  incidence. "24 errors in one minute at hour six" and "24 errors spread over
  eight hours" are different verdicts on the cable and are indistinguishable
  without timestamps.

Context: [`i2c-cable-run-validation`](https://github.com/zealtv/kite-choir-brains)
in the brains repo, and `tools/i2c_soak.py` here.

## Verify

Boot the stack on a real node and read the log. The failure case is the
valuable one: send a create naming an address with nothing on it and confirm
the failure is legible in the file within a second or two, rather than
appearing minutes later when a buffer happens to flush.
