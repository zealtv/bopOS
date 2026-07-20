# audition-automation-parity

Close the audible-Simulation parity hole for parameter automation.

Production `python/bopos.py` and protocol-only `tools/simfleet.py` expand the
ratified §3.2 generator grammar before the engine, but managed audible
Simulation launches raw engines behind `tools/audition.py`, whose relay
currently forwards the unexpanded argument list. As a result the Dashboard can
show a moving fade/LFO while the simulated patch receives no usable numeric
motion.

Done means the audition relay executes the same shared `python/paramgen.py`
grammar and generator semantics per virtual node, sends only the existing
selector-free scalar/ramp engine surface, and the behavior is proven both by
automated relay tests and a real audible managed-Simulation gate.

Constraints:

- no OSC-contract change and no new engine-facing address;
- reuse `python/paramgen.py`; do not fork the grammar or scheduler;
- preserve selector/group targeting, nested parameter identities, ordinary
  scalar parameters, nonnumeric pass-through, cue timing, and engine topology;
- never edit `.pd` files. If an unexpected Pd-side need appears, record it in
  `.notes/pd-edits-for-bob.md` and stop at that boundary;
- verify in proportion to `docs/VERIFICATION.md` and retain exact evidence in
  each child stitch.

Sequence is encoded below: software parity first, audible adoption second.
