# sync-4-hw-measurement

**.waiting — needs Bob + a real rig.** The parent's tie condition: N Pis on
WiFi fire an audible click within the jitter budget (<10 ms typical),
demonstrated with a recorded measurement.

When a rig is available:
- [ ] Run `tools/sync_measure.py` (sync-3) in hardware mode on ≥3 Pis on the
      installation WiFi; record the report in this stitch dir.
- [ ] If jitter blows the budget: tune (ping rate, smoothing window, outlier
      policy) before re-architecting — HB achieved musical sync with this
      mechanism on WiFi.
- [ ] Fold measured reality back into the contract note / parent instructions.

Agent prep is done when sync-0..3 are tied; everything after that is Bob or a
supervised live session.
