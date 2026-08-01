#!/usr/bin/env python3
"""Browser-free verify for launch-delivered version/patch-fingerprint context.

Exercises python/runcontext.py directly (no engine, no OSC) and sanity-checks
that every launcher wires the two new bopos-context items / env vars the same
way runcontext.py hands them back. Run with ~/.venvs/bopos/bin/python.
"""

import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
          " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


import identity  # noqa: E402
import runcontext  # noqa: E402


def generate_shape_checks():
    context = runcontext.generate("demo-pd")
    check("generate() still returns seed and run_id",
          "seed" in context and "run_id" in context, repr(context))
    check("generate() additionally returns version", "version" in context, repr(context))
    check("generate() additionally returns patch_fingerprint",
          "patch_fingerprint" in context, repr(context))
    check("version is a string", isinstance(context["version"], str), repr(context))
    check("patch_fingerprint is a string",
          isinstance(context["patch_fingerprint"], str), repr(context))


def version_matches_git_check():
    expected = subprocess.run(
        ["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()
    got = runcontext.resolve_version(REPO)
    check("resolve_version matches `git rev-parse --short HEAD`",
          got == expected, f"got {got!r} expected {expected!r}")


def version_unknown_outside_a_repo_check():
    with tempfile.TemporaryDirectory(prefix="bopos-runcontext-notgit-") as tmp:
        got = runcontext.resolve_version(tmp)
        check("resolve_version degrades to 'unknown' outside a git repo", got == "unknown", got)


def missing_patch_is_unknown_check():
    got = runcontext.resolve_patch_fingerprint(None)
    check("no patch path resolves to 'unknown'", got == "unknown", got)
    got = runcontext.resolve_patch_fingerprint("/does/not/exist/anywhere")
    check("nonexistent patch path resolves to 'unknown' (not the empty-manifest hash)",
          got == "unknown", got)


def cold_cache_never_hashes_and_warm_cache_resolves_check():
    with tempfile.TemporaryDirectory(prefix="bopos-runcontext-patch-") as tmp:
        patch_dir = os.path.join(tmp, "fake-patch")
        os.makedirs(patch_dir)
        with open(os.path.join(patch_dir, "main.pd"), "w") as target:
            target.write("#N canvas;\n")

        cold = runcontext.resolve_patch_fingerprint(patch_dir)
        check("an unwarmed cache degrades to 'unknown' rather than hashing", cold == "unknown", cold)

        # warming is what a background pass (as assets already do) would do;
        # launch itself must never trigger this synchronously
        identity.warm_hash_cache(patch_dir)
        warm = runcontext.resolve_patch_fingerprint(patch_dir)
        check("a warm cache resolves a real 64-hex fingerprint",
              isinstance(warm, str) and len(warm) == 64
              and re.fullmatch(r"[0-9a-f]{64}", warm) is not None, warm)
        check("the resolved fingerprint matches identity.fingerprint's direct hash",
              warm == identity.fingerprint(patch_dir), warm)


def strings_end_to_end_check():
    # PD floats are 32-bit (house rule) -- these must never look numeric.
    context = runcontext.generate("demo-pd")
    check("version never parses as a float",
          _not_floaty(context["version"]) or context["version"] == "unknown")
    check("patch_fingerprint never parses as a float",
          _not_floaty(context["patch_fingerprint"]))


def _not_floaty(value):
    try:
        float(value)
        return False
    except ValueError:
        return True


def audition_patches_dir_override_check():
    # audition.py's manifest may live outside <repo>/patches/<name>; generate()
    # must resolve fingerprints from the real directory the manifest names,
    # not always <repo>/patches/<name>.
    with tempfile.TemporaryDirectory(prefix="bopos-runcontext-audition-") as tmp:
        patch_dir = os.path.join(tmp, "outside-patches", "some-patch")
        os.makedirs(patch_dir)
        with open(os.path.join(patch_dir, "main.pd"), "w") as target:
            target.write("#N canvas;\n")
        identity.warm_hash_cache(patch_dir)
        context = runcontext.generate("some-patch",
                                      patches_dir=os.path.join(tmp, "outside-patches"))
        check("generate() honours an explicit patches_dir outside <repo>/patches",
              context["patch_fingerprint"] == identity.fingerprint(patch_dir),
              context["patch_fingerprint"])


LAUNCHERS = {
    "bash/start-engine.sh": [
        r"BOPOS_VERSION=\S*BOPOS_VERSION", r"BOPOS_PATCH_FINGERPRINT",
        r"bopos-context version \$BOPOS_VERSION",
        r"bopos-context patch-fingerprint \$BOPOS_PATCH_FINGERPRINT",
    ],
    "bash/start-laptop.sh": [
        r"bopos-context version \$BOPOS_VERSION",
        r"bopos-context patch-fingerprint \$BOPOS_PATCH_FINGERPRINT",
    ],
    "tools/perf_matrix.sh": [
        r"bopos-context version \$BOPOS_VERSION",
        r"bopos-context patch-fingerprint \$BOPOS_PATCH_FINGERPRINT",
    ],
}


def launcher_wiring_checks():
    for relative_path, patterns in LAUNCHERS.items():
        path = os.path.join(REPO, relative_path)
        try:
            text = open(path, encoding="utf-8").read()
        except OSError as error:
            check(f"{relative_path} readable", False, str(error))
            continue
        for pattern in patterns:
            check(f"{relative_path} wires {pattern}",
                  re.search(pattern, text) is not None)


def audition_wiring_check():
    text = open(os.path.join(REPO, "tools", "audition.py"), encoding="utf-8").read()
    check("audition.py PD startup sends bopos-context version",
          "bopos-context version {context['version']}" in text)
    check("audition.py PD startup sends bopos-context patch-fingerprint",
          "bopos-context patch-fingerprint {context['patch_fingerprint']}" in text)
    check("audition.py non-PD env carries BOPOS_VERSION",
          '"BOPOS_VERSION": context["version"]' in text)
    check("audition.py non-PD env carries BOPOS_PATCH_FINGERPRINT",
          '"BOPOS_PATCH_FINGERPRINT": context["patch_fingerprint"]' in text)


def simfleet_note_check():
    # simfleet answers the LAN wire (5550/6660) for N devices sharing one
    # process; it never launches an engine, so there is no launch-time
    # run-context step for it to mirror (the real bopos-context bus / env
    # vars only exist at engine launch, which the sim doesn't do). Assert
    # that fact stays true rather than silently going stale: no engine
    # subprocess launch or bopos-context wiring should appear in simfleet.py.
    text = open(os.path.join(REPO, "tools", "simfleet.py"), encoding="utf-8").read()
    check("simfleet.py still launches no engine process (run context has nothing to mirror)",
          "bopos-context" not in text and "subprocess.Popen" not in text
          and "subprocess.run" not in text)


def main():
    generate_shape_checks()
    version_matches_git_check()
    version_unknown_outside_a_repo_check()
    missing_patch_is_unknown_check()
    cold_cache_never_hashes_and_warm_cache_resolves_check()
    strings_end_to_end_check()
    audition_patches_dir_override_check()
    launcher_wiring_checks()
    audition_wiring_check()
    simfleet_note_check()
    total = 28
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
