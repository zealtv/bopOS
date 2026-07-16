# PD edits for Bob — boundary-4 rewrite wave

## 2026-07-15 — nested patch parameter routes

The parameter-address design now preserves true nested OSC from the fleet into
the engine. The target behavior is:

```text
/all/p/track1/fx/distortion 0.5   fleet input
/p/track1/fx/distortion 0.5       selector-stripped engine input
p track1 fx distortion 0.5        after [oscparse]
track1 fx distortion 0.5          bopos-param after [route p]
```

`pd/bopos.pd` already appears to have the correct framework behavior: its
existing `[oscparse] -> [route p] -> [s bopos-param]` chain preserves every
parameter path segment after removing only the `p` plane. Do not flatten the
path into one symbol.

When a concrete patch adopts a nested manifest declaration, update its consumer
from a flat route such as `[route distortion]` to the corresponding hierarchy,
for example `[route track1] -> [route fx] -> [route distortion]`. Existing flat
manifest parameters and routes remain unchanged.

Audible verification should send the exact nested address above to the engine
port and confirm the final parameter changes. No `.pd` edit is required merely
to amend the contract; Bob chooses and edits the first concrete nested patch.

## 2026-07-13 — audition matrix validator follow-up

`pd/bopos.audition~.pd` previously reset only the final `[spigot]` before
feeding a four-atom candidate through `[unpack f f f f]`. A symbol in matrix
slots 1, 2, or 3 therefore leaves a stale numeric value in the corresponding
cold `[expr]` inlet, allowing a malformed matrix to be applied partially.

Before every candidate, reset all four validation values to an invalid numeric
sentinel. In the existing `[pd validate]` subpatch:

- change the reset message from `[0(` to `[-1 -1 -1 -1(`;
- disconnect that message from the validation `[spigot]`'s control inlet;
- connect it to the validation `[unpack f f f f]` inlet instead.

Keep the existing `[t l l b]` ordering. Its bang resets all four values first,
the second list validates the candidate, and the first list reaches the data
spigot last. The existing range expression rejects every retained `-1`, while
a symbol in coefficient 0 cannot retrigger the expression and the gate stays
closed from the reset evaluation.

Retest a valid matrix plus a symbol independently in each of the four matrix
positions. Every malformed frame must retain the complete last-valid matrix.
Bob completed this edit and audibly confirmed all four cases on 2026-07-13.

This is the live, Bob-owned edit list. The earlier 2026-07-11 rewrite is
complete but is now superseded by the ratified engine boundary in
`.loom/tied/engine-boundary-ratification/ratification.md`. Agents must not edit
`.pd` files.

## 2026-07-14 — demo-pd asset-context landing

`patches/demo-pd/main.pd` already receives `bopos-context`, but it does not yet
route or demonstrate the launch-delivered asset root. Make that context visible
without restoring the retired patch-level `bopos.config`/`SAMPLEPACKSURL`
mechanism:

- connect `[r bopos-context]` to `[route seed run-id patch assets id]`;
- take the `assets` outlet as a symbol containing the framework-owned assets
  root (the parent directory whose children are the sent asset slots);
- store/publish that symbol under an explicit patch-local name such as
  `demo-assets-root`, and demonstrate constructing
  `<assets-root>/<slot>/<file>` before passing a media path to a loader;
- do not assume a `samplepacks` slot or recreate
  `patches/<patch>/bop/samplepacks`; `demo-pd` currently declares `"slots": []`
  because its shipped synthesis needs no assets;
- preserve the other context terms for demonstration: seed and run-id are
  opaque launch facts, patch is the active patch name, and id is the resolved
  device identity.

Bob should choose the concrete media loader and example asset only when the
demo has a real teaching asset to ship. Until then, routing and exposing the
root is sufficient; no fake file path should be baked into the patch.

## Gate status

- Python relays the common selector-stripped 6661 surface to PD: proven.
- The systemd helper-death/mute gate recovered control in at most 2.191 s on
  `bop000`; audible silence and resume were confirmed without restarting PD or
  JACK: proven 2026-07-12.
- Therefore PD's temporary direct 6660 path may now be removed in this wave.
- Do not add `/helper/*` compatibility, a leased probe, meter streaming, or a
  replacement for deleted report presentation metadata.

## A. Replace `pd/bopos.osc.pd` with `pd/bopos.pd`

