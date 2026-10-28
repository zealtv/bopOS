# 6-live-sensor-in-patch-edit: editor input

**Status:** after `9` · absorbs the dropped `5-simulated-input`
**Goal:** in Patch Edit, the editor's audition engine takes its IO input from a
real device's stream or from simulated panels, and can't tell them apart.

Spec: `../0a-io-design-review.tied/proposal.md` (ratified 2026-10-04; Bob's words in `rulings.md`). Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit. Wire changes are ratified as written in proposal §8; write the matching contract text and §15 row as each piece ships.

- Input source picker in Patch Edit: a device (its stream, `8`) or
  **simulated**. Values reach the audition engine on its 6662, the door
  `tools/iosim.py` uses.
- **Simulated panels** (proposal §5): the same component as `9`, arrows
  reversed. Inputs are sliders and pads you drive; outputs show what the patch
  wrote (e.g. an OLED preview).
  - `iosim`'s fidelity rules: stream continuously at poll rate (or the
    patch's `[change]` swallows the first press), and a press goes to the
    opposite rail from that channel's rest (polarity is per channel).
  - Values reset each session (Bob).
- The source is always named (*Ciro Toast · live* / *simulated*). The stream
  ends when Patch Edit closes or the source is unpicked.
- Out of scope (future): fake input into a real device's engine.
