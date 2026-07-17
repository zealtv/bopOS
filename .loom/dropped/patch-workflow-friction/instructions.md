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
The `patch-asset-sync` goal tied on 2026-07-14. Both current children are now
claimable: `friction-0-docs` owns the composer guide + network recipe, and
`friction-1-starter-kit` owns demo teaching polish plus the precise Bob-owned
PD skeleton follow-up. This goal ties when a musician can go from nothing to
sound on a device using only the doc + dashboard.

---
**2026-07-14 update — both children re-parked as `.waiting`.** d8-1..3 tied,
but Bob staged three new upstream threads that reshape what these docs must
describe: `fleet-patch` (one fleet-wide patch + convergence badges), `ui-tabs`
(the dashboard becomes tabbed: overview / spatial / fleet management / patch
editor), and `patch-editor` (composer-helper tab that also removes manual
manifest editing — it changes the composer workflow these docs teach). Resume
friction-0/1 after `ui-tabs/tabs-2-review-session` and the `patch-editor`
implementation land, so the guide describes the final tabbed UI and the
editor-assisted manifest flow.
