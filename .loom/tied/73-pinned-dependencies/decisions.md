# Pin provenance and boundaries

Use one root constraints.txt, loaded by every runtime/dev requirements entry
point. Pin the working host's runtime and test versions and their transitive
packages, not unrelated vulture tooling. requirements-dev.txt includes the
complete software-test stack (Playwright, Pillow, pyflakes); CI consumes it.
Dashboard requirements now include the already-installed pyOSC3 instead of an
unversioned extra installer argument.

The working venv is Python 3.14.7. Many packages require Python >=3.10, so pinning
that exact set unconditionally would break bopOS's Python 3.9 floor. Resolve and
freeze a compatible 3.9 set in scratch, choose it via Python-version markers,
and verify with an actual fresh Python 3.9.6 interpreter. Preserve the modern
working versions on Python >=3.10. Trixie's Python 3.13 uses that branch; no
actual 3.13/Pi install or binary build is claimed.

The working dashboard venv lacks the hardware-library distributions. Resolve
those exact versions in separate scratch environments, retain the provenance,
and label all rig package/peripheral compatibility unchecked. Include Linux's
conditional sysv_ipc and older Python's toml/exceptiongroup constraints, which
are not all installed by the modern macOS requirement graph. Optional laptop
hidapi is pinned; the old PiicoDev_SSD1306 module-name requirement is replaced
by the same piicodev distribution already required by nodes, which supplies
that module. No hardware module was exercised.

No rig was contacted, directly or indirectly. Record Pi OS/Pd/JACK versions as
unchecked rather than infer them from older records. docs/INSTALL.md supplies
Bob an exact read-only comparison command. Historical Trixie/Python 3.13.5 build
evidence is identified as historical, not a current version report.

Recommend dropping the installer's full apt-get upgrade only in
os-upgrade-recommendation.md. The script's upgrade policy and manual apt command
remain unchanged pending Bob. Python constraints do not freeze OS packages,
artifacts/hashes, compilers or interpreters. Intended package graphs are
macOS/Linux; there is no tested Windows-install claim.

Resolve environments: /tmp/bopos-pins-validation and /tmp/bopos-pins-py39.
Fresh verification environments: /tmp/bopos-pins-fresh and
/tmp/bopos-pins-fresh-py39. All are outside the repo. ~/.venvs/bopos was read
only for provenance; no install or upgrade was performed into it.
