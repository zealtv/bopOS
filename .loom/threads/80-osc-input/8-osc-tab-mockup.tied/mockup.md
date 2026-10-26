# OSC tab mockup (stitch 8)

Screenshots from the running app (real UDP sent to the input port, fixture patch `choir`,
two groups): `osc-tab-desktop.png` (1440 px), `osc-tab-phone.png` (390 px). Working code is
in the branch; stitch 9 finishes and tests it.

## What it shows (top to bottom, one card each)
1. **Send to**: dashboard IP and input port, each with a Copy button; a line saying which
   patch the page was generated from (fleet patch in Live/Simulation, edited patch in Patch Edit).
2. **Commands**: `/bop/master`, `/bop/mute`, `/bop/lead` with arguments.
3. **Events**: short address `/<target>/trig/play` and explicit `/<target>/e/trig/play`;
   each field with kind, range, default, "(optional)"; amber ⚠ when the short form is
   ambiguous (same identity as a parameter, or starts with `os`/`io`/`sync`/`e`/`p`).
4. **Parameters**: same two addresses, kind, range/options, default.
5. **Targets**: `all`, "a Seat number", and each group by name with its `g<id>`.
6. **Recent rejections and clamps**: newest first; time, sender IP, address, reason;
   clamps tagged `clamp` (cyan, modulation-colour reuse is deliberate: "something altered
   the value"), rejections with ⚠.

## Decisions
- Tab named **OSC**, last in the tab bar (after Assets).
- Server builds the reference (`osc_input.reference`) with the same ambiguity rule as
  `translate`, and ships it in the existing `state.osc_input` (new keys: `host`, `target`,
  `reference`). No new websocket type, so `SNAPSHOT_TYPES` stays as is.
- IP: `--public-url` host if given, else the outgoing-interface address found once by an
  unsent UDP `connect()`. It is not Remote's QR address (that comes from the browser URL);
  say if you would rather show that.
- Targets show `<target>` as a placeholder rather than one expanded row per target.
- Component CSS in its own `css/osc-reference.css`, `osc-` prefix; no new colours.

## Open questions for Bob
- Show the clamp/rejection list newest-first (as now) or oldest-first?
- Expand each address once per target (all, groups, seats) or keep the `<target>` placeholder?
- Show a "copy address" button on each row (not built)?
- On a phone the OSC tab sits off-screen in the scrolling tab bar, like Assets does today.
