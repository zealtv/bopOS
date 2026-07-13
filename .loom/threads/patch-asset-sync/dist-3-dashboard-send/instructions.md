# dist-3-dashboard-send

Dashboard side of the ratified model (authority:
`.loom/tied/dist-0-proposal/`; needs dist-1 text and dist-2 verbs).

- [ ] **Serve `patches/`** the way `--assets-dir` serves assets
      (`dashboard/server.py:357-380` is the pattern): static mount +
      `.manifest.json` route.
- [ ] **Send assets / Send patch**: pick a directory under `assets/` /
      `patches/`, target device or all; fires `/os/fetch` at the dashboard's
      own URL. **One "Sync all"** (Q1): every patch + asset dir to the
      selection. Per-device progress + in-sync/stale from hash comparison.
- [ ] **Sending the active patch is confirm-gated** (Q4): the confirm dialog
      says it will stop and restart the engine on the device(s).
- [ ] **Patch dropdown** from `/os/patches` replaces the typed-name Switch
      input (`dashboard.js:120`, `#patch-name`); **delete** via `droppatch`,
      confirm-gated; asset-slot delete via `dropassets` where assets render.
- [ ] **Git patches get an icon** (or similar) so git-managed vs
      host-mirrored is legible at a glance (`git` flag from `/os/patches`);
      "Pull latest" renders only for git patches.
- [ ] **Renames/removals**: "Get samples" button gone (both placements:
      `dashboard.js:120` and the action list at `:121`, plus the
      `get_samples`→`getsamples` translation in `osc_bridge.py:200-205`);
      "Update All" → **"Update bopOS"** everywhere, wire verb `updatebopos`.
- [ ] **Asset listing metadata**: host-side dirs with file count, total
      size, last-modified.
- [ ] Playwright verify_*.py on simfleet: send patch converges (sim replies),
      sync-all iterates, dropdown populated from /os/patches, git icon
      renders, active-patch send shows confirm, no getsamples anywhere,
      Update bopOS fires updatebopos.

Coordinate with `dashboard-9-ui-review` children if they land first — button
placement may have moved (map-at-top layout).
