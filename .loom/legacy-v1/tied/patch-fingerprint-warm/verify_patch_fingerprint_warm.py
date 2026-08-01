"""Verify the patch-fingerprint warm resolves the run context across
process boundaries: warm cache -> real fingerprint, cold cache -> unknown,
mutated file -> unknown until re-warmed. Run with ~/.venvs/bopos/bin/python.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.abspath(os.path.dirname(__file__))


def repo_root():
    probe = HERE
    while probe != os.path.dirname(probe):
        if os.path.exists(os.path.join(probe, "tools", "simfleet.py")):
            return probe
        probe = os.path.dirname(probe)
    raise SystemExit("repo root not found by marker")


REPO = repo_root()
sys.path.insert(0, os.path.join(REPO, "python"))
import identity  # noqa: E402

FAILURES = []


def check(label, ok, detail=""):
    print(("[PASS] " if ok else "[FAIL] ") + label + ("" if ok else f" -- {detail}"))
    if not ok:
        FAILURES.append(label)


def fingerprint_in_subprocess(patches_dir, patch):
    """Run resolve via runcontext.generate in a *fresh* process, proving the
    persistent cache (not this process's memory) is what answers."""
    code = (
        "import json, sys; sys.path.insert(0, {python!r}); import runcontext; "
        "context = runcontext.generate({patch!r}, patches_dir={patches!r}); "
        "print(json.dumps(context))"
    ).format(python=os.path.join(REPO, "python"), patch=patch, patches=patches_dir)
    result = subprocess.run([sys.executable, "-c", code], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=60)
    if result.returncode != 0:
        raise SystemExit("runcontext subprocess failed: " + result.stderr.decode())
    return json.loads(result.stdout.decode())


def main():
    with tempfile.TemporaryDirectory() as temp:
        patches_dir = os.path.join(temp, "patches")
        patch_dir = os.path.join(patches_dir, "demo-fake")
        os.makedirs(os.path.join(patch_dir, "sub"))
        with open(os.path.join(patch_dir, "main.pd"), "w") as f:
            f.write("#N canvas 0 0 100 100 10;\n")
        with open(os.path.join(patch_dir, "sub", "voice.pd"), "w") as f:
            f.write("#N canvas 0 0 50 50 10;\n")

        # 1. Cold cache: a fresh process honestly answers unknown.
        context = fingerprint_in_subprocess(patches_dir, "demo-fake")
        check("cold cache resolves to unknown",
              context["patch_fingerprint"] == "unknown", repr(context))
        check("version is a non-empty string",
              isinstance(context["version"], str) and context["version"],
              repr(context))

        # 2. Warm the patches root the way bopos.py's background warm does,
        #    which persists patches/.hashcache.json.
        identity.warm_hash_cache(patches_dir)
        check("warm persisted a cache file",
              os.path.isfile(os.path.join(patches_dir, ".hashcache.json")))
        expected = identity.fingerprint(patch_dir)
        context = fingerprint_in_subprocess(patches_dir, "demo-fake")
        check("warmed cache resolves the real fingerprint in a fresh process",
              context["patch_fingerprint"] == expected,
              f"{context['patch_fingerprint']!r} != {expected!r}")

        # 3. Mutate a file: the stale signature must degrade to unknown
        #    (never a wrong fingerprint) until re-warmed.
        with open(os.path.join(patch_dir, "main.pd"), "w") as f:
            f.write("#N canvas 0 0 200 200 10;\n")
        context = fingerprint_in_subprocess(patches_dir, "demo-fake")
        check("mutated patch degrades to unknown",
              context["patch_fingerprint"] == "unknown", repr(context))
        identity.warm_hash_cache(patches_dir)
        rewarmed = fingerprint_in_subprocess(patches_dir, "demo-fake")
        check("re-warm resolves the new fingerprint",
              rewarmed["patch_fingerprint"] == identity.fingerprint(patch_dir)
              and rewarmed["patch_fingerprint"] != expected,
              repr(rewarmed))

        # 4. A missing patch stays unknown rather than the empty manifest.
        missing = fingerprint_in_subprocess(patches_dir, "no-such-patch")
        check("missing patch resolves to unknown",
              missing["patch_fingerprint"] == "unknown", repr(missing))

    # 5. Static wiring: bopos.py initialises and re-warms the patch cache.
    with open(os.path.join(REPO, "python", "bopos.py")) as f:
        source = f.read()
    check("bopos.py initialises the patch cache at startup",
          "initialise_patch_cache()" in source)
    check("bopos.py re-warms after patch-mutating verbs",
          source.count("warm_patch_cache()") >= 3, str(source.count("warm_patch_cache()")))
    check("installed_patches persists its hashes",
          "save_hash_cache(patches_dir)" in source)

    if FAILURES:
        raise SystemExit(f"{len(FAILURES)} check(s) failed")
    print("\npatch-fingerprint-warm checks passed")


if __name__ == "__main__":
    main()
