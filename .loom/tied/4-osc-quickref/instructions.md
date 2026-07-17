# 4-osc-quickref

Write the complete OSC message quick-reference Bob asked for (2026-07-17):

> "A clear list of the available OSC messages that you can send. For example
> from a computer running OSC, you should be able to look at this list and
> see that I can send shutdown messages or reboot messages or update the
> patch. You should see the complete message that you need to send to do
> that for all of the available OSC messages from all senders and receivers,
> so a really clear table. If I need to, for example, mute a device and I
> don't have the dashboard in front of me, I need to be able to look at that
> list and understand the message that I need to construct to send a mute
> message and which port I need to send it to."

Do this AFTER 1–3 are tied so the new `/admin` and run-context items are
included.

## Shape

- New durable doc `docs/OSC-REFERENCE.md` (linked from README's technical
  route, from `docs/PORTS.md`, and from OSC-CONTRACT.md as the quick
  reference; the contract stays normative).
- One table per plane/direction, each row: **complete example message**
  (address + typed args, e.g. `/all/os/to <uid> mute 1`), destination port +
  host (LAN broadcast vs unicast vs localhost), sender → receiver, what it
  does, what reply to expect and where it arrives.
- Cover every message a human with a bare OSC client can usefully send:
  the full 6660 command surface (assign, unassign, mute both spellings,
  ping, report, identify, probe, hostname, patches/assets verbs, cues,
  points, master, update, checkout, shutdown, reboot, groups …), the 5550
  replies/heartbeats they should expect, the engine-facing 6661 surface,
  and the engine-sent 7770 requests including the new `/admin`.
- Source of truth: `docs/OSC-CONTRACT.md` + the actual handler tables in
  `python/bopos.py` (the LAN dispatch in `handle_lan_datagram` /
  `dispatch_admin_verb` / the admin-verb allowlist, and the 7770 callback
  map). Where the code and contract disagree, flag it in the stitch notes
  rather than papering over it.
- Include a tiny "worked examples" section: mute one device, reboot one
  device, update the patch — exact bytes-on-the-wire-level commands, plus
  one example using a common CLI (e.g. `oscsend`) so a reader can act
  without the dashboard.
- Plain language, short labelled sections (Bob's docs style ruling).

Verification: cross-check every row against the code paths named above;
walk at least the mute and report examples against `tools/simfleet.py`
live to prove the spellings are real. Record the check in the stitch.
