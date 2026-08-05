# 6-io-create-dropped

A patch's `io create` never reaches the bridge, and nothing anywhere says so.

**Top of the queue on Bob's call, 2026-08-05.** It is a live defect on a
device he is using, and everything else in this thread is instrumentation for
a chain this bug breaks at the first hop.

## Measured, not inferred

A listener stood in place of the bridge on `127.0.0.1:8880` while the engine
was restarted. What PD actually emits from `patches/fire-button/main.pd`'s
`[loadbang]` → `[io create adc ads1115 0x4b]` → `[s to-bopos-io]`:

```
/io   create  adc  ads1115  0x4b
```

Address `/io`. Verb `create` as the **first argument**.

`python/io/main.py:126-134` splits the address and takes the verb from the
path:

```python
parts = address.strip('/').split('/')
if parts[0] == 'io':
    self.handle_io(parts[1:], args)
```

With a bare `/io`, `parts[1:]` is `[]`, so `handle_io`'s `verb` is `''`, no
branch matches, and the function returns having done nothing. **No error, no
log line, no reply.** The documented form (`python/io/README.md`) is
`[io/create adc ads1015 0x48(` — with a slash, giving address `/io/create` —
so the patch is one character away from correct and the bridge treats the
difference as silence.

## Why this went unnoticed for so long

The peripheral outlives the engine. `bash/start.sh` starts the bridge once; an
engine restart or a patch push does not restart it. So a create issued by any
means — including by hand during debugging — persists across every subsequent
push, and the system looks like it works. Only a reboot, which restarts the
bridge too, exposes that the patch has never once created its own peripheral.
That is exactly how it presented: buttons "working", then dead after a reboot
with no patch change in between.

## Deliver

- **Accept the flat form.** When the address is a bare `/io`, take the verb
  from the first argument. Backwards compatible: a correct `/io/create` is
  unaffected.
- **Never drop a message in silence.** An unrecognised verb, an unknown
  address, or a create with too few arguments must produce a log line and,
  where a reply makes sense, an `/io/error`. This is the same failure family
  as `0-bridge-logging` and `3-peripheral-lifecycle`: the bridge knows exactly
  what went wrong and tells no one.
- **Check the other verbs for the same trap.** `poll`, `report` and `scan` go
  through the identical dispatch, so a patch saying `io poll 20` is dropped the
  same way. Fix `python/io/README.md` if it is ambiguous about the slash.
- The `.pd` side is Bob's; do not edit patches. Note the correct spelling in
  the tie so it can be applied where it belongs.

## Verify

`tests/` gains a dispatch test covering both address forms and the
unrecognised-verb path — browser-free and hardware-free, since `handle_io` is
pure dispatch. Then on the rig: reboot a node and confirm the patch's own
loadbang create succeeds with no hand-issued OSC, which is the thing that has
never happened.
