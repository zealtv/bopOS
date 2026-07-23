# Handoff — Monitor v1 and semantic message pills complete

This is the current launch note. It supersedes
`.notes/handoff-2026-07-23-console-pill-design-gates.md`.

## Loom state

- `34-fleet-patch-global-state` is preserved under `feature-backlog`; its design
  leaf remains waiting.
- `25-message-pill-encoding` is complete and tied, including its design,
  implementation, and parent stitch.
- No stitch is claimed.
- `20-console-dock` has all ratified Monitor v1 children tied. Its parent remains
  open only because `07-map-tab.waiting` is deliberately deferred.

## Monitor v1

The Dashboard now has one app-wide **Monitor** surface, outside tab panels and
`#show-root`, with:

- Incoming and Outgoing bounded traffic views with filter, pause, and clear;
- Send, using the shared typed OSC parser;
- Reports, for demand-driven inspection of node report values;
- System, including server state and one-shot probe results;
- browser-persisted collapse, height, active tabs, and split layout;
- a draggable wide split with 30/70 snap actions, plus a narrow single-tab
  fallback.

### Where `to-bopos-report` messages can be seen

PD sends `to-bopos-report` locally to the node, where the latest typed value is
retained in memory; it is not pushed spontaneously to the Dashboard.

Open **Monitor → Reports**, choose an assigned online Device, enter the report
name, and press **Request**. The latest typed value appears in Reports. The
one-shot probe request and reply are also visible in Monitor's Outgoing and
Incoming traffic views.

## Semantic message pills

Show message pills now use eight flat semantic categories:

`CUE`, `PT`, `RAW`, `VAL`, `FD`, `LP`, `LFO`, and `STOP`.

Each category has theme-specific tinted fills and a visible kind code, so colour
is not the only encoding. Labels retain full text in their title and accessible
name while ellipsizing visually in dense rows.

## Verification

- All focused browser verifiers passed:
  - unified frame: 10/10
  - Send: 7/7
  - Reports: 7/7
  - System: 6/6, including the 30-second offline/return check
  - wide split/snap: 12/12
  - semantic pills: 24/24 in dark and light themes
- Living unit suite: 44/44 passed.
- JavaScript syntax checks and Python compilation passed.
- `git diff --check` passed.
- Browser screenshots were inspected for the split/narrow Monitor layouts and
  both semantic-pill themes.

No real device was required for this verification. `dashboard/shows/` remains
unrelated, untracked, user-owned work and was not touched.

## Small Monitor follow-up

The visible `shown` / `seen` traffic-count copy was removed from Incoming and
Outgoing on Bob's request. Buffering, filtering, pause, clear, and traffic
rendering remain unchanged. The focused static guard passed 5/5 and the Monitor
frame browser verifier passed 10/10.
