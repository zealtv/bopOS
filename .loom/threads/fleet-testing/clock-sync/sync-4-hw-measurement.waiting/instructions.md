# sync-4-hw-measurement

**Status:** waiting — needs Bob + a real rig
**Goal:** prove the parent's done-condition: N Pis on installation Wi-Fi fire an
audible click within < 10 ms typical, recorded.

## Steps

- [ ] Run `tools/sync_measure.py --mode hardware` on ≥ 3 Pis on the installation
      Wi-Fi; save the report here.
- [ ] If over budget, tune first (ping rate, smoothing window, outlier policy) —
      don't re-architect.
- [ ] Fold the measured numbers back into the contract note / parent.

This is also the unmeasured half of `44/5-pd-adoption`: two-device event
forward-sync timing was never checked on hardware.

An agent may do a reduced pass (2–3 reachable Pis, hosts confirmed in-session)
for real Wi-Fi numbers. The full ≥ 3-Pi run with audible/GPIO evidence is
Bob-coordinated. Don't tie on loopback or single-Pi numbers.
