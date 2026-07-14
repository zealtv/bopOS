# pe-0-design-proposal

Write the patch-editor design proposal (lore-kept, then `.waiting` for Bob).
The seam and cue decisions in the parent goal are settled; this stitch designs
the rest:

- **Editor session lifecycle:** selecting a patch launches its engine (PD with
  GUI) via the managed-audition launch path; what stop/switch/crash-recovery
  look like; how the editor coexists with a running Start-simulation session.
- **Parameter panel:** generated from the manifest (reuse the existing param
  UI); sends `/p/<name>` over loopback to the editing instance.
- **Manifest editing UX:** add/edit/remove params (name, type, min/max,
  default, group, facilitator flag) writing `bopos.patch.json`; validation;
  and the liveness choice — restart-on-save vs a localhost-only dev-mode relay
  for not-yet-declared params (recommend one).
- **Cues amendment wording:** the exact additive `"cues"` manifest schema
  (v1.3→v1.4) — id, label, description? — and the editor's cue-fire UI. Keep
  the §3.1 rule intact: engines only ever see the bare relative fire.
- **Points mini-setup:** one element + draggable points feeding the existing
  bopos.py proximity → `/pt` path; decide whether it's a stripped spatial map
  or reuses the full one.
- **Single-object seam:** walk the resulting composer workflow and assess the
  [bopos]+[bopos.out~] merge idea in that light; recommend, don't implement
  (PD-side work is Bob's).

Check the SC path degrades sanely (launch `scide`? out of scope? say which).

On ratification: split implementation children under `patch-editor`
(numbered), tie this.
