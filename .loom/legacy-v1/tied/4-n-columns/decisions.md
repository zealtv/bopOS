# 4-n-columns — tie note

All four children are tied:

1. `1-columns-layout` — the 342px left-aligned track, `bopos.control.columns`
   with minted ids, the strip, add/remove/reorder, per-column scroll and target,
   one live region per column, and "Open in Control" replacing the retired
   focus-seat follow.
2. `2-venue-wide-capture` — D1–D3 as a **removal**: `scope`/`id` left both
   capture verbs, `preview_show_preset_capture` was deleted, and three dialogs
   became one `ShowCapture` component (arm → preview → commit → undo).
3. `3-chrome-demotions` — D8. Reachable chrome across three columns measured
   25 → 13, a Seat card 6 → 3. It also found and fixed a live defect: a
   `device_update` beating the initial `state` pruned a restored column's target
   and **persisted** it.
4. `4-current-show-broadcast` — the Monitor System panel now names the loaded
   show, because `set_current_show` finally broadcasts the plane it mutates.

## Against the ratified mockups

The tab matches `1-columns-design`'s mockups at 1280 (shot in
`3-chrome-demotions/control-after-1280-*.png`, against the real app rather than
a composed shell): fixed 342px left-aligned columns with the 1400px cap dropped,
the column as the card, the closed picker as the column's own sticky title, no
dialogs anywhere in the tab, and D8's demoted chrome. Wider viewports were shot
and checked by `1-columns-layout` when it shipped the track; nothing since has
touched the layout, only what sits inside a card.

Two mockup details are deliberately not reproduced, both because Bob ruled after
the mockups were drawn: the per-column capture button (D1 — capture is
venue-wide and lives on the strip), and the ambient focus-seat follow (D7,
amended to "never").

## What did not stay in this thread

`4-current-show-broadcast` was queued here by Bob as an ordering call rather
than a claim of kinship, with permission to lift it out if it ever held the
thread open. It did not — it shipped the same session as `3`.
