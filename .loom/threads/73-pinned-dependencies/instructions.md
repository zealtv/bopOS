# 73-pinned-dependencies

**Status:** ready
**Goal:** a fresh dashboard or device install gets the versions that were
tested, so nothing changes under a show.

## Today

- `dashboard/requirements.txt`: `fastapi`, `uvicorn[standard]`,
  `python-osc`, `websockets` — no versions.
- `python/requirements.txt` (nodes): `pyOSC3`, Adafruit CircuitPython
  libraries, `piicodev` — no versions.
- `install-device.sh` runs `apt-get upgrade -y` and installs `jackd2`,
  `puredata` etc. at whatever the image's repos currently serve.
- Test-only extras (`playwright`, `Pillow`, `pyflakes`) live only in docs.

## Do

- Pin Python deps to the versions in the working venv and on the rig (check
  what Finn Jet / Ciro Toast actually run), via constraints or lock files.
  Mind the Python 3.9 floor (`tests/test_python_floor.py`) and Trixie's 3.13.
- A dev/test requirements file for Playwright, Pillow, pyflakes.
- Decide whether `apt-get upgrade -y` belongs in the installer (it can move
  JACK or Pd under you); record the tested Pi OS image and Pd/JACK versions.
- Say how to update pins deliberately (a short note in `docs/INSTALL.md`).

Done when: fresh venv from the pinned files passes fast + browser tiers.
