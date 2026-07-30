# 03-chrome-reclamation

Reclaim wasted vertical space and move the standalone-view link into the tab
bar. Cheap, independent of the component work, and the most immediately
visible progress in the thread.

Bob, 2026-07-30: *"there's a lot of wasted real estate … that text isn't doing
anything. We don't need it at all."*

Work:

- Delete the dead `.eyebrow` + `<h2>` heading blocks where the tab bar already
  says where you are: `index.html:26` ("Live control" / "Control") and
  `index.html:128` ("Single-device delivery" / "Assets"). Review the other
  three (`index.html:82`, `show.js:455`, `show.js:487`) by the same test —
  keep only what carries information the tab bar does not.
- Move `Open standalone dashboard` (`index.html:26`, `#facilitator-link`) into
  the primary tab bar, right-aligned, as a short-named link.
  **Name RULED by Bob, 2026-07-30: `Remote`.** It is an `<a>` to a different
  document, so place it *beside* the `role="tablist"`, never inside it, or
  assistive tech announces a tab that is not one.
- **Already done in the 2026-07-30 groundwork commit:** the manifest editor's
  two `dashboard` checkboxes and the editor param badge now read **Remote**
  (they said "Facilitator" / "Dashboard"). Bob ruled the terminology follows
  the tab name. The flag itself is unchanged — it still gates only the
  standalone view. `tests/verify_manifest_param_visibility.py` was updated with
  the supersession noted inline. The `<a>` at `index.html:26` is the last
  holdout ("Open standalone dashboard") and is this stitch's to move.
- Repeated action toolbars become icon buttons with accessible names and
  tooltips: `index.html:76` (`Forget offline unbound` / `Reboot All` /
  `Shutdown All` / `Update bopOS`), `#editor-session-actions`,
  `.fleet-patch-actions`, `.mode-actions`. Destructive actions keep an
  unmistakable affordance — do not make `Shutdown All` a bare glyph.
- Give the 8 `<details>` disclosures across 5 files one shared treatment.

Do not touch the Show message pills or the spatial map beyond token colours.
