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

## Land `bopos.config` at install (Bob, 2026-07-23)

A fresh Pi currently ships **no `bopos.config`** — confirmed on `new-bop`. That
absence is a root contributor to the mute bug (`29-fleet-patch-sync-hang`): no
`MIXER_CONTROL`, no sound-card identity for the runtime. **Create `bopos.config`
during installation with sensible defaults** (Bob: "make sure bopos.config lands
during installation … and should have sensible defaults" — "important for later
stitches"). Include at least the sound-card / mixer hint the mute path and
`33-device-audio-config` will read. Coordinate the schema with 33 (which writes
sound card + JACK rate/buffer from the Device tab) so install-defaults and
Device-tab edits target the same file/keys.

Also fold in **`bopos.service`** / boot management: today bopos starts via
`/etc/rc.local → su pi -c start.sh` with no systemd unit (Bob flagged this). Give
the install a proper boot mechanism. (Aside seen on `new-bop`: a cold-boot race
where the engine sometimes doesn't come up before the DigiAMP is ready — worth
addressing in the boot/service work.)

## Defer / coordinate

- USB auto-mount setup is designed in `35-node-logging`; leave a clear hook here
  and wire it in once that lands.
- Depends on `30-gdown-retirement` being done first (clean requirements).

## Verify

- Lint/`shellcheck` the script; dry-run what can be dry-run off-Pi.
- End-to-end is a fresh-Pi gate (Bob/rig) — state that plainly.
