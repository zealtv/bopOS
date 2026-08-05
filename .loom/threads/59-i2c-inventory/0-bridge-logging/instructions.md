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

## Verify

Boot the stack on a real node and read the log. The failure case is the
valuable one: send a create naming an address with nothing on it and confirm
the failure is legible in the file within a second or two, rather than
appearing minutes later when a buffer happens to flush.
