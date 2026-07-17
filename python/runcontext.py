# runcontext.py
"""
Launch-time run context (engine-boundary ratification, 2026-07-12; version/
patch-fingerprint additive per the 2026-07-17 patch-admin-surface amendment).

bopOS owns run-context generation: the launcher calls this module and
delivers the result atomically at engine launch — `-send` onto the
`bopos-context` bus for PD, environment variables for every other engine.
There is no OSC-at-boot race: an engine that starts has its context.

The context is:

- seed: an integer in [0, 999999]. Six significant figures at most, so it
  survives PD's 32-bit OSC/message floats exactly.
- run_id: an opaque identifier for this launch, safe as a PD symbol and in
  shell single quotes. It embeds a civil timestamp for humans reading logs;
  engines must not parse civil time out of it — the ratified civil-time
  request/event API is deliberately deferred and this string is not it.
- version: the node's git shorthand (what heartbeats already carry), or the
  literal string "unknown" when it cannot be resolved.
- patch_fingerprint: the active patch's canonical content fingerprint
  (contract sec 7, v1.4 sense) taken from the same nonblocking cache the
  asset inventory uses — launching must never block on hashing, so an
  unwarmed cache degrades to "unknown" rather than hashing synchronously.
  The literal string "unknown" when there is no patch path to resolve.

Both version and patch_fingerprint are strings end-to-end (PD's OSC floats
are 32-bit; contract sec 4.2, 12).

Patch name and assets root complete the delivered context; the launcher
already resolves those from `active_patch.txt` and the framework assets
slot, and hands them over in the same launch step.
"""

import os
import random
import re
import subprocess
import sys
import time

import identity

SEED_SPAN = 1_000_000  # exclusive upper bound; keeps seeds exact as float32
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_version(repo_dir=None):
    """Git shorthand for repo_dir (default the bopOS checkout), or "unknown"."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir or REPO_DIR, "rev-parse", "--short", "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            version = result.stdout.decode(errors="replace").strip()
            if version:
                return version
    except Exception:
        pass
    return "unknown"


def resolve_patch_fingerprint(patch_path):
    """Nonblocking: only a fully-warm identity cache answers; else "unknown".

    Never hashes file contents -- launching must not stall on a cold cache.
    bopos.py's background patch warm persists the cache this reads; a cold
    or stale cache still answers "unknown" honestly.
    """
    if not patch_path or not os.path.isdir(patch_path):
        # also guards a missing/misspelled patch: an empty walk would
        # otherwise fingerprint as the empty manifest, not "unknown"
        return "unknown"
    try:
        info = identity.cached_directory_info(patch_path)
    except OSError:
        return "unknown"
    if info["fingerprint"]:
        return info["fingerprint"]
    try:
        # In-process cache couldn't answer (the usual case in a fresh
        # launcher process): bopos.py persists patches/.hashcache.json
        # (background warm + /os/patches listings); loading it is
        # stat-only, never a hash.
        identity.load_hash_cache(os.path.dirname(os.path.abspath(patch_path)))
        info = identity.cached_directory_info(patch_path)
    except OSError:
        return "unknown"
    return info["fingerprint"] or "unknown"


def generate(patch=None, now=None, repo_dir=None, patches_dir=None):
    """Return the full launch-delivered run context for one engine launch."""
    seed = random.randrange(SEED_SPAN)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    prefix = _SAFE.sub("-", str(patch)) + "-" if patch else ""
    repo_dir = repo_dir or REPO_DIR
    patch_path = None
    if patch:
        patch_path = os.path.join(patches_dir or os.path.join(repo_dir, "patches"),
                                  str(patch))
    return {
        "seed": seed,
        "run_id": f"{prefix}{stamp}-{seed:06d}",
        "version": resolve_version(repo_dir),
        "patch_fingerprint": resolve_patch_fingerprint(patch_path),
    }


def main():
    """CLI for the launchers: prints eval-able BOPOS_*= lines.

    Usage: runcontext.py [patch-name]. Never fails over input: a missing or
    strange patch name degrades to a patch-less run id (and an "unknown"
    fingerprint) rather than silence.
    """
    patch = sys.argv[1] if len(sys.argv) > 1 else None
    context = generate(patch)
    print(f"BOPOS_SEED='{context['seed']}'")
    print(f"BOPOS_RUN_ID='{context['run_id']}'")
    print(f"BOPOS_VERSION='{context['version']}'")
    print(f"BOPOS_PATCH_FINGERPRINT='{context['patch_fingerprint']}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
