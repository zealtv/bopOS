# 2-audio-config-implementation

Implement the ratified design in `.loom/tied/1-audio-config-design/decisions.md`
and land its v1.11 amendment in `docs/OSC-CONTRACT.md`.

The owned surface is:

- detected playback-card and mixer-control reporting;
- `JACK_SAMPLE_RATE`, `JACK_PERIOD_SIZE`, and `JACK_NPERIODS` defaults and
  launch consumption alongside `SOUNDCARD` / `MIXER_CONTROL`;
- exact physical-UID `audio-config` request and terminal receipt;
- atomic config persistence, JACK/engine restart, rollback, in-memory config
  refresh, and effective output-state reapplication;
- Device-tab Audio UI and operator feedback;
- simfleet/audition parity;
- living browser-free protocol/config tests under `tests/` plus focused
  Dashboard UI verification.

Do not edit `.pd`. Hardware claims require a real Pi; record untested JACK,
audible, and iPad/touch boundaries explicitly.

## Verify

- Living browser-free config/protocol tests under `tests/`.
- Playwright Device-tab guard driving server + simfleet on non-default ports.
- Real-hardware apply is a Bob/rig gate — say so in the stitch rather than
  claiming the audio actually reconfigured.
