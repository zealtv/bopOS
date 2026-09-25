# Handoff — audition spatial math ready (2026-07-13)

State at handoff: `preview-0-channel-model-spike.waiting` is next, blocked only
on collaborative Bob-owned PD math. Bob wired a pass-through
`pd/bopos.audition~.pd` inside `pd/bopos.out~.pd`, after the production
master/notification mix and before `dac~`. `bopos.out~` remains the public
abstraction; fixed stereo is the whole Wave 1 ABI. These PD changes and Bob's
`patches/default/main.pd` edits are intentionally uncommitted. Agents inspect
but never edit them.

## Agreed model

- Normal operation and zero positions: exact L→L / R→R pass-through.
- One position: co-located stereo or duplicated dual-mono. Preserve stereo
  image while applying shared distance and directional balance. A left-only
  signal remains hard-left stereo; never infer mono from signal activity.
- Two positions: two mono elements. For inputs `x0`, `x1` and matrix rows
  `(l0,r0)`, `(l1,r1)`: `L=x0*l0+x1*l1`, `R=x0*r0+x1*r1`.
- Use one complete fixed-stereo matrix update with 10–30 ms smoothing. Bad
  state retains the last valid matrix or bypasses; it never silences output.
- Higher channel counts, arguments, and discovery are fully deferred.

## Next session — patch alongside Bob

1. Read this handoff, check usage, and claim
   `preview-0-channel-model-spike.waiting`.
2. Inspect Bob's current `bopos.audition~.pd` and `bopos.out~.pd` read-only.
3. First add four manual gain controls with `line~` smoothing and prove the
   two-mono equation using distinguishable steady signals. Do not start OSC or
   listener geometry yet.
4. Prove unity bypass and that missing/malformed state cannot mute audio.
5. Then audition the one-position stereo law. Start with mid/side:
   `M=(L+R)/sqrt(2)`, `S=(L-R)/sqrt(2)`. Constant-power pan `M`; preserve a
   bounded `S`. Do not freeze the width law until Bob listens at centre, hard
   left/right, and intermediate positions. Duplicated mono has `S=0`, so it
   spatializes naturally.
6. After the sound is accepted, agents specify/test controller matrix math and
   only then freeze the private message frame.

Suggested captures: unity bypass; impulse/steady tone separately on L and R;
dual-mono; correlated and decorrelated stereo; rapid gain sweep. Record exact
amplitudes, smoothing time, and Bob's observations in the stitch.

## Position convergence after the PD spike

Dashboard `/os/assign` already sends the ordered `pos1`/`pos2` list. The next
Python child makes `tools/audition.py` retain positions per `VirtualNode`, apply
identity changes, heartbeat convergence, and recompute the complete matrix on
assignment, listener movement, engine restart, or reconnect. Listener state is
audition-local, outside the fleet contract.

## Deferred strategy

`pd-audition-host/host-0-three-child-spike.waiting` preserves `[pd~]` hosting
only for future raw stems, manual multichannel routing, or DAW integration.

## Repository and usage

Latest committed plan before this handoff: `4488b0e`. Expected dirty PD files:

```text
M  patches/default/main.pd
M  pd/bopos.out~.pd
?? pd/bopos.audition~.pd
```

Codex usage at wind-down: 85% five-hour, 54% weekly. The meter reported the
five-hour reset as `2026-07-12T17:00:29Z` despite the 2026-07-13 local date;
re-check rather than trusting that stale-looking timestamp.
