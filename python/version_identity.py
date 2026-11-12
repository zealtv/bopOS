# version_identity.py
"""
The framework's release version, and the git facts that sit beside it.

Release identity lives in the tracked ``VERSION`` file at the repository root
(``1.0.0``) plus a git tag ``v<VERSION>`` on the release commit. Exported
release commits get new hashes, so a git short hash cannot name a release; the
version can. This module answers, for one checkout:

    release   what VERSION says ("1.0.0"), or None when it is absent/invalid
    git_hash  the checkout's short hash (7 characters), or None without git
    state     how the two relate (table below)
    ahead     commits since the nearest release tag, when git can count them
    version   the string a person reads

    state     when                                        version
    --------  ------------------------------------------  ----------------------
    release   HEAD carries the tag v<VERSION>             1.0.0
    dev       git present, HEAD not at that tag           1.0.0+dev.12.gabc1234
                                                          1.0.0+dev.gabc1234 (no release tag reachable)
    export    VERSION present, no usable git checkout     1.0.0
    unknown   VERSION absent or malformed                 unknown

An export (a tarball, a copy without ``.git``) can only report what VERSION
says; it cannot tell a pristine release from a modified copy.

The framework version is deliberately separate from the OSC contract version,
the provision level, the project schema and the patch fingerprint. What
heartbeats and the Pd run context carry as ``version`` stays the git shorthand
(``git_short_hash``); only people-facing displays use ``resolve()["version"]``.

Standard library only, so the node, the launcher and the dashboard can all
import it.
"""

import json
import os
import re
import subprocess
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = "VERSION"
UNKNOWN = "unknown"
_RELEASE = re.compile(r"\d+\.\d+\.\d+")
_DESCRIBE = re.compile(r"v\d+\.\d+\.\d+.*-(\d+)-g[0-9a-f]+")


def _git(repo_dir, *args, timeout=3):
    """Stdout of a git command run in repo_dir, or None on any failure.

    Inherited GIT_* variables (a hook's GIT_DIR, GIT_INDEX_FILE) would point
    git at some other repository, so they are removed.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo_dir, env=env, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.decode(errors="replace").strip()


def _own_checkout(repo_dir):
    """True when repo_dir is itself a git work tree root, not a subfolder of one.

    An export dropped inside some other repository must not report that
    repository's hash as its own.
    """
    top = _git(repo_dir, "rev-parse", "--show-toplevel")
    return bool(top) and os.path.realpath(top) == os.path.realpath(repo_dir)


def read_release(repo_dir=None):
    """The release number in VERSION, or None when missing or malformed."""
    try:
        with open(os.path.join(repo_dir or REPO_DIR, VERSION_FILE)) as handle:
            text = handle.read().strip()
    except (OSError, UnicodeDecodeError):
        return None
    return text if _RELEASE.fullmatch(text) else None


def git_short_hash(repo_dir=None, length=None):
    """The checkout's git short hash, or None when there is no checkout.

    length=None keeps git's own default (at least 7), which is what heartbeats
    and the run context have always carried.
    """
    repo_dir = repo_dir or REPO_DIR
    if not _own_checkout(repo_dir):
        return None
    flag = "--short" if length is None else f"--short={int(length)}"
    value = _git(repo_dir, "rev-parse", flag, "HEAD")
    return value or None


def resolve(repo_dir=None):
    """Release identity of one checkout: a dict with release, git_hash,
    state, ahead and version (see the module docstring)."""
    repo_dir = repo_dir or REPO_DIR
    release = read_release(repo_dir)
    git_hash = git_short_hash(repo_dir, 7)
    ahead = None
    if release is None:
        state, version = "unknown", UNKNOWN
    elif git_hash is None:
        state, version = "export", release
    else:
        tags = (_git(repo_dir, "tag", "--points-at", "HEAD") or "").split()
        if f"v{release}" in tags:
            state, version, ahead = "release", release, 0
        else:
            state = "dev"
            described = _git(repo_dir, "describe", "--tags", "--long",
                             "--match", "v[0-9]*", "HEAD")
            match = _DESCRIBE.fullmatch(described or "")
            if match:
                ahead = int(match.group(1))
                version = f"{release}+dev.{ahead}.g{git_hash}"
            else:
                version = f"{release}+dev.g{git_hash}"
    return {"release": release, "git_hash": git_hash, "state": state,
            "ahead": ahead, "version": version}


def display_version(repo_dir=None):
    """The version string for a person: "1.0.0", "1.0.0+dev.12.gabc1234",
    or "unknown"."""
    return resolve(repo_dir)["version"]


def main(argv=None):
    """CLI: print the display version; --json prints the whole resolution."""
    argv = sys.argv[1:] if argv is None else argv
    info = resolve()
    print(json.dumps(info) if "--json" in argv else info["version"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
