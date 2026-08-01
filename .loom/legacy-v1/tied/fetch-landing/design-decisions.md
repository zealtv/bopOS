# fetch-landing — design decisions (2026-07-08)

Contract §9. Coordinates with `sample-distribution` (fleet UI is theirs;
the verb, the fetch engine, the landing convention, and the dashboard's
serving endpoint are ours — they'll build "sync samples" buttons on top).

## 1. The verb, node side

`/<sel>/os/fetch <source-uri> <slot>` handled in helper.py's LAN listener
(6660). Downloads are slow and the listener must keep answering ping/mute,
so fetches run on a **single background worker thread** with a queue;
requests are coalesced while an identical (uri, slot) is queued or running
(re-sending is safe — idempotent full-state law; a dashboard retry must not
start a second download). Reply `/os/fetched <slot> <ok|err>` unicast to
(requester, 5550) on completion — every requester of a coalesced fetch gets
a reply. `slot` must match `[A-Za-z0-9_-]+`; anything else replies err
without touching the filesystem.

## 2. Landing root

`$BOPOS_DIR/assets/<slot>/` (BOPOS_DIR *is* ~/bopOS on Pis). `/assets/` goes
in .gitignore. The slot's content **converges to the manifest**: files not
in the fetched manifest are deleted from the slot (a fetch is a convergence
assertion, §7's spirit — not an additive copy). Only http-scheme fetches
prune; gdrive/file land whatever they land.

## 3. Scheme dispatch (python/fetcher.py, stdlib urllib only — no pip deps
on nodes)

- **`http:`/`https:`** — the URI points at a manifest JSON:
  `{"files": [{"path": <relative>, "size": <n>, "sha256": <hex>}]}`.
  File URLs resolve **relative to the manifest URL** (urljoin), so one
  static tree serves both. Per file: local sha256 match → skip;
  mismatch/missing → download to `<name>.part` (Range resume if a .part
  exists), verify sha256, atomic rename into place; up to 3 attempts per
  file, resuming from the .part each time. Then prune (see §2). ok iff
  every file verified. Paths are sanitized (no absolute, no `..`).
- **`gdrive:`** — wraps today's `bash/getsamples.sh` unchanged. It writes
  to `patches/<active>/bop/samplepacks`, which §4 makes a symlink into the
  assets root — the legacy pipeline lands in the new convention without
  editing the script. The URI's payload after `gdrive:` is ignored (the
  script reads SAMPLEPACKSURL from the patch's bopos.config, as today);
  the slot should be `samplepacks`. ok/err from the exit code.
- **`file:<path>`** — sync the slot from a local directory (copy new/
  changed by sha256, prune). For the laptop rig and tests.

## 4. Legacy symlink (start-engine.sh, one release, contract §13)

At engine start, for the active patch: if `patches/<active>/bop/samplepacks`
is a real directory, adopt its contents into `assets/samplepacks/` (move,
only when the slot side is empty — never overwrite fetched content), then
replace the dir with a symlink to the slot; if the path doesn't exist,
create parent + symlink. If both sides have content, leave the patch dir
alone and warn loudly — never destroy sample data. Idempotent: an existing
correct symlink is left as is.

## 5. ASSETS handoff (start-engine.sh)

§9 sanctions extending the startup sends: append `; ASSETS <root>` to the
existing pd `-send` list and export `BOPOS_ASSETS=<root>` for every engine
(pd included — harmless, uniform). `<root>` is `$BOPOS_DIR/assets`, engines
join their slot themselves.

## 6. Dashboard serving (the fleet-scale source)

dashboard/server.py gains `--assets-dir` (default `dashboard/assets`,
gitignored): static mount at `/assets/…` plus a dynamic route
`GET /assets/<slot>/.manifest.json` that walks the slot dir and emits the
§3 manifest (sha256, size; hashes cached by (path, mtime, size)). So the
fetch URI for a dashboard-served slot is
`http://<dash>:8080/assets/<slot>/.manifest.json` — works air-gapped.
Triggering fetches fleet-wide from the UI is sample-distribution's stitch,
not this one; `/os/fetch` can already be sent by anything that speaks OSC.

## 7. simfleet

`fetch` member in receive_contract: log `fetch <uri> <slot>`, then after a
short scheduled delay unicast `/os/fetched <slot> ok` (err for a
non-http/gdrive/file scheme or bad slot name) to the requester. Sim devices
don't actually download — protocol-level truth only.

## Out of scope (parked where)

- Fleet sync UI, per-device progress display → sample-distribution +
  dashboard-4.
- Laptop acquiring packs from the cloud (`getsamples` on the laptop) →
  unchanged, sample-distribution's concern.
- PD reading ASSETS (patch-side use of the new root) → patches adopt it as
  Bob touches them; the symlink keeps today's patches working.
