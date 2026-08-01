# Decisions — 04-event-fire-affordance

Design session held live with Bob, 2026-07-28, against an interactive mockup
of three candidate fire buttons in the ratified panel token language.

## Ratified

1. **Fire button = variant A.** 58 px × `--row-h`, `--input` fill, 1px
   `--control-line`, `--radius-momentary` (7px). Rejected: a 3px baseline
   progress rule (too quiet at 58px) and a 76 × 28 oversized button (reads
   bigger, but breaks the shared left column with parameter value boxes).
   The alignment argument won: a fire button occupies the value-box slot.

2. **Flash ink = `--mod` cyan.** Bob: *"cyan works — the metaphor holds — a
   generator of sorts is driving, just not continuously."* This is a
   deliberate widening of the panel language's `cyan = modulation` rule
   (`design-language.md` §1): cyan now means *something is driving this
   control*, continuously (a generator) or discretely (an event firing).
   Considered and rejected: accent purple (correct by the narrow reading of
   the rule, but reads as chrome) and white-hot (too soft to register).
   Green — the retired `/cue` flash — stays retired.

3. **Progress = a wash** sweeping left→right behind the label over the global
   lead, then the flash. Lead `0` is sync-off and flashes with no sweep.

   *Amended in the same session, after Bob saw it running:* the ratified
   `--value-fill` wash "wasn't reading particularly well with the button in a
   hover state." Two causes, both fixed:

   - The sweep now uses `--mod-fill`, not `--value-fill`. At 58 px a neutral
     translucent wash is too low-contrast to track, and sweeping in the
     flash's own ink turns the schedule into one gesture — the fill builds
     toward the flash instead of being a separate grey event. The border also
     goes `--mod` for the duration.
   - Hover is now suppressed while `.firing` / `.fired`. The hover fill sat
     *under* the wash and repainted the rest state, and the cursor is by
     definition on the button at the moment it fires — so hover was muddying
     precisely the moment the feedback exists for.

4. **The lead field leaves the standalone iPad view too.** Bob chose to drop
   the whole section on both surfaces rather than keep a tablet-only lead
   control. Lead is now a desktop-only setting, owned by the Monitor dock's
   Globals panel (`03-global-controls-monitor`); the iPad fires, it does not
   configure. Consequence to accept: an iPad-only session cannot change lead.

5. **Events render above parameters**, on the control panel and mirrored in
   the Patch tab's manifest editor.

## Not decided here

The `02-app-wide-rollout-design` question of whether the fire button's shape
generalises to other momentary actions app-wide. This stitch establishes it
inside the panel only.
