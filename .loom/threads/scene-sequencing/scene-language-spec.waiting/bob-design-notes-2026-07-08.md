# Bob's design notes — 2026-07-08 (verbatim, lightly formatted)

Captured from Bob's session notes. Headline: **defer this, but it is worthy of a
dedicated and thorough design effort.** Do not start solo — Bob wants to co-design.

## UI: Ableton session-view style clip launching

> I am imagining an ableton session-view style layout, with clips in a grid.
> Vertical channels separate "tracks" which are simply an organisational
> affordance. The right most clip is a master clip and allows for triggering
> all clips in a row (a scene).
>
> Clicking on a clip opens an inspector which has a codebox defining that
> clip's sequence. There are also options for oneshot or loop, and follow
> actions (after n times, go to [next, previous, random, other, stop]). This
> might be a separate tab akin to the spatial layout and facilitator.

## The language itself

> The language itself is something I'd like to get some intelligence dedicated
> to. It requires defining timed sequences, musical elements (bars, beats,
> subdivisions, notes and velocity), as well as arbitrary parameters (filter,
> gain, degrees, other, `/robot/elbow/left 55.3`). So it needs to be able to
> handle defining and working easily with OSC addresses and values, as well as
> timed events in musical time and clock time.
>
> bop already has some approaches to defining harmony in a compact and
> readable way, as well as some beginning experiments with multivoice rhythmic
> sequences — though if this is not a clear fit we shouldn't force it.
>
> I want the scripting language to be readable, compact, ergonomic, efficient.
> These kinds of installations can require very high throughput of OSC
> messages. How addresses are defined, and how that might relate to tracks,
> needs some consideration — there are likely some clever solutions here. We
> are essentially creating a scene-based, script-based, OSC sequencing engine.
> A task in its own right.

## Priority

> This can be deprioritised until after the rest of the dashboard is built.
> Once we can manage devices, we have what we need to roll out, as sequencing
> can be handled externally — but this is something we will want to dig into
> at some point to relieve the Ableton instability and friction.

## Spatial patterns and node-side primitives

> Being able to define sweeping gradients, random scattering, synchronous
> events, grouped events, are all things I want to be able to achieve. And
> visualising these patterns is also important for UX. A thought occurs that
> the same way we are sending points, we could design some primitive functions
> (i.e. gradients, noise, other) that could be sent as compact messages that
> then expand node-side. If gradients can be created then that mostly
> dissolves the video-mask approach (though still worth considering if it is
> an easy win, as it would be an extremely ergonomic workflow).

## Digest for the eventual design session (agent notes, not Bob's words)

- The grid model: clips × tracks, master column = scene trigger, per-clip
  oneshot/loop + follow actions (Ableton follow-action semantics: after n
  repeats → next/previous/random/other/stop). Inspector = codebox with the
  clip's sequence source. Likely a new dashboard tab alongside spatial map and
  facilitator.
- Language requirements gathered so far: musical time (bars/beats/subdivisions,
  notes+velocity) **and** clock time; first-class OSC address/value ergonomics;
  compact/readable/high-throughput; track↔address relationship deserves clever
  design; look at bop's harmony notation and multivoice rhythm experiments as
  seeds but don't force fit.
- Spatial: gradients / noise / scatter / sync / groups as **compact primitives
  expanded node-side** (like spatial-audio Stage B's broadcast trick,
  generalised). Visualising the patterns matters for UX. If node-side gradient
  primitives land, `video-mask` mostly dissolves (kept only if it's an easy,
  ergonomic win) — cross-noted in that stitch.
