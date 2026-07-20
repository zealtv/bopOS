# automation-visual-regression

Repair the saved `test` show's `go` step so its automation is visible on the
current `demo-pd` Dashboard controls.

- Keep the saved show's musical intent and automation arguments unchanged.
- Point the fade at the manifest-declared `gain0` control.
- Point the LFO at the only bound Seat (`0`), since offline/unbound controls
  deliberately retain the static automation glyph but do not claim live motion.
- Verify saved-show references against the active manifest and installation,
  then run the focused real-server browser automation regression.
- Do not edit any Pure Data file.
