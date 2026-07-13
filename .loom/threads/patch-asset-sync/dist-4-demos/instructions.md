# dist-4-demos

Demo patches replace `templates/` (authority: `.loom/tied/dist-0-proposal/`,
Q5/Q6 ratified). Take after dist-1/2 so the layout matches the contract.

- [ ] `patches/default` → `patches/demo-pd` (directory rename + any
      references: `patches/active_patch.txt` default, docs, scripts).
      **`main.pd` content is Bob's** — rename the dir, never edit the patch.
- [ ] `templates/supercollider-bopos` → `patches/demo-sc`; delete
      `templates/`; its README already teaches the copy-into-patches
      workflow — re-aim wording at "copy a demo" and strip anything the
      hard breaks killed.
- [ ] Strip retired machinery from the demos: `patches/default/bopos.config`
      (SAMPLEPACKSURL) goes; demo manifests stay valid under the
      manifest-required rule; decide what `slots` the PD demo declares now
      that samplepacks arrive via Send assets.
- [ ] If the PD demo needs `main.pd` edits to read `BOPOS_ASSETS`/
      `bopos-context assets` (it will, once the legacy symlink story from
      dist-2 is settled), spec the edit precisely in
      `.notes/pd-edits-for-bob.md` and flag it — don't touch the .pd.
- [ ] Update `friction-1-starter-kit` instructions: the starter kit *is* the
      demos now (its templates/ RESOLVED note is superseded — already
      flagged there 2026-07-13).
- [ ] Verify: both demos pass `python/manifest.py` validation; demo-sc
      launches on the laptop rig path if practical; dashboard add/switch
      flow on simfleet sees both demos by their new names.
