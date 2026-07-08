# sync-3-jitter-harness

The honest measurement tool: something that records how tight cues actually
fire across N devices, reusable on sim (now) and hardware (sync-4).

- [ ] `tools/sync_measure.py`: schedules a cue burst, collects per-device
      fire-timestamps (helper.py/simfleet report actual fire time — add that
      report if sync-2 didn't), computes spread/jitter stats, writes a small
      report (max/typical spread, per-device offsets).
- [ ] Hardware mode designed in but not run here: a flag where fire-evidence
      comes from GPIO toggle / audible click for external recording (see parent
      "Done when" — <10 ms typical target on WiFi).
- [ ] Run it against simfleet + a couple of real helper.py instances on
      loopback; commit the sim-mode report into this stitch dir as the baseline.
- [ ] Document usage in the stitch + a pointer from `dashboard/README.md` or
      docs so the hardware run (sync-4) is a one-liner for Bob.

Loopback numbers are a floor, not the deliverable — say so in the report.
