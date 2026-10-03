# Load-failure notice placement — for Bob's ruling

An operator on Control or Seats currently sees an empty installation with no
explanation because the persistent load notice appears only in Show warnings.

| Option | Placement | Trade-off |
| --- | --- | --- |
| 1 | Header warning badge that opens the notice | Compact, but requires a click to learn why the installation is empty; the header already carries connection, execution and theme controls. |
| 2 | Persistent notice strip below the tab bar, above the active workspace | Visible on every main tab, with room for the filename and repair instruction; uses a little vertical space. |
| 3 | Repeat the notice at the top of each tab | Close to each workspace, but duplicates rendering and can drift between tabs. |

**Recommend option 2.** Render the existing notice text once outside the tab
panels, distinct from WebSocket connection status. Keep it visible while the
notice exists; no dismiss or automatic overwrite/repair action. Use readable
text and a status region, not color alone. In standalone Remote, place the same
notice immediately below its header so tablet operators get the explanation.
Leave Show-specific target/drift warnings in Show; avoid displaying the same
load notice twice there.

Decision needed: approve option 2 (including Remote), or choose another placement.
No UI implementation is included in this commit.
