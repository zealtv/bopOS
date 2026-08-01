# hw-onboarding-doc — results (2026-07-11)

Wrote `docs/HARDWARE.md` (linked from the README's SOUNDCARD bullet): the
audio-chain map (dtoverlay → ALSA card → jackd `-dhw:$SOUNDCARD` → engine →
amixer mute), a 7-step bench procedure with a visible pass/fail per step,
the fold-back-into-the-repo rule (table row + grow `mixer_candidates` in
`python/helper.py` when the control is generic), and the board table.

Honesty rules from the brief are load-bearing in the text: untested cells
are blank or explicitly "unverified" (including DigiAMP+'s mute control —
it's the deployed default but its mute path has never been benched); the
engine-stop fallback is documented as degraded and engine-lethal, not
design centre (contract §6); the input-HAT recipe is cross-linked as
future columns in the *same* table (`audio-input/input-1-hw-recipe`), not
a second doc.

All technical claims were sourced from code in this session: `set_mute` /
`mixer_candidates` and `read_node_config` in `python/helper.py`,
`SOUNDCARD` in `bash/start-engine.sh`/`start.sh`, contract §2/§6. The
per-patch vs node-level `bopos.config` ambiguity is called out explicitly
(two different files, same name).

Verification: docs-only — no runtime surface. Per-board verified rows need
Bob or a bench Pi; the table ships empty by design.
