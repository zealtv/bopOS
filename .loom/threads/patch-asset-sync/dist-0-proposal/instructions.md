# dist-0-proposal

Write the unified patch+asset distribution proposal for Bob to ratify.
Parent has the full brief; the raw source is
`.lore/items/2026-07-13-composer-experience-brain-dump`.

- [ ] Survey what exists before proposing: `dashboard-4-patch-mgmt` (tied —
      current send/update/switch paths and the "Update All" button),
      `fetch-landing` (tied — `/os/fetch <source-uri> <slot>` contract §9,
      `~/bopOS/assets/<slot>/` landing, `ASSETS` env), `patches/` and
      `templates/` layout, `getsamples.sh`, the patch manifest
      (`patch-manifest` tied). The proposal must say per piece: keep, rename,
      absorb, or supersede — including samples-0..2 as written.
- [ ] Cover every open question in the parent: host directory layout
      (`patches/`, `assets/`), send vs sync semantics (overwrite rule,
      all vs individual), the git self-update path ("pull patch" message) vs
      dashboard send for non-git folders, dropdown patch switch/delete, button
      naming (Get/Send Assets, Update All), asset metadata listing,
      `bopos.config` / `main.pd` / manifest-named entry point, SC demo patch
      replacing `templates/` (and "default" becoming the demo PD patch).
- [ ] Mind the amount of machinery on the Pi side: whatever syncs must
      survive flaky WiFi and partial fleets (resumable, verifiable,
      idempotent — the settled §9 fetch semantics were designed for this;
      prefer building the new model on it over inventing a second transport).
- [ ] Keep the OSC contract intact; if new verbs/messages are needed, shape
      them additively and flag them, per the delegation rule.
- [ ] Deliverable: a dated proposal kept in `.lore/` (`lore.sh keep`), a
      pointer here, then mark this stitch `.waiting` and surface to Bob.
      Decomposition of implementation children happens after ratification.
