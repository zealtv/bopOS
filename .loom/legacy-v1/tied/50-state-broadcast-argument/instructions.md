# 50-state-broadcast-argument

## Where this came from

`08-control-tab-columns/4-n-columns/4-current-show-broadcast` (tied 2026-07-31,
commit `948878a`) recorded a finding that went into its `decisions.md` and into
CLAUDE.md's queue:

> Thirty of the server's thirty-three `state` broadcasts still use the bare
> form; that hazard is latent, unfixed, and named here rather than in a comment
> nobody reads.

The claimed hazard: `broadcast("state", self.state.public())` sends a snapshot
with no `live_controls`, so a client — which replaces `installation` wholesale
on `state` (`dashboard.js:140`) — would blank the Control columns.

## What is actually true

**The payload argument to `broadcast("state", …)` is discarded.**
`server.py:238-239` opens with

```python
if message_type == "state":
    data = await self.public_state()
```

so every `state` broadcast delivers the enriched state whatever the caller
passed. That coercion has been there since `0551ae2` (2026-07-14) — two weeks
before the finding was written, and before `4-current-show-broadcast` itself.
Measured, not read: a probe delivering all three forms (`state.public()`,
`None`, `await public_state()`) to a fake client got byte-identical key sets,
`live_controls` included.

So there is no latent hazard, the "one real choice in the stitch" was not a
choice, and the bare/enriched distinction at a call site is meaningless. The
fix `4-current-show-broadcast` shipped is still correct and still needed — the
two missing broadcasts were genuinely missing — only its stated reasoning is
wrong.

## Why this is worth a stitch rather than a shrug

The queue already carries one entry (Tier 2 item 11, `45-device-enabled-replay-red`)
whose whole lesson is that a stale "still broken" note *sent a later session
hunting a fixed bug*. This is the same pathology one step earlier: a note
inviting a future session to "fix" 30 call sites that cannot be fixed because
they do not do anything.

## The work

1. **Remove the misleading argument.** The 30 bare calls are not merely
   redundant, they are the thing that generated the false finding: reading a
   call site tells you nothing about what is sent, and the two forms look like
   they differ. Make `broadcast`'s payload optional and drop the argument at
   every `state` site, so the call site stops making a claim it cannot keep.
   This is provably behaviour-preserving — the argument is discarded — and must
   be shown to be, not asserted.
2. **Guard it.** A living test in `tests/` that pins the coercion behaviourally:
   a `state` broadcast delivers `live_controls` regardless of what the caller
   passed. It must fail if someone "helpfully" restores the argument as the
   payload.
3. **Correct the record.** The tied `4-current-show-broadcast/decisions.md` and
   the CLAUDE.md queue entry both state the hazard as live. Amend both — per
   the repo's supersession rule, name the superseding stitch inline rather than
   silently rewriting history.
4. **Thread 47.** The same feedback flagged the browser suite as flaky under
   load in the `47` family. `47-live-param-kinds-flake` is *tied* (`edb0a5f`)
   and its named defect fixed, but CLAUDE.md Tier 2 item 12 still describes it
   as open and undiagnosed. Establish the current suite state by measurement,
   correct the entry, and record whatever residual flake actually reproduces.

## Verification

`fast`, plus the full browser suite (the flake question needs a real full-load
run, not a standalone one).
