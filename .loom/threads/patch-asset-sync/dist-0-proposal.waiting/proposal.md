# Proposal: unified patch + asset distribution (dist-0)

**Status: awaiting Bob's ratification.** From the `patch-asset-sync` thread;
source is Bob's 2026-07-13 brain dump
(`.lore/items/2026-07-13-composer-experience-brain-dump`). Facts below come
from two code surveys in the stitch dir (`survey-patch-pipeline.md`,
`survey-fetch-assets-templates.md`) — every claim about current behaviour has
a file:line there.

## 1. The model in one paragraph

The bopOS checkout on the conducting computer is the source of truth. A
composer authors a patch as a folder in `patches/` (so PD externals and the
provided-terms surface just work) and puts media in folders under `assets/`.
The device's `patches/` and `assets/` **mirror the host's**: the dashboard
sends a patch or an asset folder to any/all devices, and sending converges
the device copy to the host copy — overwrite, delete-extras, resumable,
verified. Git remains available underneath for composers who want it (a
git-repo patch can update itself with just an internet connection), but no
composer is ever required to touch git.

## 2. What already exists (the good news)

The hard part is built and tied. The §9 fetch machinery
(`python/fetcher.py` + the worker queue in `bopos.py`) already does exactly
Bob's "send" semantics: manifest of files+hashes, download only what
changed, Range-resume, sha256 verify, **prune files not in the manifest**
(= "overwrite the existing directory"), idempotent. The dashboard already
serves an assets directory over LAN HTTP with the manifest route. simfleet
already simulates the verb. What's missing is: (a) the same mechanism
pointed at *patches*, (b) any dashboard UI that triggers it, and (c) the
listing/naming layer. Nothing here needs a new transport.

## 3. Proposed contract amendments (additive, v1.3)

### 3.1 Patch mirroring rides `/os/fetch`

Extend the slot grammar with one prefix:

```
/<id>/os/fetch <source-uri> <slot>            (unchanged — assets)
/<id>/os/fetch <source-uri> patch:<name>      (new — lands in patches/<name>/)
```

Reply is unchanged: `/os/fetched <slot|patch:name> <ok|err>`. Same
convergence semantics, different landing root. Two safety rules:

- **Refuse (err) if `patches/<name>/.git` exists.** A device patch is either
  git-managed (addpatch/pullpatch, updates itself from its remote) or
  host-mirrored (fetch, converges to the host copy) — never both. This keeps
  prune from eating a `.git` dir and keeps the two update stories from
  fighting.
- **Refuse (err) if `<name>` is the active patch and the engine is running**,
  unless we decide fetch-then-restart-engine is wanted (open question Q4).

### 3.2 Patch listing and removal (enables the dropdown)

```
/<id>/os/patches      →  /os/patches <json>      (unicast)
/<id>/os/droppatch <name>                        (refuses the active patch)
```

The JSON is a list of `{name, active, git, manifest}` (booleans; `manifest`
= has a valid `bopos.patch.json`). This is the contract addition
`patch-and-install-mgmt` already flagged as needed. `droppatch` replies
`/os/rev` like other provisioning verbs, so the dashboard observes it.

### 3.3 Nothing else changes on the wire

`addpatch`/`pullpatch`/`patch`/`update` keep their meanings. Bob's "device
updates its patch with only an internet connection" is already true today:
`/os/pullpatch` does a git pull inside the active patch dir — the device
needs internet, not the dashboard's file serving.

## 4. Host-side layout

```
bopOS/
  patches/          # one folder per patch; authoring happens here
    demo-pd/        # the demo PD patch (today's "default", renamed)
    demo-sc/        # the demo SC patch (today's templates/supercollider-bopos)
    <composer's>/   # may or may not be a git repo — bopOS doesn't care
  assets/           # one folder per asset set; what "Send assets" offers
```

