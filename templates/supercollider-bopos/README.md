# bopOS SuperCollider starter patch

This is the text-native twin of the Pure Data starter kit. Copy this directory
into `patches/<name>/`, select the patch, and bopOS launches it as:

```sh
sclang patches/<name>/main.scd
```

The manifest declares `sclang`, not `scsynth`, because bopOS's launcher runs
`<engine> <entrypoint>`. `main.scd` is language code: it boots and controls the
default synthesis server, installs OSC responders, and stays alive. A bare
`scsynth` process cannot interpret this entrypoint.

## The patch-side seam

The framework provides values; this patch decides what they mean:

| Receive port | Message | Template behavior |
|---|---|---|
| 6661 | `/os/master <0..1>` | Smooths and multiplies the final mix in `boposOut`, immediately before hardware output. |
| 6661 | `/p/<name> <value>` | Updates the manifest-declared patch parameter. |
| 6661 | `/id <id>` | Reports the resolved device identity to the patch. The template requests it from helper after opening its socket. |
| 6661 | `/pt <pointId> <element> <value>` | Stores the shaped scalar by point and 0-based element. The example maps point 0 to element amplitude. |
| 6661 | `/cue <cueId>` | Runs a named action after helper has handled absolute clock synchronization. |

Port 6660 remains the LAN control port, owned by helper and the PD routing layer.
SuperCollider cannot reliably join an already-bound 6660 socket, so helper
matches the fleet selector and relays master and patch values to non-PD engines
on localhost port 6661. Points, cues, and identity already use that channel.
This keeps selector/transport mechanics out of the patch and works without a
second LAN listener. The macOS multi-instance port question remains explicitly
gated by the audition-rig spike.

`main.scd` runs one engine instance per device. It creates element Synths lazily
from the 0-based element index in `/pt` and maps each element to the matching
output channel. Increase the server's output-channel setting for devices with
more hardware outputs. Assignment geometry and falloff are framework concerns;
the patch receives only the shaped scalar.

## Minimal correctness

A production patch should retain these four properties even if it replaces all
example synthesis:

1. Route every final signal through one master mix stage and smooth master
   changes to avoid clicks.
2. Keep patch parameters patch-owned; never multiply master into the stored
   `gain` value.
3. Treat point values as optional, full-state inputs per element.
4. Treat `/cue` as an already-scheduled relative fire; never put absolute time
   inside the audio engine.

Ignoring a provided term is legal. Ignoring master means the patch plays but is
not master-controllable. Ignoring points means it plays without bopOS spatial
behavior. Ignoring cues means named fires do nothing. Framework mute remains
below the patch and requires no SC handler.

## Extending the example

- Add a declaration to `bopos.patch.json`, its initial value in `~bopos.params`,
  and its name in `installParamRoutes`.
- Register cue functions in `~bopos.cues`, keyed by the string cue ID.
- Read `~bopos.points[[pointId, element]]` or change the `/pt` responder to map
  proximity to filter, density, spatialization, or another patch concern.
- Use `BOPOS_ASSETS` from the environment for framework-landed media.

The pending PD equivalents (`bopos.out~`, `bopos.point`, and `/cue`) remain in
[`../../.notes/pd-edits-for-bob.md`](../../.notes/pd-edits-for-bob.md); agents do
not edit `.pd` files.
