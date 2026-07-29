# Decisions — 10-venue-preset-retirement

Date: 2026-07-29.

## Legacy adoption

The retired `presets` key is ignored when the current installation or a saved
venue is loaded. It is absent from public and durable state, and therefore
falls out on the next installation save or venue resave. There is no migration
into patch presets: Bob confirmed the venue-preset store is empty.

## Preset boundary

Only installation-scoped presets retired. The patch primitive remains:

- sparse documents under `patches/<patch>/presets/`;
- apply/save/delete controls on desktop Control cards and Device panels;
- save/recall in Patch Edit;
- fingerprinted references, playback expansion, flattening, and
  capture-as-step in Shows.

The standalone facilitator has no preset affordance at all, as ruled in the
design addendum Q4.

## Parent assessment

`04` through `10` are complete. The later-added
`11-browser-test-failures` remains the only child preventing
`41-preset-primitive` from tying. Its generator Stop/tick failure is
independent of venue-preset retirement and its own instructions require this
stitch to tie first.
