# seam-2-master-term — results (2026-07-11)

Master is now a provided term (contract §4.1, seam ruling R1): the dashboard
broadcasts `/all/os/master <0..1>` on change and piggybacks it on the
per-device params catch-up push. The wire carries raw mixes only.

## What changed

- `dashboard/osc_bridge.py`: **deleted** `volume_param`, the `mix × master`
  multiply (`send_device_param`), and `resend_volumes`; **added** `send_master`
  (7 lines); the `/os/params` catch-up loop now uses `set_param` and follows
  with `send_master(<id>)`. Net −33 lines.
- `dashboard/server.py`: `set_master` and `load_preset` call
  `osc.send_master()` instead of `resend_volumes()`; the per-device
  `set_param` ws branch collapsed into one `set_param(selector, …)` call.
  Net −7 lines.
- `dashboard/static/js/facilitator.js`: comment no longer points at the
  deleted Python `volume_param` (the JS mirror stays — it picks which param
  the volume card drives, contract §8).
- `tools/simfleet.py`: os-plane accepts `master`, logs `os/master <v>`,
  relays nothing (fake device has no engine).
- helper.py untouched by design: master is engine-bound; the OS-layer routing
  is Bob's PD edit (`.notes/pd-edits-for-bob.md` A5).

## Verification

    ~/.venvs/bopos/bin/python verify_master_term.py   # from this stitch dir

Browser-free. Real `dashboard/server.py` (OSC target 255.255.255.255) + two
real simfleet instances + a SO_REUSEPORT sniffer socket on the sim command
port, so assertions run against the actual datagrams (broadcast reaches every
port-sharing binder on Linux — re-confirmed with a 3-binder spike before
building on it). All 9 checks pass:

- param send carries the raw mix (0.6 on the wire at master=1)
- master change → exactly one `/all/os/master 0.5`, zero volume re-sends
- param send after the change still raw (0.8, not 0.4)
- late-joining sim (distinct mac via --devices-file) gets `/7/os/master 0.5`
  catch-up plus its stored params; its log shows `os/master 0.5`
- both fleet-A devices logged the broadcast; server logged no traceback

Gotcha encoded in the script: OSC floats are 32-bit, so compare wire values
with a tolerance (0.6 arrives as 0.6000000238…).

Hardware note: end-to-end audio behavior (engine actually multiplying master
into `bopos.out~`) needs Bob's PD edit A5 + a real rig — not claimable here.
