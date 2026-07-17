# 2-engine-admin-requests

Implement the `/admin <action>` engine-sent request ratified in
`1-contract-amendment` (must be tied first).

## Where

`python/bopos.py` runs an OSCServer on localhost 7770 (see the
`OSCServer(('', 7770))` construction near the top and the callback map near
the bottom — `store`, `load`, `config`, `report` style handlers). Add an
`/admin` handler there.

## Behaviour

- `/admin <action>` with action one of `update-patch`, `update-bopos`,
  `shutdown`, `reboot` (strings).
- Route to the existing callbacks: `pull_active_patch_callback`,
  `update_bopos_callback`, `shutdown_callback`, `reboot_callback`. Reuse
  them — do not duplicate their logic. Mind their signatures and any
  reply-socket/requester plumbing: engine-originated calls have no LAN
  requester, so replies must be skipped safely (check how
  `run_admin_verb`/`rev_reply` guard `reply_socket is None`).
- Unknown or missing action: log a warning line, do nothing else.
- Update the `contract_version` string bopos.py reports from "1.6" to "1.7".

## Parity + verification

- `tools/simfleet.py` is part of the deliverable for protocol features:
  simulated nodes should accept `/admin` on their engine-request port and
  log/record the action instead of executing it (they obviously must not
  shut the laptop down). Follow how simfleet already mirrors the 7770
  surface — if it does not model 7770 at all, add the minimal handler and
  say so in the stitch notes.
- Write a browser-free `verify_*.py` in the stitch directory: drive a real
  `bopos.py`-level unit if practical, otherwise exercise the handler
  functions directly (import bopos, call the dispatch with a fake datagram /
  direct callback invocation, assert the right callback fires — monkeypatch
  the callbacks so nothing reboots the dev machine). Locate the repo by
  marker (walk up until `tools/simfleet.py` exists), never fixed `..` hops.
  Run with `~/.venvs/bopos/bin/python`.
- Real-Pi execution of shutdown/reboot is hardware verification — state
  honestly in the stitch notes that it needs Bob or a live rig.

Commit style: plain prose subject, body says why. Note in the commit/stitch
that PD-side `[bopos]` bus plumbing is Bob's follow-up (no `.pd` edits).
