# 60-io-dispatch-silence

Residue of `59-i2c-inventory/6-io-create-dropped`, filed here 2026-08-05 on
Bob's call once the defect it was raised for was fixed and the rig confirmed
it. **Not critical. Not queued.** What is left is hardening, not a bug.

## What this was, and why it is no longer urgent

It was raised as a live defect: a patch's `[io create adc ads1115 0x4b(`
reached the bridge as address `/io` with `create` as the first argument, no
branch matched, and the bridge dropped it in complete silence — no log, no
reply. The peripheral outlives the engine, so a create issued by hand during
debugging persisted across every patch push and the system looked like it
worked; only a reboot exposed that the patch had never once created its own
peripheral.

**All of it is fixed, and the reboot check has now passed** — Bob rebooted
the node and I2C came up from the patch's own `loadbang`, which is the thing
that had never happened. The fixes, for the record:

- `pd/bopos~.pd:43-45` are now `oscformat io report` / `io create` / `io poll`
  (commit `b6785cd`) — the one-word-per-object correction, since `[route]`
  strips the matched selector.
- The unmatched `[route]` branch now prefixes too: `set io $1`
  (`pd/bopos~.pd:46`, commit `bd2d989`), so `scan 1` becomes `/io/scan 1` and
  `lights fill 0 255 0` becomes `/io/lights fill 0 255 0`. The generic branch
  is now the *peripheral* path by design, which is also why the old worry that
  "`scan` has no outlet on that `[route]`" no longer applies to anything.
- `python/io/main.py` logs rather than drops: `Unrouted OSC: <address> <args>`
  with the peripheral list (`handle_command`), `Unknown /io verb` in
  `handle_io`'s else, and `/io/error <name> no-bus|create-failed` on a failed
  create.
- `python/io/README.md` documents both namespaces and the `/io/<name>
  <command>` rule explicitly.

**One deliverable from the original stitch is deliberately NOT carried
forward.** "Accept a bare `/io` with the verb as the first argument" should
not be built. The stitch already argued against itself there, and now that
`RESERVED_NAMES` and the `/io/<target>`-with-values model have shipped, it
would only legitimise a malformed address that nothing emits.

## What is actually left

1. **No test.** Nothing in `tests/` touches `handle_io`, and it is pure
   dispatch — browser-free and hardware-free. The invariants worth pinning are
   real ones: verb-before-peripheral precedence, `RESERVED_NAMES`, the
   `len(parts) == 1` guard (which exists precisely so `/io/lights/fill` does
   not misread `fill`'s first value as a command), and that no branch is
   silent.
2. **The unknown-verb path logs but never replies.** `Unknown /io verb` goes
   to the bridge's stdout only, so a patch that typos a verb still gets
   nothing back on the wire. An `/io/error` there would close the last silent
   path.

Both overlap with live work in `59-i2c-inventory`: `0-bridge-logging` owns the
same failure family, and `3-peripheral-lifecycle` owns "a failed `io create`
is currently invisible", which is item 2 one level up. **If either of those is
claimed, fold this in there rather than reviving this stitch** — it is not
worth its own pass.
