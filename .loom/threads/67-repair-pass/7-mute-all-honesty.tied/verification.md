# Verification — 7-mute-all-honesty

2026-10-03. Software half verified; hardware **not run / not claimed**.

`set_mute` computes the requested effective output, applies `enforce_mute`,
and only commits `mute_all` after success. Failure returns false and retains
the previous overlay and report. Releasing MUTE ALL while Device enabled is
false still requests a muted mixer. The overlay remains transient: neither
success nor failure writes Device enabled or persists MUTE ALL.

Regression checks exercise failed amixer commands for both Device enabled
values and both previous overlay values, unchanged persisted bytes and
encoded reports, successful mixer-before-state ordering, and a failed LAN
request without a success receipt. The LAN dispatcher still reports that it
handled the packet; that boolean is not a wire success acknowledgement.

Audition sends the requested `/os/master` gate before changing its overlay;
an OSError retains the previous state and returns false. Its tests cover both
directions and ordering. Successful UDP submission is not proof of engine or
hardware silence. Simfleet applies its infallible in-memory output model
before committing the overlay; no artificial mixer or failure hook was added.

Checks:

- Focused device-enabled, mute-safety and audition-output-gate suites:
  **13 + 7 + 4 tests passed**.
- `./tools/run-tests.sh all`: **380 fast tests and all 23 browser journeys
  passed**, exit 0 (`tests.log`).
- Pyflakes on `dashboard/`, `python/`, `tools/` and the two changed test files:
  clean.
- Python compilation of all five changed Python files and `git diff --check`:
  passed.

No new operator wording, wire field, contract amendment, Pd edit or
engine-stop fallback. This tie closes the requested software repair only.

## Pending hardware check — device-agnostic

**NOT RUN / NOT CLAIMED.** Use any current bopOS device, recording its identity,
framework revision, audio card/control and mixer outcome. With a sounding
patch and Device enabled true, apply and release MUTE ALL, checking actual
audibility and refreshed `/os/report` values. Repeat with Device enabled
false: releasing MUTE ALL must leave output disabled. On a card without a
working mute control (or an actual failed mixer operation), confirm the
previous `mute_all` and output report remain unchanged and no success is
claimed. Record persistence of Device enabled independently of the transient
overlay. Do not stop the engine as a fallback.

This is the same outstanding hardware verification as
`2-device-enabled-honesty`; its waiting stitch remains open. No device was
contacted, and no hardware result is inferred from software tests.
