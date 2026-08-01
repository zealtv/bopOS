# d8-5 live-rig findings

## Confirmed on bop000

- Dashboard Identify reached bop000 as `/all/os/identify` with its UID; audible
  Identify and cue-point playback were then confirmed by Bob.
- Bound seat `0` routes lifecycle actions with numeric selector `0`.
- The node was on `ec33524`, matching `origin/main`; only `patches/default` was
  installed. Local patch/demo work is unpublished, so the one-item dropdown was
  an accurate view of the node rather than an inventory failure.
- The commissioned DigiAMP gain was already `0.00 dB`. Its independent playback
  switch was off; switching it on restored output without changing gain.

## Mute safety boundary

The ratified engine-boundary and seam records require mute below the engine so
it remains effective if the engine is hung or dead. Engine stop is only a
degraded fallback. On DigiAMP this means toggling the ALSA playback switch while
leaving its gain fixed at the commissioned `0 dB`.

A first reconnect draft replayed the dashboard's `muted` value after heartbeat.
That is unsafe because `muted` is runtime-only and defaults to false after a
dashboard restart: an unknown state could therefore clear an intentional
hardware mute. The draft was removed. Reconnect assignment must not infer or
change mute state.

Any future convergence design must distinguish unknown from explicitly
unmuted. A safe candidate is to persist explicit operator mute intent and replay
it only when known, while legacy/unknown state remains fail-safe and never
auto-unmutes.
