# Handoff — 34 backlogged; 20 and 25 await design ratification

This is the current launch note. It supersedes
`.notes/handoff-2026-07-23-install-device-complete.md` for Loom ordering and
claim state.

## Bob's latest ordering

- `34-fleet-patch-global-state` moved intact under `feature-backlog`; its
  menu-bar design leaf is waiting.
- Work proceeded sequentially into 20, then 25.
- Neither implementation may begin until Bob ratifies its user-facing design.

## 20 — Monitor dock

`20-console-dock/01-dock-design` was claimed, researched, and returned to
`.waiting` with `proposal.md`.

The key finding behind Bob's question:

- PD `to-bopos-report` is formatted as local `/report <name> <values…>` and
  sent to `bopos.py` on UDP 7770;
- the node retains the latest typed value per name in memory;
- the write is not forwarded to the Dashboard, so it appears in neither
  current OSC console and not in the Device Report panel;
- a one-shot `/<id>/os/probe <name>` produces
  `/os/probe <id> <name> <values…>`, whose request/reply can appear in the
  outgoing/incoming traffic streams.

The proposal names the app-wide surface **Monitor** and ships Incoming,
Outgoing, Send, Reports, and System tabs in v1. Reports provides a direct
demand-driven probe UI; Map remains deferred. Ratification points are at the
end of the proposal.

## 25 — semantic message pills

`25-message-pill-encoding/01-pill-encoding-design` was then claimed, researched,
and returned to `.waiting` with `proposal.md`.

The proposal recommends eight flat categories, treating the omitted
`param-loop` as an oversight. It uses theme-specific tinted fills plus visible
kind codes (`CUE`, `PT`, `RAW`, `VAL`, `FD`, `LP`, `LFO`, `STOP`) so colour is
not the only channel. The proposed text pairs measure 9.32:1–11.05:1 in dark
and 6.22:1–7.30:1 in light. No dashboard implementation files changed.

## Repository state

- No stitch is claimed.
- Both design stitches are `.waiting` for Bob.
- `git diff --check` passes.
- `dashboard/shows/` remains unrelated, untracked, user-owned work.
