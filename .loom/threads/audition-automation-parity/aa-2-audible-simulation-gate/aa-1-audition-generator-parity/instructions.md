# aa-1-audition-generator-parity

Implement and verify node-side parameter generators in `tools/audition.py`.

## Implementation

- Import and reuse `python/paramgen.py` through the audition tool's existing
  Python-module path setup.
- Load canonical manifest declarations once per rig and resolve qualified,
  nested parameter identities exactly as production does.
- Give every `VirtualNode` its own `GeneratorEngine`. Separate slots are
  required for per-node current values and free LFO phase; non-free generators
  may use the shared local monotonic clock, which is the audition rig's common
  clock and keeps local instances phase-aligned.
- In the selector-matched `/p/*` relay path, parse manifest-declared numeric
  messages and apply them to each matched node's generator. Generator emissions
  must go to that node's existing engine port as `/p/<identity>` containing only
  the established scalar or `value duration_ms` ramp primitive.
- Match production error behavior: malformed automation for declared numeric
  parameters is logged and dropped. Preserve byte-equivalent behavior for
  ordinary scalar sets and pass through undeclared/nonnumeric parameters as the
  relay does today.
- Close every generator deterministically when engines/rig stop; do not leave
  scheduler threads behind. Preserve cues, points, assignments, mute, groups,
  patch inventory, edit mode, and custom `--engine-command` behavior.

## Focused verification

Add a browser-free `verify_audition_automation.py` in this stitch using real
loopback OSC and fake engine UDP receivers (copy the topology patterns from
`.loom/tied/audition-1a-relay-launcher/verify_audition.py`). Assert:

1. plain numeric sets remain unchanged;
2. a fade becomes numeric scalar/ramp engine frames and reaches its target;
3. an LFO produces multiple numeric frames—never the original grammar tokens;
4. seat/group/all selectors reach exactly the matched virtual nodes;
5. each node owns independent slot state, while non-free phase is aligned;
6. `stop` and a subsequent plain value replace the generator immediately;
7. integer crossings follow shared `paramgen` semantics;
8. malformed declared-numeric grammar is dropped without killing the rig;
9. nested identities and nonnumeric/undeclared pass-through do not regress;
10. rig shutdown leaves no generator worker alive.

Run the new verifier plus the shared parameter-automation verifier and the
closest audition boundary/launcher regressions. Compile every touched Python
file with `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache`. Record exact pass counts and
state explicitly that this stitch proves the relay/engine datagrams, not human
audibility; the parent stitch owns that gate.
