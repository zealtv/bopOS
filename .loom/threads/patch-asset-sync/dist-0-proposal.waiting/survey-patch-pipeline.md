# Survey: patch pipeline (subagent, 2026-07-13)

Facts gathered read-only by a Sonnet subagent; file:line references verified
against the working tree at time of survey.

## 1. Patch model on a device

- Patch = directory under `patches/<name>/`; active one in
  `patches/active_patch.txt` (`python/bopos.py:79-83`).
- Entry point is **not hard-coded to `main.pd`** — it comes from the manifest;
  `main.pd` is only the legacy/no-manifest fallback:
  - `patches/README.md:11-15` says "entry point is always `main.pd`" — README
    is **stale** relative to code.
  - `python/manifest.py:44-52`: `entrypoint` required, validated to exist;
    `engine` too (default `"pd"`).
  - `python/manifest.py:100-118` CLI: exit 0 valid → prints
    `ENGINE=`/`ENTRYPOINT=`; exit 3 no manifest but `main.pd` exists (silent
    legacy fallback); exit 1 invalid manifest (loud, still falls back).
  - `bash/start-engine.sh:12-19` evals that, defaults `pd`/`main.pd`.
- Manifest `bopos.patch.json` (`python/manifest.py:15`), validated fields:
  engine, entrypoint, params (role key rejected, `manifest.py:76-79`), caps,
  slots. `raw()` served verbatim via `/os/params`. Absent manifest → legacy
  fallback + "undeclared" dashboard badge; invalid → loud warning, legacy
  fallback, raw broken JSON still served for badging (contract §1 "never fall
  silent" outranks strict validation — `.loom/tied/patch-manifest/
  design-decisions.md:28-32`).
- **Two distinct `bopos.config`s** (naming collision flagged in
  `docs/HARDWARE.md:33-34`):
  - Patch-level `patches/<name>/bopos.config`: only documented key is
    `SAMPLEPACKSURL`, read by `bash/getsamples.sh:16`; getsamples errors and
    exits if absent.
  - Node-level `BOPOS_DIR/bopos.config`: `python/bopos.py:55-74` parses
    HB_TARGET, HB_RSSI, MIXER_CONTROL, UPDATE_MODEL, AUDIO_CHANNELS; absence
    → defaults, no error.
- `patches/<name>/start.sh` optional, run at engine start
  (`bash/start-engine.sh:105-109`).

## 2. How patches reach a device today (git only)

- `/os/addpatch <user> <repo>` (`python/bopos.py:912-959`): validates,
  `git ls-remote`, **rmtree existing `patches/<repo>`**, clones from GitHub.
  Warns if no `main.pd`. Does not switch/activate.
- `/os/patch <name>` (`bopos.py:876-909`): validates (manifest valid OR
  main.pd), writes active_patch.txt, stops engine, if patch dir has `.git` →
  `git pull --recurse-submodules`, then **reboots unconditionally**.
- `/os/pullpatch` (`bopos.py:961-969` → `bash/pull_active_patch.sh`):
  `git restore .` + pull in the active patch dir, then reboot.
- `/os/update` (`bopos.py:833-839` → `bash/update.sh`): **bopOS framework
  self-update** — git pull of the bopOS repo (preserving active_patch.txt),
  submodule update, reboot. Never touches a patch's own repo.
- `/os/checkout <branch>`: checkout bopOS branch then update.sh.
- All provisioning verbs reply `/os/rev <sha> <model>` (`bopos.py:567-593`).
- **Dashboard "Update All"** (`dashboard/static/index.html:8` →
  `dashboard.js:157` → `server.py:128-132` → `osc_bridge.py:200-205`):
  sends `/all/os/update` = framework self-update. Distinct from the Patch
  panel's Pull latest (`pullpatch`) / Switch (`patch`).

## 3. Dashboard patch UI today

- Patch section (`dashboard.js:120`): current patch from `d.report?.patch`;
  **Switch** = typed-name text input + confirm (`server.py:138-142`);
  **Pull latest** button (`server.py:148-151`); **Get samples** button
  (→ legacy `getsamples`); **Add from GitHub** = typed user/repo inputs
  (`server.py:143-147`).
- **No dropdown of available patches** — known gap, recorded in
  `.loom/tied/patch-and-install-mgmt/instructions.md:23-24`: "A patch-listing
  verb would be a contract addition."
- **No delete-patch affordance anywhere** (dashboard or bopos.py).
- Per-device and `all` targeting both supported.
- Actions section (`dashboard.js:121`): reboot, shutdown, restart-engine,
  update, get_samples, aloha; footer `Reboot All` / `Update All` /
  `Aloha All`.

## 4. Tied loom records

- `dashboard-4-patch-mgmt`: checklist only; split 2026-07-08.
- `patch-manifest`: built manifest.py, bopos.patch.json, generalized
  launcher, params/report members, loosened switch validation.
- `patch-and-install-mgmt`: built the Patch panel + venue save/load
  (`installations/<name>.json`); 9/9 PASS simfleet+Chromium. Not covered:
  real Pi git pull/reboot, real GitHub clone, broadcast switch on real fleet.

## 5. getsamples (legacy)

- `bash/getsamples.sh`: reads active patch, sources its `bopos.config` for
  `SAMPLEPACKSURL` (errors if missing), `gdown --fuzzy` to temp zip, unzips
  into `patches/<name>/bop/samplepacks`. Dead commented-out flattening code
  at lines 43-52.
- Wire: `/os/getsamples` (`bopos.py:841-847`, PROVISION_VERBS registration
  1017-1024); dashboard button translates `get_samples` → `getsamples`.
- Distinct from `/os/fetch` (§9) which lands in `~/bopOS/assets/<slot>/`;
  `start-engine.sh:44-64` symlinks legacy samplepacks into the new slot.
