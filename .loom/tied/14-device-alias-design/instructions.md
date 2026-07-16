# 14-device-alias-design

**Ratified by Bob on 2026-07-16.** The complete design is retained at
`.lore/items/2026-07-16-device-alias-design-ratified/content/proposal.md`.

Memorable physical-box aliases use the “Freda Sparks sits in Seat 0” model:

- deterministic, collision-resolved, persisted two-word defaults from UID;
- `Freda` and `Sparks` anchor globally broad curated lists: ASCII only, short,
  easy to pronounce in English, with vivid non-name pop-star surnames;
- editable global host registry, retained across venues and excluded from
  virtual/simulated devices;
- alias primary, hostname/UID technical secondary, Seat identity independent;
- Forget genuinely removes the runtime observation and registry entry;
- no alias leakage into Seat names, hostname, node state, OSC, or venue state.

This stitch is the design gate only. Production registry, generator, editing
and cross-surface UI are a separately claimed implementation follow-up.
