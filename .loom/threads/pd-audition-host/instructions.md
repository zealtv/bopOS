# pd-audition-host — deferred multichannel DAW strategy

The **Audition Host** is retained as the advanced multichannel/DAW integration
strategy, not the default listener-preview path.

Default preview now lives in the `audition-rig/audition-2-listener-puck`
thread: `bopos.mix~` spatializes each real engine before the OS stereo sum,
with no JACK, Core Audio tap, aggregate device, or parent host.

## When this strategy becomes relevant

Resume this thread only when a composition requires one or more of:

- isolated raw device/element stems in PD or a DAW;
- manual parent-patch rerouting before final output;
- more hardware output channels than the simple stereo preview;
- dense process management or offline multichannel capture; or
- a concrete comparison showing N normal engine processes are too expensive.

The proposed Bob-owned `pd/audition-host.pd` runs N unchanged patches in
`[pd~]` subprocesses. Child `[dac~]` channels appear as parent signal outlets;
the parent alone owns hardware/DAW audio. This is macOS/Linux consistent and
keeps Core Audio taps/JACK as optional specialist fallbacks.

The stereo-first spike plan remains in `host-0-three-child-spike.waiting`, but
is deliberately deferred until the need above exists. Its future design must
reuse the same creation-argument channel count and indexed-matrix model
established by `bopos.mix~`, rather than creating a competing preview protocol.
