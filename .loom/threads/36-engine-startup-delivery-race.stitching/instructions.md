# 36-engine-startup-delivery-race

Harden engine delivery during node startup.

Observed on Finn Jet 2026-07-23: the Dashboard rediscovered and assigned the
node after `bopos.py` opened the LAN listener but before Pure Data opened the
localhost engine port. Three provided-term sends raised
`[Errno 111] Connection refused`; startup later completed normally.

Determine which early terms can be lost (assignment ID/groups, replayed live
parameters, or other provided terms), then establish a readiness/replay
boundary that:

- keeps the node listener and Dashboard responsive while the engine starts;
- delivers authoritative ID, group context, and persistent live values after
  the engine is ready;
- does not blindly buffer transient cues or point traffic;
- has simulator and browser-free node-protocol coverage.

This is logged only; it is not part of the hostname-retirement stitch.
