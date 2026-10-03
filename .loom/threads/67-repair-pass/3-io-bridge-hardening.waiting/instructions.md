# 3-io-bridge-hardening

**Status:** software verified; waiting on Bob’s Finn Jet hardware check and wire ratification · absorbs `feature-backlog/60-io-dispatch-silence`
**Goal:** the io bridge never fails silently and never fights itself over a chip.

Not the transport or ownership questions — those are `59/0a`. This is repair
inside `python/io/` as it stands.

## Fix

1. **LIS3DH ignores its address** (`io_lis3dh.py`): it always uses the chip
   default and sets no `self.address`, so a wrong-address create "succeeds" and
   `/io/scan` probes the live chip. Honour the address; set `self.address`.
2. **Bad arguments throw silently:** a malformed `/io/create` address or
   `/io/poll` rate raises in the handler thread. Reply `/io/error` instead.
3. **Unknown `/io` verbs only print** — reply `/io/error` too (from `60`).
4. **Re-create leaks:** replacing a name drops the old instance without
   `cleanup()`.
5. **No lock** between `write_data` (server thread) and `read_data` (poll
   loop) on the same chip.

## Done when

- A browser- and hardware-free test of `handle_io`, pinning (from `60`):
  verb-before-peripheral precedence, `RESERVED_NAMES`, the `len(parts) == 1`
  guard, and that no branch is silent.
- Tests for 1–5.
- Hardware: create the LIS3DH on Finn Jet at a wrong address → error, not
  zeros. Separate claim.

Defects 2 and 3 in `59/3-peripheral-lifecycle` (doubled read-error log;
LIS3DH dead after replug) stay there — claim them together if convenient.

## Current close-out

Software repairs and 10 regression tests are complete; all 356 fast tests pass.
See `verification.md` for exact claims and the explicitly pending hardware check.
New error semantics are proposed in `wire-proposal.md`, not implemented.
The stitch remains open in `.waiting`; no Pd or contract edits.
