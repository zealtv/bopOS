# audition-0-port-spike

**30–60 minute spike, do first — the whole audition-rig bet rests on it.**

Question: can N processes on ONE host all receive the same UDP broadcast on port 6660,
the way N Pis do on the network? Specifically PD's `netreceive -u` (does it set
SO_REUSEADDR/SO_REUSEPORT?), receiving from a dashboard-style broadcast sender.

Method:
1. Two/three `pd -nogui` instances opening a trivial netreceive-6660 test patch (ask
   Bob for a one-object test patch, or drive `pd/bopos.osc.pd` directly — do NOT write
   new .pd files); broadcast a message at 6660; check all instances print it.
2. Same test with plain Python sockets (python-osc + reuse flags) as the control —
   proves whether the limitation is PD's or the OS's.
3. Test on Linux AND macOS (Bob composes on a Mac; behaviours differ).

Record the result in this stitch dir (what works where, exact socket flags needed).

Fallbacks if PD can't share the port (pick cheapest that works, note in parent):
- tiny UDP fan-out relay: binds 6660 once, re-sends to per-instance localhost ports
  (instances get their port via startup message — start.sh already passes messages in);
- per-instance network namespaces (Linux-only) or containers (both OSes, heavier).

Tie with a clear verdict: "shared-port works on {linux,mac} / needs fan-out because X".

---
**2026-07-08: Linux half done — shared-port WORKS on Linux** (stock PD
netreceive, SO_REUSEADDR; one broadcast → every instance replies; unicast to
a shared port reaches exactly one process, so audible instances must stay on
broadcast+selector addressing). Full data in `results.md`. `.waiting` on the
macOS run — one command for Bob at the bottom of `results.md`.
