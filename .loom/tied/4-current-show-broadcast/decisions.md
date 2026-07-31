# 4-current-show-broadcast — decisions

## The fix

Two broadcasts, both `await self.broadcast("state", await self.public_state())`:

* `set_current_show()` — covers `create_show`, `load_show`, `save_show_as` and
  `rename_show`, all four of which route through it;
* the `delete_show` branch that clears `current_show` inline without going
  through `set_current_show` at all.

**The enriched `public_state()`, not the bare `state.public()`.** This is the
one real choice in the stitch. A client replaces `installation` wholesale on
`state` (`dashboard.js:140`), and `state.public()` returns `self.data`, which
carries no `live_controls` — that key is added by `public_state()` onto a copy.
Broadcasting the bare snapshot would have made loading a show blank the Control
columns' parameter rows until the next enriched broadcast happened along. Thirty
of the server's thirty-three `state` broadcasts do use the bare form, so that
hazard is latent elsewhere; it is not this stitch's to fix, but it is worth
recording that it is there.

## The neighbour audit

The question the instructions posed — not "does it broadcast?" but "does it
broadcast the plane it just mutated?" — asked of every verb that writes
`state.data` and never broadcasts `state`:

| verb | mutates | broadcasts | verdict |
| --- | --- | --- | --- |
| `set_master` | `master` | `master` | fine |
| `mute_all` | `muted` | `mute_all` | fine |
| `set_listener` | `listener` | `listener` | fine |
| `set_room` | `room`, `points` | `points` | fine |
| `save_venue` | nothing in `state.data` | `venues` | fine |

Each one broadcasts the fact it changed on a plane a client actually handles.
`set_current_show` was the only omission: it broadcast three planes, none of
which carried `current_show` except the `shows` catalog's `current` field —
which is why `show-capture.js` reading that field was right all along, and why
the Monitor System panel reading `state.current_show` was reading the one thing
nothing ever sent.

`js/show-capture.js` is untouched, per the instructions.

## The guard

In `tests/verify_osc_transport_monitor.py`, which already drives the Monitor
dock and needs no simfleet. It is **behavioural, not structural**: it creates a
show and requires `[data-monitor-system="show"]` to name it, then deletes it and
requires the panel to say `none loaded` again — never that a particular message
fired. That is the failure mode `23-waveform-marker-guard-regression` found
three times, and the delete half is what covers the second, easily-missed
transition.

Confirmed to fail on the unfixed tree (`git stash` on `server.py`: the
`wait_for_function` times out), which is the only way to know a regression guard
guards anything.

## Also done here: two flaky helpers hardened

The `open_authoring` helpers `3-chrome-demotions` added to
`verify_preset_control_surface.py` and `verify_preset_editor.py` were written as
"click the summary if it is closed" and hit CLAUDE.md gotcha 16 under
full-suite load: `bindPresets` reassigns `ontoggle` on every heartbeat
re-render, so a click landing on an unbound disclosure opens it without the
component recording that it is open, the next re-render closes it, and the
action click that follows times out. Both now wait on the binding and on the
menu's contents. That is the `47` family, met in a helper this thread wrote
rather than in one it inherited.

## Verification

`fast` 260, and the full browser suite green on the final run (21/21).
Two intermediate full-suite runs each failed a *different* pair of journeys
that passed standalone immediately after, which is `47`'s signature and is
why the helpers above were hardened rather than shrugged at.
