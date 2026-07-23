# 1-install-script

Produce `install.sh` + the README `curl` one-liner. One concrete deliverable;
split only if it grows a design decision Bob must gate (e.g. where the script is
hosted).

## Do

1. Read `docs/INSTALL.md` and the existing `bash/` setup scripts; list every
   step a fresh Pi actually needs from bare flash to a running node.
2. Write `install.sh` that performs them idempotently, composing
   `bash/provision.sh` / `install-power-control.sh` / `update.sh` rather than
   duplicating them. Auth prompts (sudo/git) are allowed.
3. Add the README one-liner (`curl -fsSL <url> | bash` shape) and point
   `docs/INSTALL.md` at it as the fast path, keeping the manual steps as the
   fallback/explanation.
4. Surface the hosting-URL decision to Bob (where the raw script lives).

## Defer / coordinate

- USB auto-mount setup is designed in `35-node-logging`; leave a clear hook here
  and wire it in once that lands.
- Depends on `30-gdown-retirement` being done first (clean requirements).

## Verify

- Lint/`shellcheck` the script; dry-run what can be dry-run off-Pi.
- End-to-end is a fresh-Pi gate (Bob/rig) — state that plainly.
