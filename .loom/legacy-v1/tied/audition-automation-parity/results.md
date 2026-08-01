# Audition automation parity — complete

Managed audible Simulation now executes the shared `python/paramgen.py`
generator grammar per virtual node, with selector isolation, take-over, and
generator cleanup covered at the relay boundary.

The audible gate exposed and closed two additional engine/display seams:

- float generators are evaluated by bopOS and deliver scalar-only frames to
  engines, preventing duration atoms from corrupting Pd control inlets;
- identical synchronized LFO retriggers preserve the facilitator's running
  visual anchor, matching the node generator's absolute-time phase.

Focused relay verification passed 12/12, shared generator verification had
zero failures, managed catch-up passed 6/6, the phase-sample regression passed
4/4, and the real Dashboard + simfleet + Chromium half-cycle retrigger test
passed 3/3. Bob accepted the real macOS 14.6 / Pd 0.55.2 CoreAudio workflow:
audio is clean and the looping LFO automation is working. No `.pd` file was
changed.
