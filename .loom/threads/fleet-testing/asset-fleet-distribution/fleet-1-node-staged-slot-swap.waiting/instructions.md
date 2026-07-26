# fleet-1-node-staged-slot-swap

**Waiting: optional hardening, parked 2026-07-15.** Bob accepted warn-only
live-slot updates for the first Assets workspace (11b). Claim this when the
warning proves insufficient in practice, or before any fleet work builds on
slot activation. It is independent of `fleet-0` and claimable ahead of it.

Make asset-slot convergence atomic on the node, removing the
partial-live-mutation hazard the 11b warning covers:

- Converge `/os/fetch <uri> <slot>` into a staging directory beside the slot
  (dot-prefixed, e.g. `assets/.staging-<slot>-*`), hardlinking files whose
  hashes already match the manifest from the installed slot so convergent
  skipping still avoids re-transfer, then verify and atomically swap with a
  backup, exactly the pattern `python/fetcher.py:_patch_fetch` already
  implements for patches (copy aside → converge → `os.replace` swap →
  backup cleanup/restore). This stitch is mostly "extend that pattern to
  asset slots", with hardlinks instead of `copytree` where possible.
- **No wire change:** contract §7 fixes WHAT (convergence); HOW is the
  node's. `/os/fetched` semantics, fingerprints, and the 11a inventory are
  unaffected — the fetch-time cache seeding must survive the swap (seed
  final paths, not staging paths).
- At measured pack scale (`.lore/items/2026-07-15-asset-transfer-scale-reference/`)
  the transient extra space is only the changed-file set when hardlinking;
  note actual behaviour in the stitch.
- Update the 11b warning copy once this lands: an in-place Update becomes an
  atomic swap, so the "mutates the live directory" warning shrinks to "files
  swap underneath a running engine at completion" (open handles keep old
  bytes; a restart or patch switch picks up the new generation).
- Verify with a focused non-browser verifier: interrupted fetch leaves the
  installed slot untouched; successful fetch swaps completely; hardlinked
  unchanged files are not re-downloaded; engine holding a file open during
  swap keeps playing.