Build `[bopos]` as the transport-owning façade. This is a clean break; do not
leave a compatibility copy named `bopos.osc.pd`.

### A1. One configurable engine ingress

- Delete the fixed `netreceive -u -b 6660` and all post-6660 selector logic:
  `route all`, `route-by-id`, `r ID`, and per-selector identity routing.
- Consolidate the current fixed 6661 and audition-only ingress into one binary
  UDP `netreceive` whose default listen port is 6661.
- `BOPOS_ENGINE_PORT <port>` may override that default before/at launch for
  audition instances. Both default and override feed exactly the same
  selector-free router; there must not be a second production ingress.
- The common input is already selector-stripped. Route these exact messages:

  ```text
  /id <n>                         -> `bopos-context` as `id <n>`
  /os/master <0..1>              -> `bopos-master` as the bare value
  /p/<name> <values...>          -> `bopos-param` as `<name> <values...>`
  /pt <point> <element> <value>  -> `bopos-point` as all three values
  /cue <id>                      -> `bopos-cue` as the bare id
  /notify <event>                -> `bopos-notify` as the bare event
  ```

- Retire the temporary `/identify` special case. The accepted common spelling
  is `/notify identify`; the notification chirp may continue to listen to
  `bopos-notify`.
- Unknown common-surface messages may be printed for diagnosis, but must not
  be re-broadcast or forwarded as admin commands.

### A2. Context and old globals

- Replace patch-facing `ID`, `PX`, `PY`, `RANDOM`, `STARTDATE`, `STARTTIME`,
  and `ACTIVEPATCH` transport assumptions with the single `bopos-context` bus.
