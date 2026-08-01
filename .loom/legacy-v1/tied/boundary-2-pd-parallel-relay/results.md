# boundary-2-pd-parallel-relay results

## Change

`python/helper.py` no longer excludes PD when relaying selector-addressed
`/os/master` and `/p/*` terms to the selector-stripped localhost 6661 engine
surface. PD's existing `netreceive -u -b 6660` remains untouched beside its
6661 ingress as the reversible migration safety net.

Identity (`/id`), decomposed points (`/pt`), scheduled cues (`/cue`), and the
current identify notification (`/identify`) already used 6661 and were not
given duplicate paths. The ratified eventual `/notify <event>` spelling needs
the lockstep PD edit in `boundary-4`; implementing it here would either break
the current abstraction or require a forbidden `.pd` edit. No `/helper/*`
alias was added.

## Duplicate-delivery analysis

During the migration window, PD receives master and parameter terms through
both direct 6660 selector routing and the new 6661 relay. Both terms are
full-state, idempotent values, so applying the same value twice leaves the same
final state and needs no compatibility/deduplication mechanism. A patch must
not interpret provided-term arrival itself as an edge trigger; doing so would
already violate their full-state semantics. The later PD edit wave removes the
direct path after its safety gates, eliminating the duplicate delivery.

The real three-PD macOS smoke continues to print the known fixed 6660/6661/6662
`Address already in use (48)` warnings. The per-instance common ingress ports
still bind and operate. Those warnings are expected until the later topology
stitches remove the production fixed binds from audition instances.

## Verification

The compile command redirected bytecode out of the Loom tree, and the verifier
sets `sys.dont_write_bytecode` before repository imports. No stitch-local
`__pycache__` was created.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/helper.py \
  .loom/threads/engine-boundary-design/boundary-6-contract-v12-and-renames/boundary-5-launch-context-and-topology/boundary-4-pd-edit-wave/boundary-3-framework-slimdown/boundary-2-pd-parallel-relay.stitching/verify_pd_parallel_relay.py
```

PASS (no output).

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  .loom/threads/engine-boundary-design/boundary-6-contract-v12-and-renames/boundary-5-launch-context-and-topology/boundary-4-pd-edit-wave/boundary-3-framework-slimdown/boundary-2-pd-parallel-relay.stitching/verify_pd_parallel_relay.py
```

PASS: confirmed the PD abstraction retains 6660 and 6661 listeners; master,
parameters, identity, points, cues, and identify notification all produced the
expected selector-stripped, decodable 6661 messages.

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  .loom/tied/seam-2-master-term/verify_master_term.py
```

PASS: nine dashboard/simfleet checks covering raw parameter values, one master
broadcast, no composed resends, late-join catch-up, fleet delivery, and no
server traceback.

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  .loom/tied/audition-1b-pd-mac-gate/verify_pd_mac.py
```

PASS: three real PD/CoreAudio engines bound distinct local ingress ports,
reported distinct identities, consumed the common surface, and stopped
cleanly. The known fixed-port collision warnings remained as expected. Bob
confirmed audible output during this run.

## Boundaries

This verified real, audibly producing PD processes locally on macOS, but not a
production node or installation LAN. It did not assess calibrated audio level,
latency, clipping, or multi-device acoustic quality. No Pure Data file was
edited.
