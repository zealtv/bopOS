# PD edits for Bob — boundary-4 rewrite wave

## 2026-07-24 — `to-bopos-log` bus (node logging, thread 42)

The ratified logging design (`.loom/threads/42-node-logging/` — proposal +
decisions in `1-logging-seed-design`) adds one engine-sent term:
`/log <stream> <values…>` on localhost 7770, next to `/store`/`/report`/
`/admin`. The PD-side bus is Bob's edit, same pattern as `to-bopos-admin`
and `to-bopos-report`:

- Add `[r to-bopos-log]` in `pd/bopos.pd` feeding an OSC
  `/log <stream> <values…>` message into the existing localhost **7770**
  request `netsend`.
- A patch sends `stream value…` on the bus, e.g. `[presses 1071.5(` →
  `[s to-bopos-log]`; the abstraction wraps it as `/log presses 1071.5`.
- Stream names are `[A-Za-z0-9_-]+`; bopos.py drops invalid names with a
  logged warning, never fatally. The node stamps each entry at receipt —
  patches never send absolute time. Interval-vs-raw-events encoding is the
  patch author's choice (ratified Q6): a computed ms interval is safe to
  ~100 s at PD float precision; raw events get node-exact timestamps.
- No reply to the engine; fire-and-forget like `/store`.

The Python side lands in stitch `2-nodelog-facility`; the bus edit can
happen before or after — an unconsumed `/log` before that stitch is simply
an unknown message on 7770.

## 2026-07-23 — completed multi-asset-slot context

Thread `32-multi-asset-packs/1-context-list-design` changes the
launch context from one assets-root symbol to a list of absolute asset-slot
folder paths:

```text
bopos-context assets <absolute-slot-path-0> ... <absolute-slot-path-N>
```

Bob completed the `.pd` side on 2026-07-23 and ruled that each top-level folder
remains an **asset slot**; "asset pack" is not a distinct term.

- `pd/bopos~.pd` no longer rebuilds or publishes the old scalar
  `bopos-assets-path`.
- No replacement plural bus was added. The template consumes the canonical
  `[r bopos-context] -> [route patch assets]` surface directly.
- `patches/.templates/bopos-template.pd` preserves and displays the complete
  assets list and its length.
- Bob confirmed in the local patch editor that zero, one, and two host asset
  slots produce list lengths 0, 1, and 2.
- The same PD pass completed the pending live `groups` route and added
  `clip~ -1 1` immediately before both output channels.

The launcher escapes PD/FUDI atoms before constructing `-send`, so the
template receives already decoded absolute paths.

This supersedes the 2026-07-14 `demo-pd asset-context landing` note below: the
value is no longer one framework assets-root symbol. No further asset-context
PD work is pending.

## 2026-07-20 — Seat-group membership on the bopos-context bus (engine group-context amendment)

The Python side is live and verified: `bopos.py` now pushes the node's
current Seat-group membership to the engine at launch (via `-send`, same as
seed/run-id/version/patch-fingerprint) and again after every successful,
durably-persisted membership change while the engine is running (group
sync, and the durable clear on assignment-to-a-different-Seat and on
unassignment). Live updates arrive as a plain OSC message on the engine
port (6661): `/groups <int...>` — one selector-stripped message, exactly
like `/id <n>` already does. Shape is sorted OSC ints in canonical order,
or the single sentinel integer `-1` alone when the node has no membership
(never an empty arg list).

The wire target is the same `bopos-context` bus other context values land
on, with shape `bopos-context groups <int...>`. Bob completed this `.pd`
edit on 2026-07-23 alongside the multi-asset-slot/template pass; the wiring
description below is retained as the completion record.

**Where:** `pd/bopos~.pd` (root canvas), the `[route id os audition]`
object at roughly (51, 225), which is what turns the incoming `/id <n>`
message into `id $1` on `[s bopos-context]`.

**What to change**, mirroring the existing `id` branch:

1. Extend the route list: `[route id os audition]` → `[route id os
   audition groups]`. This adds outlet 3 for a `groups` match and pushes
   the reject/passthrough outlet from index 3 to index 4.
