# 03-osc-send-tab

**Waiting on `01-dock-design`.** Claim once the dock design is ratified.

Bob: "maybe some sort of terminal that lets us send OSC messages by typing them."

## Outcome

- A dock tab with a prompt: type an OSC message (address + args), send it, see it
  echoed into the outgoing stream like any other traffic.
- Argument typing follows the OSC contract's grammar — read
  `docs/OSC-CONTRACT.md` §3 before inventing a syntax, and reuse the show
  message builder's parsing/validation rather than writing a second parser.
- **PD float precision** (house rule): the UI must not let a typed value needing
  >6 significant figures go through as a float.
- History: up/down recall of previous sends, at minimum for the session.
- Errors are shown inline, not swallowed — a malformed address must say so.
- Where the message is sent *from* and what it is allowed to address is a
  contract question, not a UI one. If typed sends need a new server-side route,
  keep it inside the existing engine/LAN boundary (`bopos.py` owns LAN
  6660/5550) and record it additively.

## Verify

Playwright: type a known message, assert it appears in the outgoing stream and
that `tools/simfleet.py` observed it. Plus a rejection case for a malformed
address and one for an over-precision float.
