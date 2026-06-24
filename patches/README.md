## Patch Management Workflow (2026)

### Patch Structure

- Each patch is a git repository cloned into a subfolder of `patches/` (e.g., `patches/default`).
- The patch folder name is the patch name.
- The entry point for each patch is always `main.pd` inside the patch folder.
- Optionally, a patch may include a `bopos.config` file specifying variables (e.g., `SAMPLEPACKSURL`) to be accessed by shell scripts in the parent project.


### Adding Patches

- Patches are added via an OSC command that now receives the patch user and repo as two separate arguments (not a single `user/repo` string).
- The system checks if the repo exists, deletes any existing patch folder of the same name, and then clones the repo recursively (including submodules) into `patches/<patchname>`.
- Example OSC command: `/addpatch user repo`

### Activating Patches

- The active patch is tracked in `patches/active_patch.txt`.
- When activated, the system launches `main.pd` from the patch folder.
- If a `bopos.config` file is present, shell scripts can access variables such as `SAMPLEPACKSURL` for samplepack download.

### Example Patch Folder

```
patches/
  default/
    bop/ # optional - patch provides it's own pd dependencies
    main.pd
    bopos.config   # optional, stores variables like SAMPLEPACKSURL
    start.sh  # optional, runs at boot if present
```

### Notes

- Entry point is always `main.pd` unless otherwise specified in future conventions.
- Samplepack location and other variables are discovered from `bopos.config` in the patch folder.

## active_patch.txt
stores the currently active patch