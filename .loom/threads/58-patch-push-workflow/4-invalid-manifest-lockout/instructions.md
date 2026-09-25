# 4-invalid-manifest-lockout

**Status:** ready · node-side bash · independent of `1`–`3`
**Goal:** an invalid patch must not take the device off the network. It should
stay reachable and recover when a good patch is pushed — no SSH.

Evidence: `../incident-2026-08-05-ciro-toast.md` (restart counter 211).

## Today

- `bash/start-engine.sh` exits 1 when `python/manifest.py` rejects
  `bopos.patch.json`.
- `bash/start.sh` has `trap start_failed ERR`, which runs `stop.sh` over the
  **whole** stack — including `bopos.py` and the io bridge, which were already up
  and healthy.
- systemd restarts every 5 s, forever. The device is invisible, and patch
  distribution (the fix) needs it visible.

Tearing down a half-started stack is right in general. It's wrong for "this
patch is unusable", which is an ordinary operator mistake.

## Options (pick one, record why in `decisions.md`)

- **Fall back to `patches/demo-pd`** (always in git). Keeps audio; must report
  loudly that it's not the requested patch.
- **Run without an engine** and report the patch as failed. Most honest; the
  patch listing already has a `manifest: valid|invalid` column.
- **Narrow the `ERR` trap** so patch-scoped failures don't stop running
  services. Smallest diff; a genuinely half-started engine must still tear down.

## Must hold

1. After a manifest failure the device still heartbeats and answers `/admin`.
2. **Pushing a valid patch recovers it without SSH.** This is the point.

If the chosen approach makes "online but patch won't load" a normal state, check
whether `patch_badge` needs a word for it. Don't add one speculatively.

## Done when

- **Software:** simfleet doesn't model manifest validation — either add it (house
  rule: protocol behaviour lands in simfleet too) or write a shell harness that
  runs `start.sh` against an invalid patch dir.
- **Hardware:** on the Finn Jet / Ciro Toast rig, write a manifest with the
  retired `type` grammar, confirm the device stays visible and recovers via push.
  Don't claim this half unless it ran.

## Why it matters

`patches/` is gitignored — patches reach devices only by push, never by
`git pull`. A manifest hard break therefore leaves stale copies on devices for
months (it happened to Ciro Toast and Finn Jet). Nodes must fail soft.
