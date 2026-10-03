# Git patch-route retirement — proposal for Bob

Drafted 2026-10-03 against contract **1.18** and accepted commit `9af7af1`.
**Awaiting Bob's approval of the amendment and existing-clone decision.**
Bob's instruction to remove the route is recorded in `instructions.md`; it
does not substitute for approval of this exact wire amendment. Phase 1 changes
only this proposal and the stitch's claim. No code, contract or `.pd` file is
changed. Phase 2 follows the ruling, implements it, and runs fast and browser
verification before tying the stitch.

## Decision proposed for existing device clones

**Yes: a dashboard push overwrites an existing cloned patch directory,
including removing its local `.git` directory or `.git` file.** There is one
deployment route, using the existing `/os/fetch` `patch:<name>` slot; there is
no Git mode, compatibility alias, migration command or new receipt shape.

Removing the route does not proactively delete installed patches or metadata.
An existing clone remains an installed directory and can be selected with
`/os/patch`; selection uses its validated installed bytes without contacting
its remote. Its next actual push converges to the host's distributable bytes,
prunes obsolete files and removes the clone's metadata. A matching content
fingerprint may still let fleet convergence skip an unnecessary transfer;
that does not require a metadata-only push or sweep.

Converge and validate in staging, then replace the destination using the
existing backup/rollback flow. Never delete `.git` in the live destination
before validating the replacement. A failed fetch or validation keeps the old
bytes and metadata; a failed replacement restores them. A `.git` file is
removed locally, without following its `gitdir:` pointer or deleting any
external repository. Existing traversal and symlink rejection stays in force,
including symlinks inside an old clone; conversion does not bypass those
guards. Active-patch transfers retain the existing stop/converge/restart
sequence and dashboard confirmation.

This is the smallest consistent choice: treating a formerly cloned directory
as ordinary installed content avoids retaining a hidden second mode or a
permanent deployment lockout. Composer Git repositories on the host remain
allowed; their dot entries are excluded from distribution and fingerprints.

## Exact proposed contract amendment

The following text is for landing **after approval**. Other contract text,
including earlier §15 entries, remains unchanged. §4.2 and §9 changes are
necessary companions to §7: otherwise the contract would still allow the
engine Git action and require rejection of an existing clone.

### Header — replace the opening version paragraph

```markdown
**Version 1.19** — base ratified 2026-07-07; latest revision 2026-10-03. The
complete amendment record, with provenance for every revision, is in
[§15 Revision history](#15-revision-history).
```

The draft uses today's date; if ratification occurs later, the header and new
§15 row must use the actual ratification date together.

### §7 — replace the complete section

