# Handoff — 2026-07-12 (boundary 4 ready for Bob)

## Loom

- `boundary-3-framework-slimdown` is tied.
- `boundary-4-pd-edit-wave.waiting` is next and blocked only on Bob-owned PD
  edits. Resume with `./.loom/loom claim boundary-4-pd-edit-wave`.
- Do not edit `.pd` files as an agent. Walk Bob through the live specification
  in `.notes/pd-edits-for-bob.md`, then build the verification harness.

## Boundary-3 hardware gate

Fresh DigiAMP+ Pi `bop000` is reachable as `pi@bop000.local` using
`~/.ssh/id_ed25519_spectre`. A real system unit from
`systemd/bopos-helper.service` is enabled and supervises helper directly with
`Restart=always` and `RestartSec=250ms`.

Retained recovery timings were 1.780–1.999 s across three trials. The combined
audible kill/mute trial recovered in 2.191 s. Bob confirmed snap cues stopped
while muted and returned on resume; JACK and PD did not restart. Full details
and the verifier are in `.loom/tied/boundary-3-framework-slimdown/`.

The DigiAMP+ `Digital` control is verified for engine-safe mute. Its indicator
light did not reflect ALSA mute state. Percent values are misleading: 10% was
-93 dB; -40 dB was audible but very quiet. `docs/HARDWARE.md` records this.

## Pi state at handoff

- bopOS checkout: `/home/pi/bopOS` (origin/main plus synchronized current
  runtime files; do not treat the Pi checkout as the source of truth).
- venv: `/home/pi/venv`, full `python/requirements.txt` installed.
- Trixie needed `python3-dev` to build `rpi_ws281x` and `RPi.GPIO`.
- JACK and PD were started manually for the gate; the handoff leaves the
  hardware mixer muted for safety.
- Legacy `/etc/rc.local` was not installed, avoiding a duplicate helper.

Useful checks:

```sh
ssh -i ~/.ssh/id_ed25519_spectre pi@bop000.local \
  'systemctl status bopos-helper.service; pgrep -alf "helper.py|jackd|pd"'
ssh -i ~/.ssh/id_ed25519_spectre pi@bop000.local \
  'amixer -c DigiAMP sget Digital'
```

## Boundary-4 supporting-agent prerequisite

Current `python/helper.py` still emits legacy engine notification addresses
(`/identify`, `/update`, `/shutdown`, `/reboot`, `/checkout`, and
`/restart-engine`). During boundary 4, normalize these producers and tests to
the ratified `/notify <event>` surface. Do not preserve aliases in PD.

After Bob's edits, run the static/headless assertions and production macOS N=1
recipe in `.notes/pd-edits-for-bob.md`. Only tie boundary 4 after Bob confirms
the point sound, snap cue, and identify chirp.
