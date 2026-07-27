# 46-control-surface-probe-race

`tests/verify_control_surface_component.py` fails intermittently — roughly one
run in five — with

    TypeError: Cannot read properties of null (reading 'querySelector')

raised from `KIND_SHAPE_JS`. Found 2026-07-27 during
`desktop-ui-overhaul/01-control-panel/9-generator-drawer-panel`: it failed once
in a full-suite run, then passed 5/5 on the same tree and 4/4 on the tree
before that stitch's changes. It is not a regression from that work, and it is
not worth expanding a UI stitch to chase — hence its own thread.

## The mechanism (already diagnosed)

`ROW_GRAMMAR_JS` (around line 238) does

    document.querySelector(".live-card").appendChild(host);

to move the `#surface-probe` element inside a real live card, so the panel
stylesheet applies to the measurements. The facilitator's `renderCards()`
(`dashboard/static/js/facilitator.js`) then does

    $("#cards").innerHTML = cards.join("")

on the next heartbeat, which destroys everything inside the card — the parked
probe with it. `KIND_SHAPE_JS` (around line 333) later calls
`document.getElementById("surface-probe")` and gets `null`.

So the flake window is "did a heartbeat land between the two probe scripts",
which is why it is intermittent and why it got likelier as more probes were
added between them.

## The work

Make the probe survive, **without weakening what the test measures** — it needs
the panel stylesheet to apply, so the probe has to live inside a `.live-card`
(or somewhere that resolves the same tokens). Candidate approaches:

- hold the page's `interacting` guard for the duration of the probes (the
  render guard the precision field and drawer already use);
- re-append the host at the top of every probe script;
- park the probe in a container that resolves the panel tokens but is not
  inside `#cards`.

Prefer whichever leaves the test's *claims* untouched; this is a fixture
problem, not a coverage question.

Verify: run the file 10 times in a row, all green.

    ~/.venvs/bopos/bin/python tests/verify_control_surface_component.py

Then `tools/run-tests.sh browser` once, to confirm nothing else moved.
