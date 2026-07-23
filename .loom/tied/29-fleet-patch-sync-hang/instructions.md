# 29-fleet-patch-sync-hang

**BUG.** A freshly-flashed Pi goes **unresponsive in the bopOS interface** when
you send it the fleet patch. It still answers SSH (Bob shut it down that way),
so the box is alive — but it stops appearing/responding in the Dashboard after a
patch send. Something in the patch-sync path hangs the node's OSC surface (or its
heartbeat), not the whole Pi.

Bob, 2026-07-23: "I have a recently flashed Raspberry Pi here. I've just flashed
bopOS to it and then when I tried to send the fleet patch to the device, the
device becomes unresponsive in the bopOS interface. I can still SSH into it to
shut it down, but there seems to be some sort of bug in the patch syncing."

## Why this is first

It blocks the one thing a new node has to do — receive its patch. Everything in
the fleet story assumes a flashed Pi can take a patch send. This jumps the queue.

## What we know / suspect

- Patch + asset fetch on the node is `python/fetcher.py` (`_http_fetch`, patch
  slot install). The Dashboard/relay push and the node heartbeat on 5550 are the
  surfaces that would go quiet if the fetch blocks the main loop or wedges a lock.
- Candidate causes to rule in/out during diagnosis: a blocking/long fetch on the
  thread that also services OSC; the asset-cache warm (`warm_asset_cache` /
  `identity.warm_hash_cache`) holding `asset_warm_lock` or thrashing a
  fresh/empty cache; a fetch that never returns (no timeout) against an
  unreachable source; a crash in `bopos.py` that drops the heartbeat while
  leaving SSH up.
- "Freshly flashed" is the tell — a clean node has no warmed asset cache and no
  prior patch, so first-sync-only state is the prime suspect.

## Shape of the work

`1-reproduce-diagnose` first — reproduce (dev Pi `bop000`, and/or a fresh
simfleet node) and pin the exact hang. Name the fix stitch (`2-fix`) from what
diagnosis finds; don't guess the fix before we know the cause. If the fix turns
out to need a PD-side receiver change, that is Bob's domain — record it in
`.notes/pd-edits-for-bob.md` and note the dependency here.

## Constraints

- New protocol behaviour lands in `tools/simfleet.py` in the same stitch.
- Ship a regression guard that would have caught this (a fresh-node patch-send
  that keeps the heartbeat/OSC surface alive).
