# Decisions — 1-reference-foundation

## Reference envelope

Every cleaned Show message now carries an explicit `kind`: existing messages
normalize to `"osc"` and composition-content references use `"reference"`.
A reference message carries:

```json
{
  "kind": "reference",
  "reference": {
    "content": {
      "name": "patch-name",
      "fingerprint": "<64 lowercase hex>"
    },
    "schema": "sha256:<64 lowercase hex>"
  }
}
```

`content` is required; `schema` is optional at this foundation layer and is
available for the preset child. This keeps the mechanism about authored
content rather than presets while giving 09/2 both fingerprints in the
ratified location. An unhandled reference fails closed in `ShowEngine`; it is
never emitted as raw OSC.

## Portable group targets

Shows store a named group target as `group:<exact venue name>`. The prefix
keeps names distinct from `all`, decimal Seat ids, and legacy `g<id>`
selectors. Legacy `g<id>` targets still load and play as site-bound selectors;
new picker choices store names. At playback the dashboard injects resolution
into the transport-only Show engine, and only `g<id>` reaches the wire.

Name matching is exact and case-sensitive, matching the stored venue API.
Missing or ambiguous names are omitted from that send and produce derived,
non-blocking warnings at load and in the authoring picker. Other valid targets
in the same message still send.

## Group-name adoption

Group names are non-empty and exactly unique per venue. Create and rename
reject violations.

On current-state or venue load, old blank/duplicate names are repaired in
ascending group-id order:

- a blank becomes `group-<id>`;
- the first occurrence of an existing name keeps it;
- a later collision gets `-2`, `-3`, and so on, truncating the base to keep
  the existing 48-character limit;
- generated names avoid every original non-blank name, so an early repair
  cannot steal a later group's existing name.

The repaired document is persisted once. A runtime operator notice names every
rename; it is intentionally not persisted, so a fixed venue does not announce
the adoption again after restart.
