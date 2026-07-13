# Patches

`patches/` is the host-side authoring root and mirrors the patch layout on
bopOS nodes. Each immediate child directory is one patch. Patch authors can
work here without installing or importing bopOS separately.

The repository's demos are:

- `demo-pd/` — Pure Data reference patch
- `demo-sc/` — SuperCollider reference patch

The host layout is:

```text
bopOS/
  patches/
    demo-pd/
    demo-sc/
    <composer-name>/
    active_patch.txt
  assets/
    <slot>/
```

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
  "caps": [],
  "slots": []
}
```

Missing or invalid manifests fail launch loudly. Patch-level `bopos.config`
and its `SAMPLEPACKSURL` workflow are retired.

## Distribution workflows

The normal composer workflow is host-mirrored:

1. Create or copy a directory under `patches/`.
2. Add and validate its `bopos.patch.json`.
3. Send the patch to selected devices from the dashboard.
4. Select the installed patch by name.

Sending uses `/os/fetch` with the `patch:<name>` slot. It converges the node's
`patches/<name>/` directory to the host copy, including pruning files that no
longer exist on the host. Sending an active patch stops and restarts its engine
and is confirmation-gated in the dashboard.

For the advanced Git workflow, `/os/addpatch` installs a Git-managed patch and
`/os/pullpatch` updates it directly from its remote. Host-mirror sends refuse a
device patch containing `.git`, which prevents the two workflows from being
mixed.

Assets live in sibling directories under `assets/` and are sent separately.
At launch, the framework supplies the shared asset root to the engine through
its run context. The dashboard offers per-item sends and one aggregate Sync
all operation.

## Active patch

`active_patch.txt` stores the name of the active patch.
