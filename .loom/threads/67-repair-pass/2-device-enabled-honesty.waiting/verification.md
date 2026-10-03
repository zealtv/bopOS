# Verification — 2-device-enabled-honesty

2026-10-03. Software half verified; Ciro Toast hardware half **not claimed**.

Passed:

- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest discover -s tests -p test_device_enabled.py`: **10 tests, OK** (`device-enabled.log`).
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest discover -s tests -p test_audio_config.py`: **9 tests, OK** (`audio-config.log`).
- `./tools/run-tests.sh fast`: **362 tests, OK** (`fast.log`).
- `git diff --check`: passed.

The new mute-failure regression uses the real enforce_mute path with one mixer
target and a failing mocked amixer command. It checks no store write occurs,
original persisted bytes are unchanged, a freshly loaded fixture still reads
enabled, no /os/enabled receipt is sent, and an encoded/decoded /os/report
still has device_enabled=true and output_enabled=true. Only amixer is called:
no engine-stop fallback.

Additional checks cover failed enabling of a previously disabled device,
failed disabling when no durable key exists, successful mixer application
before any live/durable flag change, persistence and receipt after success,
and live report honesty if the mixer succeeds but persistence fails. Existing
exact-UID targeting, MUTE ALL independence and positive report-field checks
remain green. Audio configuration regression checks also pass.

No UI wording, wire/report field, contract, engine fallback or Pd change.
No browser tier needed for this node-side order repair. These are mocked mixer
and local store checks, not proof of acoustic silence or actual card capability.

## Pending — Bob's Ciro Toast rig check

**NOT RUN / NOT CLAIMED.** Disable Ciro Toast from the Device page while its
patch produces sound. Record node revision, card/control, amixer outcome,
actual audibility, receipt/timeout and the refreshed /os/report. If the mixer
fails, confirm the previous persisted/live enabled state is retained and the
report does not claim output disabled. Verify successful enable/disable on a
working mixer as appropriate; no engine-stop fallback is permitted (Bob's
2026-07-23 ruling).

If the rig demonstrates a need for a card-specific operator explanation, write
it as a proposal for Bob; do not ship wording or wire fields without his ruling.
This hardware claim stays open. Park the stitch `.waiting`, not tied.
