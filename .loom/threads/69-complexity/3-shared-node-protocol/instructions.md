# 3-shared-node-protocol

**Status:** ready · proposal first, then implementation
**Goal:** the node side of the wire is implemented once, so the real node and
its simulators can't drift apart.

## Today

Three implementations of uid-admin dispatch, reports, provisioning verbs and
listings: `python/bopos.py` (real node), `tools/simfleet.py` (N fake nodes),
`tools/audition.py` (laptop relay). Evidence of drift: `contract_version` stale
in all three (fixed by `67/4`); simfleet doesn't model manifest validation
(`58/4`); simfleet's docstring still describes `LegacyProtocol` /
`bopos.osc.pd`. The house rule "protocol behaviour lands in simfleet too" is a
manual sync with no check.

## Decide (proposal.md)

- What can be shared: message parsing and validation, verb tables, reply
  shapes, report construction — with the side effects (reboot, engine start,
  amixer) injected.
- Two OSC libraries are in play: `pyOSC3` on the node, `python-osc` in the
  dashboard and tools. Is one enough? `pyOSC3` is old; check what the Pi image
  ships and the 3.9 floor.
- How this fits the horizon refactor (`glean:horizon-refactor`): several
  engine instances per device and non-Pd engines.
- A parity test as an alternative or complement: the same datagram into each
  implementation → the same reply.

Surface the proposal to Bob before implementing — it shapes the horizon
refactor.
