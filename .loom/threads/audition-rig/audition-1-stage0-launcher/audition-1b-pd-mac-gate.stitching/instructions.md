# audition-1b-pd-mac-gate

External gate for completing audible Stage 0 on the Mac.

The tied macOS port spike proved stock PD 0.55.2 cannot run N instances with
each binding LAN port 6660. The audition relay child owns 6660, matches each
virtual node selector, strips it, and forwards to a distinct localhost port.
Current `pd/bopos.osc.pd` cannot consume that delivery because both
`netreceive` ports are fixed at object creation and no startup receiver can
retarget them. Agents never edit `.pd` files.

Bob-owned PD work, also indexed in `.notes/pd-edits-for-bob.md`:

- Add an audition startup control (recommended symbol:
  `BOPOS_ENGINE_PORT <port>`) which sends `listen <port>` to an initially
  unbound UDP binary `netreceive` feeding the selector-free local engine
  surface.
- Keep normal node behavior unchanged when the startup value is absent.
- The local surface must carry the rewrite-wave `/p/*`, `/os/master`, `/pt`,
  `/cue`, and `/id` messages into the same patch-visible routes used on a real
  node. Do not re-apply fleet selector routing locally; the relay already did
  it for one virtual node.

After Bob's edit, claim this stitch and verify on the composition Mac:

1. Launch three real default-patch PD instances through `tools/audition.py`
   (or its shipped launcher), each with a distinct id/uid and local port.
2. Use `-nogui -pa` first; confirm all three open the same CoreAudio stereo
   output without PortAudio/device errors and are audibly summed. JACK is not
   installed and is not a prerequisite unless this direct route fails.
3. Run the real dashboard and exercise fleet-wide plus selector-specific
   master/parameter/identify control. Confirm all three virtual nodes remain
   distinguishable despite sharing one host IP.
4. Stop through the launcher and confirm no owned `pd` or `pd-watchdog`
   processes remain. Never blanket-kill an unrelated live PD session.
5. Retain exact commands, logs, dashboard evidence, audible result, and any
   unverified limitations here before tying.

Blocker: waiting for Bob's `.pd` receiver edit and an interactive audible Mac
run. Do not claim the parent Stage 0 or listener-puck stitch as complete until
this gate is tied.
