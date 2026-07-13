# ui-1-layout-pass

Page structure and technical-view changes from the 2026-07-13 brain dump.

- [ ] **Map to the top:** the spatial map is the primary view — it goes at
      the top of the page body (or bleeds into the sides), with the rest of
      the UI below/around it as the central overview.
- [ ] **Synced cue section** moves out of the spatial section — it doesn't
      belong there; further down the page.
- [ ] **Master slider** visible in the technical view, probably alongside the
      mute button.
- [ ] **Aloha button:** Bob suspects it's no longer needed. Check what it
      actually does and whether anything still depends on it; if it's dead,
      remove it — if it isn't, leave it and record why here.
- [ ] **Facilitator → technical link:** a button back to the technical view
      from `/facilitator`. Bob explicitly deferred locking the facilitator
      page — don't build a lock, just note the future mechanism is welcome.
- [ ] Playwright `verify_*.py`: layout order (map first), master slider
      present + functional in tech view, facilitator back-link navigates.
