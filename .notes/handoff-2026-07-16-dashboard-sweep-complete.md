# Handoff — Dashboard implementation sweep complete (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-live-controls-complete.md`.

## Completed

- The accepted Dashboard implementation sweep is complete through diagnostic
  density: aliases, updater, Assets, Groups, Live Controls, exact-device mute,
  copyable identity tails, host checkout indication, terse copy, Seats
  inspector hierarchy/guard/IP, and responsive control grouping are tied.
- A whole-Dashboard UX review selected a subordinate **All & Groups / Seats**
  live-control tab because aggregate cards consumed the iPad viewport before
  any individual Seat appeared. The tab is touch/keyboard accessible and
  persists across renders.
- The empty embedded `Seat presets` footer is gone. All Seats and per-Seat
  **Send all** remain parameter-only; adding global master/fleet-mute replay is
  explicitly held pending Bob's hands-on use.
- Diagnostic density verification passed **17/17** against the real dashboard,
  simulator, and touch Chromium. Live Controls backend **20/20**, exact mute
  **13/13**, and Seats workspace **12/12** also passed.
- The active fleet manifest's declared cues now render as synchronized,
  touch-friendly Dashboard actions in both embedded and standalone views. The
  production free-text field and idle shared-clock copy are gone; Patch edit
  retains undeclared cue trials. Focused verification passed **9/9**.
- Seats and Physical device rosters are now bounded scrolling regions. Seats
  have a live name-prefix filter; Physical devices deliberately retain only
  their existing categorical dropdown. Focused verification passed **9/9**.
- Exact-device mute intent can be changed beneath fleet safety mute; the node
  remains effectively muted until the fleet layer is released, and roster
  indicators now describe device intent only. Focused browser verification
  passed **7/7** and the existing node protocol regression passed **13/13**.
- A selected Device can set its OS hostname from its alias (`Finn Jet` →
  `finn-jet`) through an exact-UID, receipt-backed action. Existing Pis need a
  one-time `sudo bash/provision.sh` run for the new root-owned helper and
  sudoers policy; routine Update bopOS cannot install that boundary. Focused
  verification passed **10/10** without real Pi execution.

No `.pd` files changed. Real iPad/Safari, screen reader, installation LAN,
audible engine, and real Pi behavior were not exercised in this polish pass.

## Next

Close the sweep through `patch-workflow-friction` in order:

1. `friction-0-docs` — complete documentation review: make README a friendly
   system overview, establish a getting-started guide and composer guide, and
   move detailed implementation material into coherent technical docs.
2. `friction-1-starter-kit` — align starter-kit copy and examples with that
   final documentation.
