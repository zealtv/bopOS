---
name: land-before-usage-window
description: "Bob's rule — use the whole 5hr usage window but never leave the project midflight when the limit hits"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c18c7ad9-d5f2-4425-bdbd-dc573f1c3cb6
---

Bob (2026-07-14): "try and land before the 5hr usage window. you can use the
whole window, just try not to leave the project midflight if the usage limit
hits."

**Why:** a usage cutoff mid-task strands uncommitted, unverified work that
the next session has to reconstruct.

**How to apply:** prefer small committable slices over one big pass; commit
each coherent slice as it verifies; prefer inline work over large subagent
runs late in a window (a monolithic agent run can't be landed partially).
Before starting anything sizable, ask whether it can be finished-and-committed
in the window's remainder; if not, split it or park it cleanly with a note.
