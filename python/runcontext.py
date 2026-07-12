# runcontext.py
"""
Launch-time run context (engine-boundary ratification, 2026-07-12).

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

Patch name and assets root complete the delivered context; the launcher
already resolves those from `active_patch.txt` and the framework assets
slot, and hands them over in the same launch step.
"""

import random
import re
import sys
import time

SEED_SPAN = 1_000_000  # exclusive upper bound; keeps seeds exact as float32
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def generate(patch=None, now=None):
    """Return {"seed": int, "run_id": str} for one engine launch."""
    seed = random.randrange(SEED_SPAN)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    prefix = _SAFE.sub("-", str(patch)) + "-" if patch else ""
    return {"seed": seed, "run_id": f"{prefix}{stamp}-{seed:06d}"}


def main():
    """CLI for the launchers: prints eval-able BOPOS_SEED=/BOPOS_RUN_ID= lines.

    Usage: runcontext.py [patch-name]. Never fails over input: a missing or
    strange patch name degrades to a patch-less run id rather than silence.
    """
    patch = sys.argv[1] if len(sys.argv) > 1 else None
    context = generate(patch)
    print(f"BOPOS_SEED='{context['seed']}'")
    print(f"BOPOS_RUN_ID='{context['run_id']}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
