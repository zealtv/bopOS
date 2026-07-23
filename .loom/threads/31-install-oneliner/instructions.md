# 31-install-oneliner

**FEATURE / docs+tooling.** Condense the Raspberry Pi setup into a **single
copy-pastable line** in the README, on the way to a **`curl`-referenced install
script**: paste one line into a fresh Pi's SSH session and everything needed gets
installed. It's fine for it to prompt for authentication.

Bob, 2026-07-23: "On the README I'd like to condense the instructions for setting
up a Raspberry Pi into a single copy-and-pastable line, so you can copy one piece
of text, SSH into a Pi, run that pasted text, and install everything you need.
It's okay if it asks for authentication. What we're aiming for is to turn that
into a bash script that can be referenced by curl — a one-liner that just points
to an installation bash script."

## Target shape

- An explicit **`install-device.sh`** at the repo root that runs the full first-time device
  setup end to end: system deps, the venv + `python/requirements.txt` (post
  `30-gdown-retirement`, so no stale `gdown`), the clone/checkout, and the
  privileged `bash/provision.sh` step. Auth prompts (sudo, git creds) are
  acceptable.
- A README one-liner of the `curl -fsSL <url> | bash` shape (or
  `bash <(curl …)`) so a fresh Pi is one paste away from installed. The current
  multi-step `docs/INSTALL.md` flow is the source of truth for what it must do —
  fold it in, don't contradict it.

## Consolidate from what exists

`docs/INSTALL.md`, `bash/provision.sh` (privileged, installs root-owned files),
`bash/install-power-control.sh`, `bash/update.sh` (convergence), `bash/rc.local`,
the venv/requirements dance in `dashboard/README.md` / CLAUDE.md. The one-liner
should compose these, not reinvent them.

## Cross-thread

- **USB auto-mount** belongs to the logging seed (`35-node-logging`) by Bob's
  call — but the *install action* that sets up automount lands here. Wire the two
  together when both are ready; note the dependency, don't duplicate the design.
- Do this **after `30-gdown-retirement`** so the installed requirements are
  already clean.

## Constraints / cautions

- For now, host the script at the repository's raw GitHub URL. Keep the laptop
  environment installer explicitly named `install-dashboard.sh`; do not infer
  which machine is being installed.
- Idempotence: re-running the one-liner shouldn't wreck an existing node.
- Real verification needs a fresh Pi (Bob/rig gate) — a fresh flash is exactly
  the case `29-fleet-patch-sync-hang` is chasing; don't claim end-to-end verified
  without hardware.
