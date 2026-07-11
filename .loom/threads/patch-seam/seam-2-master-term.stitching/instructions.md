# seam-2-master-term

**GATED: requires `seam-1-contract-amendment` tied. Do not claim before.**

Implement master gain as a provided term (seam ruling R1: unconditional, no
compat path, no `subscribes` gate).

- `dashboard/osc_bridge.py`: broadcast `/all/os/master <0..1>` (idempotent
  full-state) on master change; include current master in the per-device
  catch-up push (the `/os/params` reply path, ~line 237). **Delete** the
  `mix × master` multiply in `send_device_param` and delete `resend_volumes`
  (+ its call sites in `server.py`). The wire carries raw mixes only.
- `tools/simfleet.py`: accept `/all/os/master`, log it (`os/master <v>`) so a
  verify can assert delivery; relay to nothing (fake device has no engine).
- Browser-free `verify_*.py` in this stitch dir (venv: `~/.venvs/bopos`; find
  repo root by marker, never `..` hops): master change → one broadcast, no
  per-device volume re-sends, raw mix on the wire, catch-up carries master to
  a late-joining sim device.
- helper.py needs **no handler** (master is for the engine; PD hears 6660
  directly — the OS-layer routing is Bob's, listed in
  `.notes/pd-edits-for-bob.md` A5). Facilitator/index master slider keeps
  working — it now just drives the broadcast.

Net diff should be **negative** on the dashboard side. Contract text: the
Provided-terms section landed by seam-1.
