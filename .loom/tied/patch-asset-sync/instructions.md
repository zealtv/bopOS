# patch-asset-sync

**Goal:** one coherent model for how patches and assets live on the bopOS
conducting computer and reach devices — a composer never needs git, and the
device directory structure mirrors the host's. Source: Bob's 2026-07-13 brain
dump (`.lore/items/2026-07-13-composer-experience-brain-dump` — read the
verbatim dump before working this thread).

The forming model (Bob's words, condensed — the proposal firms this up):

- Patch authoring happens **inside the bopOS directory structure**: each patch
  is a folder in `patches/`, so PD patches see the bopOS externals without any
  import dance. Same for SC and other engines.
- Some patch folders are git repos, some aren't. A git-repo patch pushed to a
  device can self-update with only an internet connection when sent a
  "pull patch" message — no dashboard needed. Non-git composers just build in
  `patches/` and use the dashboard to **send** the patch to devices, the same
  way media is sent.
- An `assets/` folder on the host; you choose a directory from it to send;
  sending **overwrites** the same-named directory on the Pi. Host and Pi
  directory structures mirror each other.
- Sync shape is open: sync-everything button vs per-patch / per-asset-dir
  sends (Bob sketched both; likely both belong).
- Once patches are on a device, switching is a **dropdown**, not typed names;
  possibly delete patches the same way.
- "Get samples" renames to "Get Assets" (or "Send Assets" — the verb's
  direction is part of the design). "Update All" is ambiguous today (updates
  bopOS or the current patch?) — clarify or rename.
- Assets list with metadata: file count, folder size, last-updated date.
- Open manifest questions: is `bopos.config` required inside a project? Must
  the entry point be `main.pd`, or should the manifest name the starting
  patch?
- `templates/supercollider-bopos` dissolves: SC becomes a **demo SC patch in
  `patches/`**, akin to the demo PD patch (which replaces "default").

**RATIFIED (Bob, 2026-07-13)** — `.loom/tied/dist-0-proposal/` holds the
proposal, the two code surveys, and `ratification.md` (Bob's verbatim
feedback + rulings). Headline amendments over the sketch above: **all hard
breaks, no legacy windows** (gdrive scheme, getsamples, and the no-manifest
`main.pd` fallback all die now); `/os/update` renamed **`/os/updatebopos`**;
git-managed patches get a UI icon; send-to-active = stop→converge→restart,
confirm-gated dashboard-side (Q4 "violence"); one "Sync all" + per-item
Sends; `droppatch` and `dropassets`; `demo-pd`/`demo-sc` in `patches/`,
`templates/` deleted.

Children in order: `dist-1-contract-amendment` → `dist-2-node-side` →
`dist-3-dashboard-send` → `dist-4-demos` (free to work; dist-3/4 need
dist-1/2's contract text and verbs first). `sample-distribution` (goal +
samples-0..2) was dropped as superseded; `friction-0-docs` waits on
dist-2/3 so the composer doc can be walked against the real flow.

Done when: the ratified model is implemented — a composer can author in
`patches/`, send patches and assets to any/all devices from the dashboard,
switch patches by dropdown, and the host↔Pi mirror holds.
