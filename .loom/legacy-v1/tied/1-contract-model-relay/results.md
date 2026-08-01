# Verification record — contract/model/relay

Date: 2026-07-16 (Australia/Melbourne)

## Outcome

- `python/manifest.py` now exposes `qualify_param(declaration)` as the
  canonical `path + name` identity helper. Validation accepts duplicate leaves
  in distinct paths, rejects duplicate qualified identities, enforces the
  ratified segment grammar, eight-segment/255-byte bounds, and keeps flat
  declarations compatible.
- The shared relay preserves every `/p/<segment>...` tail and every argument;
  production and audition callers now admit that variable-length patch plane.
  `/os/master` remains an exact three-part, one-value provided term.
- simfleet loads, stores, and logs canonical qualified identities, while flat
  names retain their existing special diagnostics.
- `docs/OSC-CONTRACT.md` and `README.md` document the additive nested shape.
  The amendment is folded into contract v1.5 so this child does not advertise
  the not-yet-landed Seat-group selector work as a new runtime revision.
- No dashboard state/editor or live-control behavior, Seat-group matching, or
  `.pd` file was changed.

## Commands and results

### Focused verifier

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/parameter-addresses/param-address-1-implementation.tending/1-contract-model-relay.stitching/verify_param_contract_relay.py
```

Result: **28 passed, 0 failed**. It covers valid/invalid paths, bounds,
duplicate leaves and identities, flat compatibility, strict master shaping,
preserved argument lists, production/audition parity, simfleet qualified
state/logging, and flat/nested × All/Seat/group selector shaping. The group
cases deliberately exercise the selector-opaque shared shaper only; matching
and membership semantics remain for the Seat-group stitch.

### Compile and whitespace checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/manifest.py python/relay.py python/bopos.py tools/audition.py tools/simfleet.py
git diff --check
```

Result: **passed**.

### Adjacent engine-boundary regression

Run outside the filesystem/network sandbox because the verifier binds local
UDP ports:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/boundary-5-launch-context-and-topology/verify_launch_context.py
```

Result: **67 passed, 1 expected obsolete assertion failed**. All live flat
parameter, master, selector, production-source, audition UDP, launch-context,
shell, SC, and compile checks passed. The single failure asserts that every
four-part address—including `/all/p/gain/extra`—must be rejected. That is the
exact legacy constraint this ratified stitch replaces; the focused verifier
proves the new variable-length behavior and separately proves nested
`/os/master` remains rejected. The tied historical verifier was not modified.

### Additional historical checks

- `.loom/tied/patch-manifest/test_patch_manifest.py`: current flat manifest,
  invalid declaration, helper params, and simfleet param checks passed; seven
  unrelated assertions are stale against already-ratified mandatory-manifest,
  report, and engine-liveness changes.
- `.loom/tied/dist-4-demos/verify_dist4_demos.py`: both shipped flat manifests
  validated; its later dashboard socket check could not run in the sandbox.
- `.loom/tied/boundary-2-pd-parallel-relay/verify_pd_parallel_relay.py`: cannot
  serve as a current regression because it requires removed
  `pd/bopos.osc.pd`.

These historical failures predate and do not exercise the nested parameter
implementation. The stitch-local verifier uses the current production modules
and replaces their obsolete shape assertions.

## Unverified boundaries

- No physical node or installation-LAN broadcast was tested.
- No audible engine/Pure Data route was tested. The existing
  `.notes/pd-edits-for-bob.md` entry already records the exact nested route and
  confirms no framework `.pd` change is required; Bob owns the first concrete
  nested consumer and audible gate.
- Group selector matching/membership is intentionally absent. The shared
  shaper proves that `g<id>` can compose with nested paths once that later
  matcher is implemented.
