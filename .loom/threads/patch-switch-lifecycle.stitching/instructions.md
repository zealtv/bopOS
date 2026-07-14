# patch-switch-lifecycle

Make `/os/patch <name>` an observable engine-only patch switch on real and
simulated nodes.

- Stop and restart only the engine stack; never reboot the OS for a patch
  selection.
- Keep the helper alive throughout and emit the provisioning receipt only after
  the replacement engine has been launched.
- On receipt, refresh installed patches, active report, and parameter
  declarations so the dashboard cannot retain the previous patch surface.
- Show an honest switching state and describe the engine restart accurately in
  the confirmation copy.
- Update simfleet to model the same engine-only lifecycle.
- Add focused verification. Do not edit `.pd` files and do not broaden this
  stitch into the later fleet-wide UI simplification.
