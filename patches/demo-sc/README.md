# bopOS SuperCollider demo

This is the text-native twin of the Pure Data demo. Copy `patches/demo-sc/` to
`patches/<name>/`, give the copy its own name, and bopOS launches it as:

```sh
sclang patches/<name>/main.scd
```

The manifest declares `sclang`, not `scsynth`, because bopOS's launcher runs
`<engine> <entrypoint>`. `main.scd` is language code: it boots and controls the
default synthesis server, installs OSC responders, and stays alive. A bare
`scsynth` process cannot interpret this entrypoint.

## The patch-side seam

The framework provides values; this patch decides what they mean:

The engine listens on its assigned port: `BOPOS_ENGINE_PORT` from the
environment, defaulting to 6661 (the production value). Audition instances
each get their own port, so no instance attempts a fixed shared bind.

| Message | Demo behavior |
|---|---|
| `/os/master <0..1>` | Smooths and multiplies the final mix in `boposOut`, immediately before hardware output. |
| `/audition/matrix <l0> <l1> <r0> <r1>` | Applies the private fixed-stereo preview matrix with 20 ms smoothing before master. Exactly four finite numeric gains in `[0,1]` are required; a malformed frame leaves the last valid matrix active. |
| `/p/<name> <value>` | Updates the manifest-declared patch parameter. |
| `/id <id>` | Reports the resolved device identity to the patch. The demo retries `/config` on 7770 every two seconds until this lands. |
| `/pt <pointId> <element> <value>` | Stores the shaped scalar by point and 0-based element. The example maps point 0 to element amplitude. |
| `/cue <cueId>` | Runs a named action after the framework has handled absolute clock synchronization. |
| `/notify <event>` | Framework notifications (e.g. `identify`); the demo logs them. |

Port 6660 is the LAN control port, owned solely by the framework process.
It matches the fleet selector and relays the selector-stripped engine surface
to every engine on the assigned localhost port. This keeps selector/transport
mechanics out of the patch and works without a second LAN listener.

## Run context

bopOS generates run context in a bopOS-owned step and delivers it atomically
at launch through the environment: `BOPOS_SEED` (an integer, at most six
digits), `BOPOS_RUN_ID` (an opaque launch identifier — never parse civil time
out of it), `BOPOS_ACTIVEPATCH`, and `BOPOS_ASSETS`. A standalone
`sclang main.scd` run degrades to a self-generated seed and a
`standalone-*` run id rather than silence. The demo seeds sclang's
thread RNG from `BOPOS_SEED` so a fleet launch can be reproduced.

`main.scd` runs one engine instance per device. It creates element Synths lazily
from the 0-based element index in `/pt` and maps each element to the matching
input of the fixed-stereo final mix. Assignment geometry and falloff are
framework concerns; the patch receives only the shaped scalar. Higher channel
counts are outside the Wave 1 ABI rather than inferred from the audio device.

The Wave 1 audition boundary is fixed stereo. Its coefficient order is
`l0 l1 r0 r1`, rendering `L = x0*l0 + x1*l1` and
`R = x0*r0 + x1*r1`. Identity `[1, 0, 0, 1]` is installed before any preview
state arrives. The audition matrix is applied before the separately smoothed
production master, so preview movement cannot rewrite master or patch params.

## Minimal correctness

A production patch should retain these four properties even if it replaces all
example synthesis:

1. Route every final signal through one master mix stage and smooth master
   changes to avoid clicks. If audition is retained, apply its complete
   fixed-stereo matrix before master and keep identity as the cold-start state.
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

The Bob-owned PD follow-ups remain in
[`../../.notes/pd-edits-for-bob.md`](../../.notes/pd-edits-for-bob.md); agents do
not edit `.pd` files.
