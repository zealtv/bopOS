# Patches

`patches/` is the host-side authoring root and mirrors the patch layout on
bopOS nodes. Each immediate child directory is one patch. Patch authors can
work here without installing or importing bopOS separately. The step-by-step
authoring and deployment guide is [docs/COMPOSING.md](../docs/COMPOSING.md);
this file is the layout and manifest reference.

The repository's demos are:

- `demo-pd/` — Pure Data reference patch
- `demo-sc/` — SuperCollider reference patch

The host layout is:

```text
bopOS/
  patches/
    .templates/
      bopos-template.pd
    demo-pd/
    demo-sc/
    <composer-name>/
    active_patch.txt
  assets/
    <slot>/
```

`.templates/bopos-template.pd` is Bob's immutable Pure Data stub for the
dashboard's **New patch** action. The hidden directory is outside patch catalog
listing. New patch copies that file byte-for-byte to `<name>/main.pd`; dashboard
code never authors or modifies Pure Data source. If the template is unavailable,
New patch still writes the manifest and reports that `main.pd` must be supplied
before the patch can launch.

Composer-owned patch directories may be ordinary folders or independent Git
repositories. They are ignored by the bopOS repository; only the demos are
tracked. A device copy is either Git-managed or host-mirrored, never both.

## Required manifest

Every patch requires a valid `bopos.patch.json`. The manifest declares at
least the engine and entry point, so the entry point is not required to be
`main.pd` and the engine is not required to be Pure Data.

```json
{
  "engine": "pd",
  "entrypoint": "main.pd",
  "params": [],
  "events": [],
  "caps": [],
  "slots": []
}
```

`params` declares the controls the dashboard can render. Each parameter uses
an explicit `kind`: `float`, `int`, `toggle`, `enum`, or `text`. Optional
`events` documents actions the patch handles. Each event has a `name`, optional
structural `path`, an `arity` from 0–3, and optional per-element `labels` and
`defaults`. Events are delivered as `/e/<identity>` with zero to three floats.
Declarations do not filter event traffic, so well-formed undeclared identities
are still delivered.

Missing or invalid manifests fail launch loudly. Patch-level `bopos.config`
and its `SAMPLEPACKSURL` workflow are retired.

## Distribution workflows

The normal composer workflow is host-mirrored:

1. Create or copy a directory under `patches/`.
2. Add and validate its `bopos.patch.json`.
3. In the dashboard's Patches tab, select it as the fleet patch and press
   **Deploy as fleet patch** (one confirmed operation for all online
   assigned devices; per-device patch mixtures are not a supported mode).

Deployment uses `/os/fetch` with the `patch:<name>` slot. It converges each
node's `patches/<name>/` directory to the host copy, including pruning files
that no longer exist on the host, then restarts the audio engines into the
new patch.

For the advanced Git workflow, `/os/addpatch` installs a Git-managed patch and
`/os/pullpatch` updates it directly from its remote. Host-mirror sends refuse a
device patch containing `.git`, which prevents the two workflows from being
mixed.

Assets live in sibling directories under `assets/` and are sent separately.
At launch, the framework supplies the ordered list of absolute installed
asset-slot folders to the engine through its run context. Adding or removing a
slot changes that list on the next engine start.

## Active patch

`active_patch.txt` stores the name of the active patch.
