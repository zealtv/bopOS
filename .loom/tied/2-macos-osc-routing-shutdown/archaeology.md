# Routing archaeology

Date: 2026-07-26

The incident is a latent macOS limited-broadcast fault exposed by a routing
ownership change, not evidence of recent network or OS drift.

- Before `5eda7b4` (`Separate physical device control routing`),
  `uid_command()` called the single mutable `send()` path. Simulation and Patch
  Edit retarget that path to loopback, so UID administration during those
  sessions did not necessarily exercise the default limited-broadcast target.
- `5eda7b4` introduced `physical_destination` and routed UID administration
  through `send_for_uid()`/`send_physical()` for real devices. That correctly
  made physical administration independent of the execution mode, but exposed
  the raw default target to first-seen enabled/report/asset traffic.
- The tied dashboard and fresh-device verification harnesses inspected in this
  pass launch `dashboard/server.py` with explicit non-default ports and
  `--osc-target 127.0.0.1`. They prove the wire/control paths but do not exercise
  a bare `./run.sh` limited broadcast from macOS.
- The repository recorded errno 49 for unbound macOS limited broadcast on
  2026-07-11, before `5eda7b4`. That is consistent with the route having always
  been unavailable from an unbound sender on this Mac.

The regression therefore pins both sides of the seam: destination ownership
continues to keep physical traffic off the loopback execution route, while the
non-loopback sender becomes source-bound and transport failure can no longer
truncate heartbeat handling.

## Hardware discovery correction

The first Imani adoption run found a competing tunnel route that the initial
ordinary UDP-connect probe could not distinguish:

- heartbeat peer: `192.168.0.103`, received on `en0`;
- ordinary probe source: `100.113.184.66` on `utun4`;
- directly attached `en0` source: `192.168.0.100`.

macOS's route table contained both `utun4` and `en0` routes for
`192.168.0/24`, with the tunnel winning ordinary lookup. A throwaway probe with
`SO_DONTROUTE` selected `192.168.0.100`; the same probe without it selected the
tunnel. Source discovery now prefers that direct-LAN probe and retains ordinary
lookup only as a fallback for explicitly routed unusual venues.
