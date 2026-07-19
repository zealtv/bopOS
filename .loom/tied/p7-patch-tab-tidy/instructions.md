# p7-patch-tab-tidy

Three Patch tab items from the braindump. Independent of p1–p6; claimable
alongside them.

1. **"facilitator" → "Dashboard" — full rename (Bob ratified 2026-07-19).**
   Not just UI copy: the manifest key itself renames `facilitator` →
   `dashboard` (boolean, same semantics: the param is promoted to the
   dashboard's live-control surfaces, facilitator view included — that
   view is a dashboard-served surface). Scope: `python/manifest.py`
   validation, the launcher's validation path, `dashboard/server.py`,
   `dashboard.js`/manifest editor, every demo `bopos.patch.json`, and the
   verifies/fixtures that write `facilitator: true`. Compatibility: accept
   the legacy `facilitator` key on load and normalize to `dashboard`
   (saves write only the new key); reject a manifest carrying both with
   conflicting values. Record the rename as a contract amendment line in
   `docs/OSC-CONTRACT.md` §8 + revision table (ratified, so record it —
   don't re-open it). Grep-sweep when done: rendered UI shows "Dashboard";
   `facilitator` survives only in the legacy-load path, the facilitator
   view's own filenames/routes (unchanged — it is an operator surface
   name, not the manifest term), and historical lore/notes.
2. **Legacy `group` removal.** Nothing in the demo patches uses it (Bob,
   2026-07-19 — verify with a grep before deleting). Remove: the "legacy
   group" field from the manifest editor, the group/path mutual-exclusion
   plumbing in `dashboard.js`, the `group` fallback in section rendering
   (absent path renders in the flat "parameters" bucket), and the field
   from any demo manifest that carries it. `python/manifest.py`
   validation: drop the `group` rules; decide whether an encountered
   `group` key now errors or is ignored — recommend ignore-with-badge or
   plain ignore for old third-party manifests; record the choice
   additively (contract §8 mention of the legacy field needs a one-line
   amendment note — flag it, don't re-litigate the contract).
   If any demo manifest tidy would require changing PD routes (it should
   not — `group` never touched the wire), stop and surface to Bob.
3. **Path hint clarity.** The path field's example placeholder reads as if
   it were a value. Make it unmistakably an example (e.g. placeholder
   `e.g. instrument/marimba` or a caption under the field), consistent
   with existing form idioms.

Verify: `verify_patch_tab_tidy.py` (house pattern): no "facilitator" text
renders on the Patch tab (case-insensitive DOM sweep; the JSON key still
present in the manifest payload), no legacy-group input exists, a manifest
carrying `group` still loads per the recorded decision, path field hint
matches the chosen form, and `grep -ri group patches/*/bopos.patch.json`
comes back clean. Re-run the tied manifest-editor verify(s) and amend (log
it).
