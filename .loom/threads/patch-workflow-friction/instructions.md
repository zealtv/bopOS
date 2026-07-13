# patch-workflow-friction

**Goal:** lower the barrier for non-tech-savvy musicians to get their sound onto devices.
Today's path — write PD, push to GitHub, set up a WiFi network, talk OSC to a headless
Pi — is too steep (review §3.6). Secondary priority per Bob (hand-holding works today),
but the dashboard changes the economics.

Direction (dashboard-first — most of this falls out of `dashboard-4-patch-mgmt`):
- [ ] Musician never touches a terminal: add/switch/update patches from the dashboard
- [ ] A patch starter-kit / template repo: `main.pd` skeleton wired to bopos.osc
      conventions, `bopos.config` example, README written for a musician
- [ ] Document the "bring a patch" path end-to-end (who makes the repo, who presses what)
- [ ] Consider: dashboard-side patch upload (zip → backend pushes to Pis) to bypass
      GitHub entirely for one-off workshops — judge cost vs the git model's benefits
      before building
- [ ] Network setup recipe: the travel-router pattern (documented SSID/password
      convention) so "get the Pis on WiFi" is a checklist, not an adventure

Keep bopOS's git-repo patch model as the canonical mechanism; friction reduction layers
on top, it doesn't fork the mechanism.

---
**2026-07-13 update — much of the direction above is superseded by the
ratified `patch-asset-sync` model** (`.loom/tied/dist-0-proposal/`): git is
no longer canonical-for-composers — the main flow is author in `patches/`,
Send from the dashboard (host↔Pi mirror); git survives as the advanced path
(own doc section per Bob). The "zip upload" consideration is resolved (Send
patch is the ratified equivalent); `bopos.config` (patch-level) is retired.
Current children: `friction-0-docs.waiting` (composer doc; resumes when
dist-2/3 land) and `friction-1-starter-kit.waiting` (rewritten — the starter
kit is the demo patches; blocked on dist-4). The network-recipe item remains
live inside friction-0. This goal ties when a musician can go from nothing
to sound on a device using only the doc + dashboard.
