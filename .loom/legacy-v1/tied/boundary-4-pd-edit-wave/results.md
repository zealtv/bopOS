# boundary-4-pd-edit-wave results

## Outcome

Bob completed the Pure Data rewrite wave. The engine-facing PD transport is now
`[bopos]` on the selector-stripped 6661 surface, the old `bopos.osc` transport
is gone, and the patch-side buses were rewritten to the ratified `bopos-*`
names.

Agent work in this stitch stayed inside the allowed scope:

- maintained the live Bob-owned edit list in `.notes/pd-edits-for-bob.md`;
- normalized `python/helper.py` lifecycle/provision notifications to
  `/notify <event>` with no legacy engine-notification aliases retained;
- added a stitch-local static verifier;
- ran the focused static and macOS N=1 gate support checks;
- did not edit any `.pd` file.

## Static verification

Commands run:

- `~/.venvs/bopos/bin/python .loom/threads/engine-boundary-design/boundary-6-contract-v12-and-renames/boundary-5-launch-context-and-topology/boundary-4-pd-edit-wave.stitching/verify_boundary4_pd_wave.py`
- `~/.venvs/bopos/bin/python -m py_compile python/helper.py`

Observed PASS conditions:

- `pd/bopos.pd` exists and `pd/bopos.osc.pd` is absent.
- `pd/bopos.pd` contains the common 6661 ingress, retained 6662 IO input, and
  7770/8880 localhost outputs.
- The named buses are present as specified:
  `bopos-context`, `bopos-master`, `bopos-param`, `bopos-point`,
  `bopos-cue`, `bopos-notify`, `bopos-io`, `to-bopos-io`,
  `to-bopos-report`.
- `pd/bopos.point.pd` listens on singular `bopos-point`.
- `pd/bopos.out~.pd` consumes `bopos-master` and `bopos-notify`.
- The default patch consumes the rewritten buses and no active shipped/reference
  patch retains the deleted legacy symbols:
  `bopos.osc`, `osc-in`, `osc-out`, `from-bopos-io`, `bopos-points`,
  `route-by-id`, `from-helper`, `role:meter`.
- No shipped/reference `.pd` retains port literals `6660` or `5550`.
- `python/helper.py` emits only `/notify <event>` for helper-driven lifecycle
  and provisioning notifications; legacy top-level engine notification
  addresses like `/identify`, `/update`, `/shutdown`, `/reboot`, `/checkout`,
  and `/restart-engine` are gone from those producer paths.

## Production-style macOS N=1 gate

Platform: macOS with stock Pd 0.55.2 (`/Applications/Pd-0.55-2.app`).

Automated support checks:

- `lsof -nP -iUDP:6661 -iUDP:6662 -iUDP:6660 -iUDP:5550`
  confirmed Pd owned `6661` and `6662`, and did not own `6660` or `5550`.
- Using the project venv's `pyOSC3`, selector-free messages were injected to
  `127.0.0.1:6661`:
  - `/id 7`
  - `/os/master 1`
  - `/p/gain 0.75`
  - `/pt 0 0 0.5`
  - `/cue snap`
  - `/notify identify`

Bob's audible/manual confirmation:

- "got sound" after the N=1 gate injection, covering the intended live patch
  behavior on the running default patch.

## Known limits / not exercised in this session

- The dynamic gate did not retain an automated artifact for `to-bopos-io`
  observed on `8880`.
- `to-bopos-report` was intentionally not exercised because the active patch did
  not expose a live report sender path and the session constraint was to avoid
  modifying the `.pd` patch for the test.
- Clean post-stop release of `6661` and `6662` was not rechecked after the
  audible gate.

These were recorded honestly rather than papered over. The main static checks
and the primary macOS N=1 audible gate passed.