- In this wave, `/id` is the required runtime context item. Stage 5 will add
  atomic launch-delivered seed/run-id/patch/assets context; leave a clear bus
  landing point, but do not invent that later wire or launch mechanism here.
  - **Stage 5 landed (2026-07-12, no PD edit needed):** the launcher's `-send`
    now targets the `bopos-context` receive symbol directly with
    `seed <n>`, `run-id <s>`, `patch <name>`, `assets <path>` (alongside
    `[bopos]`'s own `id <n>`). Patches opt in with `[r bopos-context]` +
    `[route seed run-id patch assets id]`. The run id is an opaque symbol;
    never parse civil time out of it.
- Delete `[bopos]`'s boot-time `helper config` request. An engine that needs
  identity retries `/config` through the request surface described in A4;
  stage 5 owns the cross-engine retry implementation.

### A3. Keep IO transport separate

- Keep binary UDP input on localhost 6662, but publish decoded messages on
  `bopos-io` (rename `from-bopos-io`).
- Keep `to-bopos-io` -> OSC binary -> localhost 8880.
- Keep the existing dynamic IO message formatter (`report`, `create`, `poll`,
  and arbitrary device commands). Do not fold IO traffic into port 6661.

### A4. Engine-to-framework requests and reports

- Delete the entire `osc-in -> route helper -> process-helper-messages ->
  netsend 7770` admin chain. Engines may not request update, reboot, shutdown,
  restart-engine, patch changes, checkout, sample fetches, or other LAN admin.
- Provide a narrow localhost 7770 request path for only `/config`, `/store`,
  and `/load`. Its patch-facing send bus should be explicit framework intent,
  not the retired generic `osc-out` bus. If no current patch consumes
  persistence, only `/config` needs a façade trigger in this wave; do not
  invent persistence UI.
- Add `r to-bopos-report` -> OSC `/report <name> <values...>` -> localhost
  7770. Reports are demand-inspection state only; they have no meter role or
  presentation metadata.

### A5. Delete legacy reporting/debug transport

- Delete `osc-out`, the ID-prepending `/rpt` formatter, both 5550 broadcast
  `netsend`s, the echo gate/chain, `from-helper`, and helper-reply behavior.
- Delete the old generic `osc-in` and patch-facing abstraction inlet/outlet
  semantics. Patches consume the named `bopos-*` buses instead.
- `[bopos]` must never bind or send LAN ports 5550 or 6660.

## B. Update framework PD abstractions

### B1. `pd/bopos.out~.pd`

- Replace `r osc-in -> route os -> route master` with `r bopos-master`.
- Keep the 10 ms master ramp and default master of 1.
- Remove the `osc-in /os/mute` multiplier. Framework mute is enforced by
  Python at the hardware mixer (or engine-stop fallback); `/os/mute` is not on
  the engine-facing 6661 surface.
- Keep the `bopos-notify` chirp mixed after patch inputs so `notify identify`
  remains an audible install diagnostic.

### B2. `pd/bopos.point.pd`

- Rename its source from plural `r bopos-points` to singular
  `r bopos-point`.
- Preserve 0-based routing: `[bopos.point <point> <element>]` outputs the value
  from `<point> <element> <value>`.

## C. Rewrite the reference patch

Apply these edits to `patches/demo-pd/main.pd`; use the resulting spellings in
future PD starter patches.

- Instantiate `[bopos]`, not `[bopos.osc]`.
- Replace `r osc-in -> route gain` with `r bopos-param -> route gain`.
- Rename `r from-bopos-io` to `r bopos-io`; keep `s to-bopos-io`.
- Keep `r bopos-cue` and the `snap` diagnostic.
- Keep `[bopos.point 0 0]` and the two element buses.
- Delete the entire level snapshot/metro sender, `s osc-out`, and the stale
  `role:meter` annotation. Do not replace it with `to-bopos-report` unless a
  concrete demand-driven inspection need is specified later.
- Retain `[bopos.out~]` as the only final sink.

Search every shipped/reference PD patch after editing. These legacy symbols
must be absent from active patch code:

```text
bopos.osc  osc-in  osc-out  from-bopos-io  bopos-points
route-by-id  from-helper  role:meter
```

## D. Post-edit verification (agent-supported, Bob runs/hears)

Before D2, the supporting agent must normalize helper-to-engine lifecycle
notifications in `python/helper.py`. It currently emits legacy `/identify`,
`/update`, `/shutdown`, `/reboot`, `/checkout`, and `/restart-engine`
addresses. The ratified surface is only `/notify <event>`; fix the Python
producer and its tests rather than retaining those aliases in PD.

### D1. Static/headless assertions

The boundary-4 verifier should fail unless all of the following are true:

- `pd/bopos.pd` exists and `pd/bopos.osc.pd` does not.
- No shipped `.pd` binds 6660 or sends 5550.
- `[bopos]` contains one configurable ingress defaulting to 6661, plus the
  retained 6662 input and 7770/8880 request/IO outputs.
- The six incoming named buses and two outgoing buses use these exact names:
  `bopos-master`, `bopos-param`, `bopos-point`, `bopos-cue`, `bopos-notify`,
  `bopos-io`, `bopos-context`, `to-bopos-io`, `to-bopos-report`.
- The deleted legacy symbols above and admin verbs are absent from `[bopos]`.
- The default patch has no meter sender or `role:meter` annotation.

### D2. Production-style macOS N=1 gate

1. Ensure no previous PD process owns the test ports.
2. Launch one stock PD 0.55.2/CoreAudio default patch with `[bopos]` on its
   default ingress (6661), not an audition override.
3. Assert with `lsof` that PD owns 6661 and 6662, does **not** own 6660, and
   has no 5550 socket.
4. Send selector-free `/id 7`, `/os/master 1`, `/p/gain 0.75`,
   `/pt 0 0 0.5`, `/cue snap`, and `/notify identify` to localhost 6661.
5. Confirm ID/context routing, parameter delivery, point-controlled element-0
   sound on the left, the snap cue, and the identify chirp on both channels.
6. Send a representative `to-bopos-io` message and confirm its decoded OSC on
   8880. Send `to-bopos-report` test state and confirm `/report` on 7770.
7. Stop PD cleanly and confirm 6661/6662 are released with no `pd` or
   `pd-watchdog` process remaining.

The gate is N=1 deliberately. Multi-instance audition topology cleanup belongs
to stage 5. Record automated results and Bob's audible observation inside the
boundary-4 stitch before tying it.

## Asset-root cleanup after retiring the samplepacks compatibility path

The engine now exposes only the run-context asset root and no longer creates
`patches/<active>/bop/samplepacks -> assets/samplepacks`. When these abstractions
are next maintained, update their path templates to address top-level asset
slots directly:

- `pd/bop/bop.stream~.pd`: change `%s/samplepacks/$1/*/` to `%s/$1/*/` and
  `%s/samplepacks/bop_samplepack/*/` to `%s/bop_samplepack/*/`.
- `pd/bop/bop.sampler~.pd`: make the same two replacements.

No `.pd` file was changed by the Assets cache/compatibility repair.
