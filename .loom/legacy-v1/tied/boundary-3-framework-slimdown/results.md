# boundary-3-framework-slimdown results

## Software outcome

- 7770 now registers only `/config`, `/store`, `/load`, and `/report`.
- `/report <name> <values...>` retains the latest typed values under a lock.
- `/<id>/os/probe <what>` replies once, unicast, as
  `/os/probe <id> <what> <values...>` for retained reports and the small held
  fact set (`id`, `uid`, `version`, `update_model`). Unknown probes are handled
  without a reply. No leased probe was added.
- Framework meters, meter config, manifest `role: "meter"`, dashboard meter
  state/UI, simulator meter emission, `/rpt`, helper-reply/echo-report behavior,
  and simulator legacy-report mode were removed. The default manifest no
  longer declares `level` as a meter.
- LAN administration remains framework-owned. Engine-originated admin handlers
  were removed without deleting the LAN implementations.
- No `.pd` file was edited.

## Local verification

All Python commands used `PYTHONDONTWRITEBYTECODE=1` or
`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache`.

- `verify_framework_slimdown.py`: PASS — exact 7770 handlers, typed report and
  selector-gated probes, unknown/mismatched behavior, simfleet probe wire, and
  removed-surface assertions.
- `verify_dashboard_no_meters.py`: PASS — real dashboard + simfleet + headless
  Chromium; declared params remain controls, meter/stray telemetry UI is absent,
  and facilitator remains meter-free.
- `.loom/tied/patch-manifest/test_patch_manifest.py`: PASS, 24 checks.
- `.loom/tied/os-admin-verbs/verify_browser.py`: PASS, 4 checks.
- `.loom/tied/seam-4-facilitator-promotion/verify_facilitator_promotion.py`:
  PASS, 13 checks.
- Python compilation and `git diff --check`: PASS.

The authorized `~/.venvs/bopos` verification environment gained Playwright
1.61 and its Chromium headless shell.

## Required safety gate — passed on hardware

Fresh DigiAMP+ Pi `bop000` (Debian 13/Trixie, arm64, systemd 257) was prepared
as a real node on 2026-07-12. `systemd/bopos-helper.service` supervises
`helper.py` directly as user `pi`, with `Restart=always`, `RestartSec=250ms`,
and no start limit. The legacy `rc.local` path was deliberately not installed:
`start.sh` backgrounds helper and would create a competing listener. The unit
was enabled at boot and owned 6660/7770 alone before the retained migration PD
listener was started.

The focused `verify_helper_death.py` bound the real 5550 reply port, issued
uniquely tokened `/os/ping`, killed systemd's actual helper MainPID with
`SIGKILL`, sent `/os/mute 1` at 10 Hz, and required a new PID plus exactly one
restart before accepting the first restored pong. Five initial trials passed;
three retained unbuffered timing trials measured conservative kill-start to
first-pong recovery of 1.906 s, 1.999 s, and 1.780 s (maximum 1.999 s).

After installing JACK and Pure Data, a production-style default PD engine was
run against the real DigiAMP+. A combined audible trial recovered in 2.191 s,
incremented `NRestarts` 8 -> 9, muted the ALSA `Digital` control, and left the
JACK and PD PIDs unchanged. Bob confirmed repeated snap cues stopped. Resume
returned `Digital` to on, retained the same helper/JACK/PD PIDs, and Bob
confirmed the cues returned. The board mute light remained unlit in both
states and was recorded as non-diagnostic in `docs/HARDWARE.md`.

The bench level was an explicit -40 dB. The initially requested 10% mapped to
-93 dB on this control and was effectively inaudible; this percentage trap is
also recorded in the hardware guide.

Fresh-image setup exposed one installer prerequisite: the complete
`python/requirements.txt` build on Trixie needs `python3-dev` for the
`rpi_ws281x` and `RPi.GPIO` extensions. After installing it, the full declared
requirements installed successfully. The stage did not install legacy
`rc.local`, edit a `.pd` file, or reboot the node.
