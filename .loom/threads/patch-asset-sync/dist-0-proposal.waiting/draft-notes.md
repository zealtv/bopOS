# dist-0-proposal working notes

Contract facts pinned before the survey results (from docs/OSC-CONTRACT.md):

- §7: provisioning verbs exist and reply `/os/rev <sha> <model>`:
  `/os/update` (git pull + reboot today), `/os/checkout <branch>`,
  `/os/patch <name>` (switch), `/os/addpatch <user> <repo>` (git),
  `/os/pullpatch`.
- §8: `bopos.patch.json` is the ratified manifest — `engine` + `entrypoint`
  fields already exist, so "must it be main.pd?" is answered by contract: no.
  Open: what the implementation still hard-codes, and whether `bopos.config`
  is legacy alongside the manifest.
- §9: `/os/fetch <source-uri> <slot>` → `/os/fetched <slot> <ok|err>`;
  `http:` scheme = dashboard-served LAN manifest+hash with Range resume;
  landing `~/bopOS/assets/<slot>/`, delivered via run context
  (`bopos-context assets` / `BOPOS_ASSETS`).

Design tension to resolve: Bob's "host assets/ dir mirrors the Pi, send
overwrites" vs §9's slot model. Likely reconciliation: slots == top-level
asset directory names; "send" is dashboard-initiated fetch. Patch send for
non-git folders can ride the same manifest+hash HTTP machinery pointed at a
patches root — additive, no new transport.

Survey results from subagents land below / in survey-*.md files.
