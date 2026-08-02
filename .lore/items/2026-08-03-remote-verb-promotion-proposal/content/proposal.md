# Remote verb promotion

## Outcome

Add a venue-scoped **Remote device commands** editor beside the patch manifest
editor. It writes the existing `installation.json.facilitator_commands`
allowlist; it does not add verbs to `bopos.patch.json`.

This satisfies the request where it was looked for while preserving the
ratified ownership rule: a patch promotes its own parameters and events; a
venue promotes framework verbs such as reboot and shutdown.

## Why this shape

The runtime capability already exists. The Remote view renders the configured
allowlist as a venue-wide `Fleet setup` row and as per-seat `Device setup`
commands. Destructive commands already use hold-to-confirm. What is missing is
an application path for editing the allowlist; today it requires hand-editing
`installation.json`.

Moving promotion into the patch manifest would make portable content arm
destructive venue controls, make command availability change with the loaded
patch, and change the patch fingerprint whenever an operator toggles a Remote
command. Those are ownership and deployment regressions, not necessary costs
of the requested UI.

## Proposed interface

In the Patches tab, place a separate card immediately beside or below the
manifest editor:

> **Remote device commands**  ·  **venue setting**
>
> Choose framework commands available from Remote. This setting is not saved
> in the patch and does not deploy to devices.

Offer the four framework verbs already accepted by the state model:

- Restart engine
- Update bopOS
- Reboot
- Shutdown

Use ordinary check controls and one explicit save action. Preserve a fixed,
reviewable display order rather than mixing these rows into manifest parameter
order. The Remote surfaces and their confirmation behavior do not change.

The card remains visible independently of which patch is selected so its
venue scope is not merely a label. It may sit in the same authoring region for
discoverability, but it must not appear inside the manifest document/card or
participate in manifest save, reorder, dirty state, fingerprinting, or deploy.

## Storage and application path

Add one dashboard mutation, provisionally:

```json
{"type":"set_facilitator_commands","data":{"commands":["restart-engine","reboot"]}}
```

The server filters through the existing `FACILITATOR_COMMANDS` allowlist,
deduplicates using `InstallationState.clean_facilitator_commands`, persists the
installation state, and broadcasts the resulting public state. Invalid values
must not be silently turned into a destructive command. The implementation
should return an operator-visible error if persistence fails and leave the
prior allowlist in force.

This is an application path over an existing ratified field, not a new OSC
plane and not a contract change.

## Desktop boundary

The allowlist continues to gate only the simplified Remote surface. The
desktop Devices tab retains its unconditional Actions section and the Control
card retains its `Device setup…` handoff to that tab. This keeps the existing
D8 model: a desk operator has the full administrative surface; a carried
Remote exposes only the venue-approved subset.

## Verification after ratification

- Browser-free state/server tests for filtering, ordering, persistence,
  rollback on save failure, and public-state broadcast.
- A Patches-tab browser journey proving the card is visibly venue-scoped,
  independent of manifest selection/save, and survives reload.
- A Remote journey proving enabled commands appear in fleet and per-seat
  locations, disabled commands do not, and existing confirm/hold behavior is
  unchanged.
- No patch fingerprint, deployment, OSC-contract, hardware, or Pure Data
  change.

## Rulings requested

1. **Placement and ownership:** approve the recommended venue-level sibling
   card in the Patches tab, rather than moving this setting to a general venue
   settings surface or moving ownership into the manifest.
2. **Meaning of “as remote parameters”:** confirm framework verbs remain in
   Remote's existing `Fleet setup` / `Device setup` sections and are not
   interleaved or drag-ordered among patch parameter rows.
3. **Desktop scope:** confirm the allowlist gates Remote only; the desktop
   Devices Actions remain unconditional and Control keeps its Devices-tab
   handoff.
