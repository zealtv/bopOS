# 1-contract-amendment

Amend `docs/OSC-CONTRACT.md` (v1.6 → v1.7) with two additive changes to the
engine surface (§4.2). Bob ratified the intent on 2026-07-17: "There are some
messages that I'd like to be able to send to Bopos from a patch running on a
Pi. These are mostly the admin controls: being able to update the patch,
update Bopos, shut down, reboot. Also I'd like to receive BOPOS version and
patch version in addition to the active patch name."

## Change 1 — engine-sent admin requests (7770)

New engine-sent message on localhost 7770:

```
/admin <action>    action ∈ {update-patch, update-bopos, shutdown, reboot}
```

Each routes to the node's existing admin behaviour — the same code paths the
dashboard verbs use (`pull-active-patch`, `update`, `shutdown`, `reboot` in
`python/bopos.py`). No selector, no reply to the engine — the actions are
terminal or restart the engine anyway; outcome receipts continue to flow to
the LAN model where applicable. Unknown actions are ignored with a logged
warning, never fatal. Soften the "administrative commands never cross"
sentence in §4.2 to name this bounded exception.

## Change 2 — versions in the run context

Extend the launch-delivered run context (§4.2 run-context paragraph):
PD additionally receives `bopos-context version <string>` and
`bopos-context patch-fingerprint <string>`; other engines receive
`BOPOS_VERSION` and `BOPOS_PATCH_FINGERPRINT` in the environment.
`version` is the node's git shorthand (what heartbeats already carry);
`patch-fingerprint` is the active patch's canonical content fingerprint
(§7, v1.4 sense), or the literal string `unknown` when it cannot be
resolved at launch. Both are strings end-to-end — never floats (PD 32-bit
rule). Patch name is already delivered; this is additive.

## Deliverables

- Contract §4.2 text updated; changelog row `1.7 | 2026-07-17 | …` pointing
  at this stitch (`.loom/tied/1-contract-amendment/` once tied) as the
  decision record.
- Note in §4.2 that the PD-side bus plumbing for `/admin` (e.g. a
  `to-bopos-admin` bus in `pd/bopos.pd`) is Bob's to add — agents never edit
  `.pd` files.

Verification: doc-only stitch — proofread the rendered markdown; grep docs/
and CLAUDE.md for stale `v1.6`/`1.6` contract-version mentions and update
prose that names the current version. Do NOT touch `python/bopos.py`'s
reported `contract_version` here — that lands with the implementation in
2-engine-admin-requests.
