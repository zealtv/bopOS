# os-admin-verbs

**Split 2026-07-08 from the parent during the implementation run:** the §7
admin-verb rename was mapped to `hb-identity` in the parent checklist but
that stitch (correctly) scoped itself to liveness — no child ever landed
it. Everything else in the parent checklist is tied; this is the last
node-side gap between the deployed wire and `docs/OSC-CONTRACT.md`.

Contract §7: lifecycle + provisioning verbs answered by helper.py's LAN
listener (6660), same pattern as ping/mute/params/report:

- `/<sel>/os/reboot`, `/<sel>/os/shutdown`, `/<sel>/os/restart-engine`
- `/<sel>/os/update`, `/<sel>/os/checkout <branch>`, `/<sel>/os/patch
  <name>`, `/<sel>/os/addpatch <user> <repo>`, `/<sel>/os/pullpatch`,
  `/<sel>/os/getsamples` (alias of fetch-era behavior — decide whether it
  stays or maps to `/os/fetch gdrive: samplepacks`; propose, don't decree)
- **Every provisioning verb replies `/os/rev <sha> <model>` (unicast)** so
  the dashboard observes convergence — this is the genuinely new part; the
  handlers themselves mostly delegate to the existing 7770 callbacks.
  Reboot/shutdown obviously can't reply after; reply before executing.
- Update model dispatch (§7): persistent = today's behavior; ephemeral =
  honest no-op with the reply still sent.
- helper.py's existing 7770 handlers stay (PD's `helper …` route keeps
  working — deployed fleet migrates on aliases, §13).
- simfleet: same verbs at protocol level with `/os/rev` replies.
- dashboard osc_bridge: flip the admin-verb row of the LEGACY_COMPAT
  matrix to `/os/*` and consume `/os/rev` (surface converged sha per
  device — the "update all and watch them come back" story).

Verify in simfleet: dashboard update-all → every device replies /os/rev
with the bumped sha; a device with a dead engine still answers (helper
owns the verbs, not PD).

When this ties, the parent `osc-schema-contract` goal stitch can tie with
it (its done-bar is already met; Bob's PD edits in `pd-edits-for-bob.md`
are tracked there and don't block — aliases keep both spellings working).