2. Rewire the existing reject connection (currently outlet 3 → `[route p
   pt cue notify]`) to come from the new outlet 4 instead — the `id`/`os`/
   `audition` matching behavior must stay exactly as it is today.
3. New outlet 3 (the `groups` match) carries the list of ints after
   `oscparse` + `[list trim]` has already stripped the leading `groups`
   address token — i.e. just `<int...>`, or `-1` alone. Because the arg
   count varies, reformat with `[list prepend groups]` (the same technique
   already used for `assets` in the `build-assets-path` subpatch) rather
   than a fixed-arity `msg` box like the `id $1` one. Feed that into the
   existing `[s bopos-context]`.

Net result: a patch that already has `[r bopos-context]` → `[route seed
run-id patch assets id version patch-fingerprint]` can extend its route
list with `groups` to receive `<int...>` (or `-1`) both at launch and live
on every membership change, with no other wiring changes.

No consuming reference patch (`demo-pd`, `bonks-pd`) currently reads
`groups` off the bus; wiring a route arm there is optional/demonstrative,
not required for the framework side to work.

## 2026-07-17 — engine admin requests + version context (contract v1.7)

The v1.7 amendment adds a bounded engine-sent admin surface. The Python side
is live and verified; the PD-side bus is the one edit Bob owns.

### Add the `to-bopos-admin` bus to `pd/bopos.pd`

- Add `[r to-bopos-admin]` feeding an OSC `/admin <action>` message into the
  existing localhost **7770** request `netsend` (the same one `/config`,
  `/store`, `/load`, and `/report` use).
- A patch sends the bare action symbol on the bus:
  `[update-patch( / [update-bopos( / [shutdown( / [reboot(` →
  `[s to-bopos-admin]`. The abstraction wraps it as `/admin <action>`.
- bopos.py accepts exactly those four actions and routes them to the same
  code paths as the dashboard verbs; anything else is logged and ignored, so
  a typo'd action is safe. There is no reply to the engine — the actions are
  terminal or restart the engine anyway.
- This supersedes the A4 sentence below ("Engines may not request update,
  reboot, shutdown…") for exactly these four actions. Everything else A4
  deleted stays deleted: no generic admin chain, no checkout, no
  restart-engine, no patch switching from the engine.

### Version context — no PD edit required

The launcher's `-send` now also delivers `version <string>` and
`patch-fingerprint <string>` on `bopos-context`, alongside seed/run-id/
patch/assets/id. Patches opt in by extending their existing route:
`[r bopos-context]` → `[route seed run-id patch assets id version
patch-fingerprint]`. Both are symbols, never floats. `patch-fingerprint`
reads `unknown` until the node's background patch warm has run once after
boot (the warm is in place as of 2026-07-17; a fresh clone's very first
launch may still say `unknown`).

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
- Patch lifecycle callbacks now send `/notify updatepatch` before pulling or
  switching the active patch. The reference patch's `bopos-notify` route should
  recognize the bare `updatepatch` symbol for Bob's audible replacement cue.

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
  **Amended 2026-07-17 (contract v1.7):** the four actions `update-patch`,
  `update-bopos`, `shutdown`, `reboot` are now allowed via the dedicated
  `/admin` request — see the 2026-07-17 section at the top. The generic
  admin chain stays deleted.
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

## Event-plane receiver adoption (thread 44 child 5)

Python now delivers scheduled events to the engine as selector-free,
time-free `/e/<identity> [<e0> [<e1> [<e2>]]]` messages. Update
`pd/bopos~.pd` and `pd/babs.blineseq.pd` to route `/e/<identity>` alongside
the existing `/cue` receiver. Preserve nested identity segments and arity
0–3; event elements are 32-bit OSC floats. Absolute shared nanosecond time
must remain in Python and must never enter Pure Data. Keep `/cue` working
until thread 44 child 4 retires that plane.

No `.pd` file was changed for the event-plane wire implementation.
