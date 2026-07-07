# fetch-landing — verification (2026-07-08)

Loopback + scratch-tree proof; **not hardware-verified on a real Pi** and
the gdrive path was not run (needs gdown + a real SAMPLEPACKSURL — wrapped
unchanged, exit-code plumbed; the symlink makes it land in the assets root
by construction).

## Unit/integration suite

`test_fetch_landing.py` (this dir) — 17 checks, all passing (codex's
sandbox blocked its TCP listener; run by the orchestrator):

- safe_path traversal/absolute rejection; manifest validation matrix.
- Real local HTTP server: fresh fetch lands + hash-verifies; second fetch
  is a byte-for-byte no-op; changed file + refetch updates just it; a file
  dropped from the manifest is pruned.
- **Range resume**: server kills the connection mid-file on first attempt;
  fetcher retries with a Range header and completes; final sha256 correct.
- file: scheme sync + prune.
- helper `/os/fetch`: real worker thread fetches from the test server and
  replies `/os/fetched <slot> ok`; two identical concurrent requests
  coalesce to one download with two replies; `../evil` slot → immediate
  err, nothing touched.
- simfleet fetch member ok/err.

Regression: patch-manifest, assign-persistence, and dashboard suites all
still pass. (The dashboard suite needed a fix: it located the repo by a
fixed `../..` depth, which broke when the loom moved it into `tied/` —
now marker-based. Worth copying for future stitch tests.)

## Live loop — dashboard-served fetch on loopback

Dashboard with `--assets-dir <scratch>/assets-src` (slot `testpack`,
nested file included), real helper.py, listener on 5550:

1. `GET /assets/testpack/.manifest.json` → correct manifest (sha256+size,
   nested path, forward slashes).
2. `/all/os/fetch http://…/.manifest.json testpack` → `/os/fetched
   testpack ok` unicast; both files land under `$BOPOS_DIR/assets/testpack/`
   with matching sha256s.
3. Source changed (one file edited, one deleted) + refetch → slot
   converges: new bytes in place, removed file pruned, empty subdir gone,
   second ok reply.

## Launcher — scratch tree, fake pd/jackd

- Legacy `patches/default/bop/samplepacks` with content: contents adopted
  (moved) into `assets/samplepacks/`, dir replaced by symlink; second run
  leaves the symlink alone (idempotent).
- pd `-send` line now ends `; ASSETS <root>`; `BOPOS_ASSETS` exported (both
  captured from the fake binary's env/argv log).

## Not verified (needs Bob / hardware / real network)

- gdrive end-to-end (gdown venv lives on Pis).
- Fleet-scale HTTP over real WiFi (drop/resume behavior under actual loss —
  the resume mechanics are proven, the radio isn't).
- PD-side ASSETS consumption — patches adopt the new root as Bob touches
  them; the symlink keeps today's patches working meanwhile.
