# Verification — 73-pinned-dependencies

2026-10-03. Pins from the working host plus explicitly recorded scratch
resolutions; no rig access. See decisions.md for provenance and limits.

## Fresh install acceptance

Both fresh scratch venvs were created outside the repository and installed
from the final pinned files:

```sh
<python> -m venv <scratch>
<scratch>/bin/python -m pip install -r requirements-dev.txt -r python/requirements-laptop.txt
<scratch>/bin/python -m pip check
<scratch>/bin/python -m playwright install chromium --only-shell
BOPOS_PYTHON=<scratch>/bin/python ./tools/run-tests.sh fast
BOPOS_PYTHON=<scratch>/bin/python ./tools/run-tests.sh browser
```

| Interpreter | Scratch venv | Fast | Browser | Dependency check |
| --- | --- | --- | --- | --- |
| Python 3.14.7 (working host interpreter) | /tmp/bopos-pins-fresh | 362 tests, OK | all 23 PASS | no broken requirements |
| Python 3.9.6 (system interpreter, supported floor) | /tmp/bopos-pins-fresh-py39 | 362 tests, OK | all 23 PASS | no broken requirements |

Modern logs use `fresh-*`; floor logs use `fresh-py39-*`. Installation,
Chromium setup, pip check, freeze snapshots, and full fast/browser results
are retained. `working-venv.txt` is the original host snapshot;
`node-resolved.txt` and `py39-resolved.txt` retain resolution provenance.
No package was installed into or upgraded in ~/.venvs/bopos.

The exact docs/INSTALL.md comparison Python block was executed in both fresh
environments: all installed constrained versions match and all node direct
requirements are present (`fresh-comparison.log`, `fresh-py39-comparison.log`).
piicodev's installed file metadata confirms it supplies PiicoDev_SSD1306.py.
No I2C/sensor/mixer module was exercised on hardware.

`bash -n install-dashboard.sh` and `git diff --check` passed. CI now consumes
requirements-dev.txt in both jobs, but remote GitHub Actions was not run.
Constraints cover the resolved macOS/Linux Python graphs, including conditional
Linux sysv_ipc and pre-3.11 toml/exceptiongroup pins; they are version constraints,
not hashes, an OS image lock or a compiler/interpreter lock. Actual Linux/Pi
binary builds and Python 3.13 execution were not run locally.

## Rig/image versions — explicitly unchecked

| Device | Python distributions | Current Pi OS image | Current Python | Pd/JACK package versions |
| --- | --- | --- | --- | --- |
| Finn Jet | unchecked | unchecked | unchecked | unchecked |
| Ciro Toast | unchecked | unchecked | unchecked | unchecked |

Neither device was contacted by SSH, tmux, OSC or another route. Existing
Trixie 64-bit Lite/Python 3.13.5 installation evidence in docs/INSTALL.md is
historical, not a current rig report. Bob's exact read-only package/OS/Pd/JACK
comparison command is documented in docs/INSTALL.md under Python dependency
pins. No rig, acoustic, peripheral or hardware compatibility claim is made.

## OS-upgrade decision

`os-upgrade-recommendation.md` recommends removing the installer-wide apt upgrade
as a separately approved change. install-device.sh and the manual apt upgrade
instructions remain unchanged. Python pinning does not freeze apt packages.

The authorized stitch is complete: fresh installs pass both tiers, the Python
floor is retained, rig data is recorded as unchecked with Bob's comparison
command, and the upgrade policy is a recommendation only.
