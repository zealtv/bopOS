# pe-2-edit-mode

The editor's runtime and tab shell (ratified design:
`.lore/items/2026-07-14-patch-editor-design-ratified/`, proposal §2–§4).
Needs pe-1 tied (the param panel may meet `cues` keys in manifests).

- `tools/audition.py --edit`: force `--devices 1`, drop `-nogui` from the PD
  command, report the mode in the ready message. Nothing else diverges — run
  context, engine port, relay surface, heartbeats unchanged.
- Supervisor mode enum in `dashboard/server.py`: `off | simulate | edit`,
  mutually exclusive (the rig binds the loopback cmd port; the OSC sender is
  single-target). Entering either running mode stops the other;
  confirmation-gate leaving a *running* sim. Edit mode retargets OSC to
  loopback exactly as simulate does and restores the performance target on
  exit.
- Editor UI (lives wherever the current layout allows; the `ui-tabs` thread
  gives it a real tab later): host patch list (valid manifests), select to
  launch, param panel reusing the tech-view manifest-driven controls — all
  params with group + facilitator badge, master included, framework mute
  excluded. "Hear it in the sim" / "Edit this patch" cross-mode buttons.
- Health: `/hb` engine-alive drives an "engine closed → Relaunch" state when
  Bob quits the PD window — never auto-respawn (it would steal focus and
  discard the editing session's state). Explicit Restart button for
  cold-start testing.
- Verification: Playwright `verify_*.py` (copy newest tied template) driving
  mode exclusivity, patch launch/param send (`--no-engine` for CI-ish runs),
  and the closed-engine state; plus a real GUI-PD launch check where the
  environment has PD, skipped honestly otherwise.
