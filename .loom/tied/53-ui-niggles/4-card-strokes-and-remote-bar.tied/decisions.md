# Decisions

- Group card identity now follows the same sorted-roster modulo-four rule as
  the Seats target picker. The previous implementation followed the temporary
  set of groups visible on the map, which made every group card neutral in the
  normal empty map view and caused Bob's report.
- Removed the localStorage bridge for map visibility. Group identity is
  derivable from venue state on both documents, so persisting presentation
  state was unnecessary and made Remote depend on whether Control had opened a
  particular map view.
- Grid tracks retain the proven 342px minimum, stop at 480px, and distribute
  free horizontal space between columns.
- Remote's live-audio controls are a fixed bottom bar (the always-visible
  behavior meant by “sticky” here). Fleet setup commands remain in document
  flow rather than being pinned with master/mute. The bar is one row above
  620px and stacks below it; body padding keeps the final content clear.
- The mute action reads `MUTE`; while active, its inverse reads `UNMUTE`.
