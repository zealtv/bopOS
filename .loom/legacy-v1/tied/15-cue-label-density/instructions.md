# 15-cue-label-density

Apply Bob's hands-on density revision to declared Dashboard cues:

- Each cue button shows only `label || id`.
- Do not render the manifest description or a secondary cue ID.
- Remove the visible panel-level scheduling message.
- Keep the cue name unchanged while scheduling; use a subtle, reduced-motion-
  aware animation instead of switching the button text to "Scheduled".
- Preserve exact ID delivery, the shared Lead control, touch targets, and an
  accessible non-visual scheduling announcement.
- Verify embedded and standalone Dashboard behavior without changing the OSC
  contract or `.pd` files.