```markdown
## 7. Admin and convergence (`/os/*` verbs)

Lifecycle verbs always mean one thing: `/os/reboot`, `/os/shutdown`,
`/os/restart-engine` (targeted; replaces pkill-everything — `stop.sh`'s
`pkill python` is retired).

Provisioning verbs are **convergence assertions**, not filesystem operations —
WHAT is fixed by the contract, HOW is chosen by the node's `update_model`:

- `/os/updatebopos` updates the bopOS framework only — persistent: git pull +
  reboot (today's behaviour). Ephemeral: re-fetch the mutable layer and re-exec,
  or honestly no-op. The old `/os/update` spelling has no alias.
- `/os/checkout <branch>` selects and converges the bopOS framework branch;
  it does not update patches.
- `/os/patch <name>` keeps the OS and helper online: stop the current engine
  stack, select the validated installed patch, launch its engine, then send the
  provisioning receipt. It uses the installed bytes without a Git pull and
  never reboots the device.
- Patches reach devices through dashboard push using `/os/fetch` with a
  `patch:<name>` slot (§9). `/os/addpatch` and `/os/pullpatch` are removed;
  there are no aliases or compatibility handlers.
- `/<id>/os/patches` → `/os/patches <json>` (unicast) lists installed
  patches as objects `{name, active, manifest}`. The two flags are
  booleans; `manifest` means `bopos.patch.json` is present and valid.
  The former `git` field is removed; patches have no Git deployment mode.
  Each entry may also carry `fingerprint` (v1.4, additive): the 64-hex
  sha256 of the canonical directory-manifest JSON — identical to the host
  catalog fingerprint for the same bytes (dot-entries, symlinks, and `.part`
  files excluded from the walk). Absent from pre-v1.4 nodes, and from an
  entry whose content cannot be read; every consumer tolerates absence.
- `/<id>/os/assets` → `/os/assets <json>` (unicast) lists installed asset
  slots as objects `{name, fingerprint, files, bytes}`. `name` is a top-level
  non-dot, non-symlink directory under `~/bopOS/assets/`; `files` and `bytes`
  are fresh counts from the canonical manifest walk, excluding dot entries,
  symlinks, and `.part` files. `fingerprint` is the same canonical
  directory-manifest sha256 used by the host catalog, or JSON `null` while the
  node's nonblocking stat-signature cache is still warming. An empty list means
  no installed slots; no reply means inventory unknown. The query path never
  hashes file contents synchronously.
- `/os/droppatch <name>` removes an inactive patch and refuses the active
  patch. `/os/dropassets <slot>` removes an asset slot.
- **Every provisioning verb replies** `/os/rev <sha> <model> <uid> [<status>
  <phase>]` (unicast; uid additive in v1.5, optional outcome additive in v1.6)
  so the dashboard observes attributable convergence, not fire-and-forget.
  `status` is `ok` or `err`; `phase` is a short machine-readable token such as
  `pull`, `authorization`, `converged`, or `reboot`. An `updatebopos` success
  receipt is sent before requesting reboot; a rejected reboot produces a
  second `err reboot` receipt. This includes both
  drop verbs; `/os/patches` is a query and replies with its listing instead.
- `/os/getsamples` is removed. Assets use `/os/fetch`; there is no alias.
```

### §4.2 — replace the `/admin` entry in the engine-sent code block

```text
/admin <action>                bounded admin request (v1.7, additive);
                               action ∈ {update-bopos, shutdown, reboot}
                               — routes to the node's existing framework
                               update, shutdown and reboot behaviour (the
                               same code paths the dashboard verbs use in
                               python/bopos.py). No selector, no reply to the
                               engine — these actions are terminal or
                               restart the engine anyway; outcome receipts
                               continue to flow to the LAN model where
                               applicable (§7). Unknown actions, including
                               the removed update-patch action (v1.19), are
                               ignored with a logged warning, never fatal.
```

### §9 — replace the asset-location phrase and patch-landing bullet

In the asset-landing bullet, replace `outside the patch git tree` with
`outside the patch directory`. The path and all remaining asset rules stay.
Replace the patch-landing bullet with:

```markdown
- **Patch landing convention:** `patch:<name>` lands in
  `~/bopOS/patches/<name>/` with the same diff, resume, hash-verification and
  prune-to-manifest convergence semantics as an asset slot. An existing
  Git-cloned patch directory is treated as ordinary installed content:
  a successful fetch replaces its bytes with the host's distributable content
  and removes its local `.git` directory or `.git` file. A `.git` file's
  external target is not followed or removed. The replacement is converged and
  manifest-validated in staging before installation; fetch or validation
  failure preserves the existing directory, including its Git metadata, and
  installation failure restores it. Existing path and symlink safety checks
  still apply. Git metadata is not distributed from the host.
```

The following active-patch stop/converge/restart and confirmation bullet is
unchanged. `/os/fetch-progress`, `/os/fetched`, `/os/rev`, selectors, ports,
asset behavior and fingerprint grammar do not change.

### §15 — append this row, preserving all prior history

```markdown
| 1.19 | 2026-10-03 | Retire the Git patch-deployment route (§4.2, §7, §9): remove `/os/addpatch`, `/os/pullpatch`, the engine `/admin update-patch` action and the `git` patch-inventory field, with no aliases or compatibility handlers. Patch selection uses installed bytes without a Git pull. Dashboard push through `/os/fetch` is the sole deployment route; a successful push converts an existing clone to ordinary installed content, removing its local Git metadata through staged, validated replacement with rollback on failure. Framework Git update, checkout and revision reporting are unchanged. | stitch `68-remove-git-patch-route`, `proposal.md` and Bob's ratification ruling |
```

Update the central `python/osc_contract.py` version to `1.19` in Phase 2 with
the approved contract; do not add another version source. `docs/PORTS.md`
requires no amendment.

## Removal inventory for Phase 2

| Surface | Exact removal or associated adjustment |
| --- | --- |
| Node LAN provisioning, `python/bopos.py` | Remove `addpatch` and `pullpatch` from `PROVISION_VERBS`; remove `add_patch_callback`, `pull_active_patch_callback`, `_PULL_ACTIVE_PATCH_PHASES`, their GitHub lookup/clone, `/addpatch <repo>` engine notification, pull-script execution, route-specific receipt phases and reboot path. No compatibility dispatch. |
| Engine admin, `python/bopos.py` | Remove `update-patch` from `ENGINE_ADMIN_VERBS`; retain the existing logged-and-ignored unknown-action behavior. Adjust the four-action comment. |
| Installed patch selection, `python/bopos.py` | Remove the `.git`-conditioned `git pull --recurse-submodules` block in `switch_patch_callback` and its Git-specific cache warm; retain manifest validation, installed selection, engine lifecycle/rollback and existing switch notification. |
| Node fetch worker, `python/bopos.py` | Remove `git_managed` detection and refusal, and the `not git_managed` restriction on active-patch engine restart. Keep the normal fetch serialization and stop/restart paths. |
| Fetch landing, `python/fetcher.py` | Remove the `.git` refusal in `_landing`; retain name, containment and symlink checks. Existing `_patch_fetch` staging plus `_prune` provides conversion to the host manifest and metadata removal; verify it through the public route after removing the guard. |
| Node inventory, `python/bopos.py` | Remove `git` from each `/os/patches` object and update the Git-installation comment. Keep installed-name discovery, active/manifest facts and fingerprints. |
| Shell | Delete `bash/pull_active_patch.sh` in full, including patch `git restore`/pull and hard-coded Pi ownership adjustment. |
| Dashboard WebSocket handlers, `dashboard/server.py` | Remove `add_patch` / `pull_patch` mutation names and branches, including their argument handling, active-Git test and OSC sends. |
| Dashboard convergence, `dashboard/server.py` | Remove the Git-target skip in the distribution handler (`device_patch(..., git=True)`) and `entry.get("git")` skip in `converge_fleet_patch`. Remove the now-unused `git` filter argument from `device_patch`. Keep matching-fingerprint fast paths, per-device/fleet generations, receipts and confirm gates. |
| Dashboard inventory, `dashboard/osc_bridge.py` | Remove the `git` projection from the patch-listing cleaner; do not retain a false-valued compatibility field. |
| Dashboard UI, `dashboard/static/js/dashboard.js` | Remove the Pull latest button, `patch-pull` binding, reboot confirmation and `pull_patch` send; remove the ◆ marker, Git/host source column and patch-source description from diagnostics. Adjust empty-row colspan. Retain the existing Manifest / framework git label and framework SHA, remaining diagnostics and remediation. No new operator wording or controls are needed. |
| Dashboard CSS, `dashboard/static/css/style.css` | Remove unused `.git-add` and `.git-badge` selectors; retain `.invalid-badge` styling. No active add-patch form was found. |
| Fleet simulator, `tools/simfleet.py` | Remove `addpatch` / `pullpatch` dispatch and simulated admin outcomes from both allowlists and `admin_verb`; remove engine `update-patch`, fixture/storage/listing `git` flags and the `git_target` fetch rejection. Simulated fetch follows the one deployment path. Keep framework versions and updates. |
| Audition simulator, `tools/audition.py` | Remove the two `git: False` inventory fields. Search found no Git patch verb implementations here; retain framework `git_rev` reporting. |
| Tests | Replace the Git-refusal portion of `tests/test_fetcher.py` with successful clone conversion and failure-preservation regressions, preserving unsafe-path/symlink coverage. Remove the retired `pullpatch` routing assertion from `tests/test_device_control_routing.py` while retaining coverage with supported execution administration. Remove obsolete patch `git` fields in `tests/verify_device_control_modes.py` and `tests/verify_log_destination.py`; extend relevant browser coverage to show ordinary diagnostics with no Pull latest/source column. Add simple route/inventory absence checks where useful. |
| Current wire docs | Land the approved contract text and version. Remove retired routes, clone/pull phases, engine notification/action, sample command and receipt-list references from `docs/OSC-REFERENCE.md`; describe ordinary patch fetching without the Git split. Keep historical §15 records. |
| Composer/dashboard docs | Remove device Git deployment instructions, refusal claims and UI descriptions from `docs/COMPOSING.md`, `patches/README.md` and `dashboard/README.md`. Keep optional host authoring with Git and framework administration docs. `docs/ARCHITECTURE.md` already describes host-mirrored distribution and needs no second mode. |
| Current guidance | Refresh relevant `.glean` guidance/version after implementation if it describes the retired route; preserve immutable lore and historical loom records. |

## Confirmed framework-only Git surfaces that stay

- `python/io/sys_info.py`: `_repo_root()` resolves two levels above this file
  to the bopOS framework root. `get_git_rev()` runs `git -C <that root>
  rev-parse --short HEAD`. `get_active_patch()` reads only the selection file;
  it does not inspect the patch repository. Keep this module unchanged.
- `python/runcontext.py`: `REPO_DIR` is the framework root; `generate()`
  resolves `version` using that root (or its explicit framework `repo_dir`
  override), separately from `patch_path`. The CLI uses the framework default.
  Patch identity comes from `identity.cached_directory_info`, not Git. Keep
  revision resolution, context `version` and content fingerprint unchanged.
- Keep `python/bopos.py` framework revision reporting, `updatebopos`,
  `checkout`, `converge_framework` and their framework-only Git subprocesses.
  Keep dashboard framework revision resolution, report `git_rev`, simulator
  framework versions and all framework install/update workflows.
- Keep canonical dot-entry exclusions and the `.git` noise fixture in
  `tests/test_identity_fingerprint.py`: it proves host Git metadata is outside
  content identity, independently of the retired device deployment route.
- Keep Git used by repository tooling and `tests/test_commit_gate.py`.
  No `.pd` file changes and no device contact are needed for this proposal.

## Investigation and Phase 2 verification

Read-only searches covered tracked current sources/docs and the stitch, using
the retirement identifiers, Git flags, `.git` guards and UI labels. They also
found the two READMEs beyond the initial stitch's named docs. Examined the
fetcher's landing, full destination copy, prune, manifest validation and
backup/replacement flow, plus both framework revision implementations.

A disposable stdlib harness under `/tmp` called the unchanged internal
`fetcher._patch_fetch` with `file:` sources, deliberately bypassing only the
public `_landing` Git guard to inspect downstream behavior. All three checks
passed: a nonempty `.git` directory was pruned on successful replacement; a
`.git` pointer file was pruned without following its pointer; and an invalid
replacement manifest left the old payload and `.git/config` intact. This is
evidence for the decision, **not** proof that the still-gated public route is
already converted. Temporary directories were automatically cleaned up.

After approval, regression tests must exercise the public `fetch` route with
directory and file metadata, obsolete-byte pruning, invalid-source rollback,
and replacement-failure rollback; preserve symlink/traversal rejection. Verify
active-clone engine stop/restart and no Git subprocess on patch selection,
absence of retired handlers/actions/inventory fields, and the browser's normal
push/remediation flow without Git UI. Run `tools/run-tests.sh fast` and
`tools/run-tests.sh browser`, and search for retired identifiers so only the
explicit retirement contract text and historical records retain references.
No hardware claims are made in Phase 1.
