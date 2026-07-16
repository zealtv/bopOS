# updatebopos-unattended

Repair the existing dashboard **Update bopOS** command so the unprivileged
background helper can complete it without interactive authentication.

Known root cause: `python/bopos.py` runs `bash/update.sh` as user `pi`, while
the legacy runtime path still executes `sudo cp ./rc.local /etc/`. A helper
without a terminal cannot satisfy that prompt. Separate privileged first-time
provisioning from routine framework convergence; do not broaden the narrow
power-control sudoers rule merely to preserve a legacy copy step.

Audit the complete update path as one operation, including the checkout's Git
remote/credentials, `git restore`, pull, submodules, active-patch preservation,
power-rule reuse and reboot. It must:

- never prompt for sudo, Git credentials or any other input;
- fail fast and honestly before reboot when pull/convergence cannot complete;
- preserve the active patch selection;
- reboot only after a successful framework convergence;
- expose enough status/receipt information to distinguish pull, authorization
  and reboot failures without adding explanatory dashboard prose.

Verify shell behavior locally with controlled fake commands, retain the fresh
root provisioning path, and finish with a Bob-triggered real `bop000` update.