- **`templates/` dissolves.** The SC starter's own README already says "copy
  this into `patches/<name>/`" — it becomes `patches/demo-sc` and is simply
  *there*, launchable, copyable. `patches/default` becomes `patches/demo-pd`
  (dir rename only; `main.pd` content stays Bob's). This supersedes the
  2026-07-08 "template lives in `templates/`" ruling — flagged for explicit
  re-ratification here.
- Composer patches under `patches/` that are their own git repos are ignored
  by the bopOS repo (gitignore all of `patches/*` except the demos, ditto
  `assets/*`) so composer work never tangles with framework git state.

## 5. What dies

- **Patch-level `bopos.config` is retired.** Its only key is
  `SAMPLEPACKSURL` for the legacy gdrive path. Media acquisition onto the
  *host* is the composer's business (drag files into `assets/<dir>/`);
  host→device is the mirror. This also dissolves the config naming collision
  with the node-level `bopos.config` that `docs/HARDWARE.md` flags. The
  `gdrive:` fetch scheme stays one release as legacy ingest.
- **`getsamples` leaves the UI.** The verb survives one release for deployed
  fleets (contract §13 migration discipline) but the dashboard button goes.
- **`main.pd` as a requirement is already dead** — the manifest's
  `entrypoint` field is ratified (§8) and implemented; `main.pd` is only the
  no-manifest legacy fallback. Ruling requested: a *new* patch must ship
  `bopos.patch.json` (the demos model it), the fallback stays for deployed
  legacy patches one release, and `patches/README.md` (stale — still says
  "always main.pd") gets rewritten.

## 6. Dashboard surface (naming rulings requested)

| Today | Proposed | Scope |
|---|---|---|
| Get samples | **Send assets** — pick a dir under `assets/`, per device / all | fires `/os/fetch http://<dash>/assets/<dir> <dir>` |
| (nothing) | **Send patch** — pick a dir under `patches/`, per device / all | fires `/os/fetch http://<dash>/patches/<name> patch:<name>` |
| (nothing) | **Sync all** — every patch + asset dir to selection | iterates the above |
| Switch (typed name) | **dropdown** from `/os/patches`, plus delete (confirm-gated → `droppatch`) | |
| Update All | **Update bopOS (all)** — same verb, honest label | framework self-update, which is all it ever did |
| Pull latest | unchanged, shown only for git patches (`git` flag from `/os/patches`) | |

"Send" is recommended over "Sync" for the per-item actions because the
gesture is directional (host → device) even though the wire is a fetch; the
one aggregate action is "Sync all". Asset dirs list with metadata Bob asked
for: file count, total size, last-modified (host-side stat; device-side
state is the hash comparison the manifest already gives us, so in-sync /
stale per device can render on the cards).

## 7. Effect on existing loom work

- **`samples-0-backend-manifest`** — *mostly already built* by
  `fetch-landing` (serving side exists); what remains (per-pack version
  display) folds into the implementation children below. **Drop.**
- **`samples-1-fetch-client`** — *already built* (`fetcher.py` is real and
  tested); its one live remainder, fetch **progress observability**, moves
  into the implementation children. **Drop.**
- **`samples-2-fleet-ui`** — superseded by the Send/Sync UI above. **Drop.**
- **`friction-0-docs`** — unblocks on ratification; the composer doc teaches:
  make a folder in `patches/`, copy a demo, edit, Send. No git chapter.
- **`friction-1-starter-kit`** — reshaped: the "starter kit" *is* the demo
  patches; the stitch reduces to demo polish + the PD skeleton spec for Bob.

## 8. Implementation children (created on ratification)

1. `dist-1-contract-amendment` — §7/§9 text for `patch:` slots, `/os/patches`,
   `/os/droppatch`, retirements; renames the stale `patches/README.md`.
2. `dist-2-node-side` — `patch:` landing + refusal rules, listing/drop verbs,
   fetch progress observability, simfleet parity, gitignore for
   `patches/*`/`assets/*`.
3. `dist-3-dashboard-send` — serve `patches/`, Send/Sync/dropdown/delete UI,
   button renames, asset metadata listing, Playwright verify.
4. `dist-4-demos` — `default`→`demo-pd`, `templates/supercollider-bopos`→
   `patches/demo-sc`, strip retired config, flag the PD-side edits for Bob's
   list.

## 9. Open questions for Bob (the actual decision points)

- **Q1 naming:** "Send assets"/"Send patch" + one "Sync all" — or "Sync"
  everywhere?
- **Q2 gdrive/getsamples retirement:** one-release legacy window (proposed)
  or kill now? Kite Choir / The Plants are the fleets that care.
- **Q3 delete semantics:** is `droppatch` wanted at all, and should it also
  exist for asset slots (`dropassets <slot>`)?
- **Q4 send-to-active:** should sending the *active* patch stop the engine,
  converge, and restart (convenient, slightly violent) — or refuse and make
  you switch away first (proposed: refuse, dashboard offers the
  restart-after as a follow-up action)?
- **Q5 demo naming:** `demo-pd`/`demo-sc` as proposed?
- **Q6 templates/ ruling:** confirm superseding the 2026-07-08 "template
  lives in `templates/`" decision.
