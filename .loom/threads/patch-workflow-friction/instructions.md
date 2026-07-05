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
