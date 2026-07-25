# Proposal — per-parameter generator affordance

Written 2026-07-25 (autopilot). **Awaiting Bob's ratification.**

- **Artifact (mockups):** https://claude.ai/code/artifact/6f9c395e-f7b0-43f3-b132-dbe1ebc2f780#p1
- **Source of record:** `../control-surface-proposals.html` (Proposal 01)

## Recommendation (see artifact for mockup + annotations)

Give every numeric control a two-state **mode switch — `value ▸ gen`**. Flipping
to `gen` opens an inline drawer hosting the **extracted `automation-2` builder**
(waveform / rate / depth / center / phase + the ratified `16-param-automation`
waveform preview); the value readout becomes the live generator output. One
control, one param address, two authoring modes — same component in editor /
Device tab / Control tab.

## Open questions Bob must settle
1. Drawer (in editor/Device) vs popover (on the dense All aggregate).
2. Mixed aggregate: broadcast one generator to all members, or disable when they disagree?
3. Stop affordance: third seg state vs in-drawer control.

**Seam to 41:** what a generator means *inside a preset* stays the preset
primitive's design; this settles only live authoring.
