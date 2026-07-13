# Survey: fetch / assets / templates (subagent, 2026-07-13)

Facts gathered read-only by a Sonnet subagent; file:line references verified
against the working tree at time of survey.

## 1. The `/os/fetch` contract (docs/OSC-CONTRACT.md §9)

- `docs/OSC-CONTRACT.md:405-419` — §9 "Distribution and landing":
  `/<id>/os/fetch <source-uri> <slot>` → `/os/fetched <slot> <ok|err>` (unicast)
- `docs/OSC-CONTRACT.md:411-413` — scheme dispatch: `http:` (fleet-scale —
  dashboard serves LAN HTTP with a files+hashes manifest, nodes pull by diff,
  Range-resume, works air-gapped), `gdrive:` (legacy ingest), `file:`.
- `docs/OSC-CONTRACT.md:414-419` — landing convention: framework-owned,
  engine-neutral root outside the patch git tree, `~/bopOS/assets/<slot>/`;
  handed to every engine at launch as run context (`bopos-context assets` for
  PD, `BOPOS_ASSETS` for other engines); legacy
  `patches/<active>/bop/samplepacks` symlinked into it for one release.

Tied stitch `.loom/tied/fetch-landing/`:
- Implemented for real: node-side worker-thread fetch queue in bopos.py,
  scheme dispatch module `python/fetcher.py` (stdlib-only), http/https
  manifest fetch + prune + Range-resume + sha256 verify, `file:` sync,
  `gdrive:` thin wrapper around unchanged `bash/getsamples.sh`, legacy
  samplepacks symlink adoption in the launcher, `ASSETS`/`BOPOS_ASSETS`
  handoff, dashboard `--assets-dir` static mount + dynamic `.manifest.json`
  route, simfleet `fetch` simulation member.
- `.loom/tied/fetch-landing/verification.md:53-59` — NOT hardware/real-network
  verified: gdrive end-to-end (needs gdown venv on Pis), fleet-scale HTTP over
  real WiFi under packet loss, and PD-side consumption of `ASSETS` (patches
  must be edited by Bob to read it; the symlink keeps old patches working).

## 2. Device-side fetch implementation

- `python/fetcher.py:1-192` — real implementations, not stubs:
  - `_http_fetch` (121-135) — JSON manifest, per-file sha256/size compare,
    `.part` download with Range resume (`_download`, 97-118, 3 attempts),
    atomic rename, prunes files not in manifest (`_prune`, 79-94).
  - `_file_fetch` (138-167) — same convergence semantics from a local dir.
  - `gdrive:` (182-189) — requires `slot == "samplepacks"`, shells out to
    `bash/getsamples.sh`, ok iff exit 0.
  - `parse_manifest`/`safe_path` (12-65) — strict: manifest is
    `{"files": [...]}` only, each file exactly `{path, size, sha256}`, path
    traversal/absolute rejected, slots `[A-Za-z0-9_-]+` (`_valid_slot`, 12-14).
- `python/bopos.py:288-331` — single background worker thread + queue;
  `queue_fetch` (320) coalesces identical `(uri, slot)` requests; worker calls
  `fetcher.fetch(uri, slot, os.path.join(BOPOS_DIR, "assets"))` and unicasts
  `/os/fetched` to every coalesced requester.
- `python/bopos.py:659-667` — LAN dispatch for `/os/fetch`, slot validated.
- Landing: `~/bopOS/assets/<slot>/` (`bopos.py:309`).
- Handoff: `bash/start-engine.sh:87` exports `BOPOS_ASSETS`; line 91 appends
  `bopos-context assets ...` to the PD `-send` bus. `bash/start-laptop.sh:49`
  equivalent for laptop rig.
