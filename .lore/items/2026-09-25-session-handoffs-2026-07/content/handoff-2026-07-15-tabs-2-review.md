# Handoff — tab skeleton complete, hands-on review next (2026-07-15)

State at handoff: tabs-0 is ratified and tied; tabs-1 implements the six-tab
skeleton and is tied. The next interaction is Bob's tabs-2 visual/touch
review against the real dashboard.

## Start here

1. Read `CLAUDE.md`, this note, and `.loom/tied/tabs-1-skeleton/results.md`;
   run Loom status.
2. Refresh `http://127.0.0.1:8080/`; static assets are served live by the
   existing dashboard process. Dashboard is the default tab and the URL hash
   deep-links every tab.
3. Resume `ui-tabs/tabs-2-review-session.waiting` only when Bob is ready to
   inspect the real UI. Record observations there and split concrete fixes.

## Landed map

- Dashboard: live/touch surface, master, cues, presets, promoted params and
  guarded fleet/single-device admin actions.
- Seats: spatial map, points, seats, simulation and venues.
- Devices: active/recent and unbound devices, details/admin and fleet patch.
- Patches: complete editor.
- Assets / Sequencer: placeholders.

`/facilitator` remains a renamed standalone Dashboard compatibility entry. The
Dashboard tab embeds that mature surface for the skeleton; whether to flatten
that boundary is a tabs-2 judgment, not hidden technical debt.

## Known review prompts

- Dashboard has generous empty space with a small fleet.
- Devices intentionally shows both active/recent and unbound groupings, so an
  unbound device appears in both; judge whether the visibility is useful.
- Check tab density and sticky navigation on iPad/touch.
- The requested all-device promoted-parameter controller is in the ratified IA
  but was deliberately deferred with the other post-skeleton Dashboard UX wins.

Focused browser verification passed 20/20; no `.pd` file changed.
