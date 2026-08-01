#!/usr/bin/env python3
"""Run the amended real-browser transport regression for this spot-fix stitch."""

import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repo")
    REPO = parent

verifier = os.path.join(
    REPO, ".loom", "tied", "p3-global-transport-and-cue-lead",
    "verify_show_transport.py")
raise SystemExit(subprocess.run([sys.executable, verifier], cwd=REPO).returncode)