- Legacy symlink: `bash/start-engine.sh:40-61` — adopts
  `patches/<active>/bop/samplepacks` into `assets/samplepacks/` (move only if
  slot side empty, never overwrites fetched content), replaces dir with
  symlink; warns and leaves alone if both sides have content.
  `bash/clearsamples.sh` and `bash/getsamples.sh` still operate on the legacy
  path (`getsamples.sh:23`).
- `samples-1-fetch-client` genuinely unstarted; node-side machinery it would
  consume already exists — the missing piece is dashboard UI triggering.

## 3. simfleet (tools/simfleet.py)

- Verbs handled: reboot (287), shutdown (290), restart-engine (293),
  update/checkout (296), patch (302), addpatch (307), pullpatch, getsamples
  (admin_verb chain ~559-561), ping (490), assign (496), identify (521),
  mute (524), master (532), params (540), **fetch (545-559)** — validates
  scheme/slot, schedules `/os/fetched <slot> ok|err` after 1s; protocol-level
  only, no actual download. report (564), probe (581).
- No patch-fetch/template verb beyond git-based patch/addpatch/pullpatch.

## 4. Templates and demo patches

- `templates/supercollider-bopos/`: `bopos.patch.json` (`engine: sclang`,
  `entrypoint: main.scd`, two facilitator params, `caps: []`, `slots: []`),
  `README.md`, `main.scd`. README workflow: "Copy this directory into
  `patches/<name>/`, select the patch, and bopOS launches it as
  `sclang patches/<name>/main.scd`." README documents the full provided-terms
  surface and run-context env vars, and instructs using `BOPOS_ASSETS` — the
  SC template is already written for the new assets model.
- `patches/default/`: `bopos.patch.json` (`engine: pd`, `entrypoint: main.pd`,
  `slots: ["samplepacks"]`), `bopos.config` (just
  `SAMPLEPACKSURL=<gdrive placeholder>` — the legacy gdrive config consumed by
  `bash/getsamples.sh`), `main.pd`, `start.sh` (trivial placeholder echo).
- Engine launch (`bash/start-engine.sh:14-19,88-98`):
  `python3 python/manifest.py <patch>` emits `ENGINE=`/`ENTRYPOINT=` (falls
  back to `pd`/`main.pd` on invalid manifest); `pd` gets the PD command line,
  anything else runs `"$ENGINE" "$PATCH_PATH/$ENTRYPOINT"` generically — no
  SC-specific launcher logic.

## 5. Dashboard asset/sample UI

- `dashboard/static/js/dashboard.js:120` — Patch section "Get samples" button
  (`data-action="get_samples"`); line 121 repeats it in the generic action
  list (`["reboot","shutdown","restart-engine","update","get_samples","aloha"]`).
- `dashboard/server.py:126-131` — ws `action` allow-list includes
  `get_samples`; `dashboard/osc_bridge.py:200-201` translates it to wire verb
  `getsamples` — **the legacy gdrive-only admin verb**, not `/os/fetch`.
- Dashboard fetch pieces from `fetch-landing` are serving-side only:
  `--assets-dir` static mount + `/assets/<slot>/.manifest.json` route
  (`dashboard/server.py:357-380`). No UI constructs an `/os/fetch` call.
- `dashboard/static/index.html:30` — the `cue / sample name` input is for
  `/cue`, unrelated to assets.

## 6. Run context (python/runcontext.py)

- `generate(patch=None, now=None)` returns `{"seed", "run_id"}` only.
  `seed` ≤6 sig figs (PD float safe); `run_id` opaque, embeds civil timestamp
  for log-reading only.
- Launcher sets the rest: `BOPOS_ACTIVEPATCH`, `BOPOS_ASSETS`,
  `BOPOS_ENGINE_PORT` (default 6661) in `bash/start-engine.sh`; PD receives
  `seed`/`run-id`/`patch`/`assets` on the `bopos-context` bus instead.

NOT FOUND: no `BOPOS_DIR` env var (bash local derived from script location,
`start-engine.sh:4`). No dashboard fleet-wide sync verb wired to `/os/fetch`.
