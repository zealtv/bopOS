# Verification

Passed on 2026-07-30:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_value_box_component.py
19 checks passed, 0 failures

./tools/run-tests.sh fast
Ran 250 tests — OK

./tools/run-tests.sh browser
19/19 browser verifiers passed
```

`tests/verify_value_box_component.py` grew from 12 checks to 19: the textfield
face on static, dynamically-rendered and drawer-classed fields; `ArrowUp` and
`ArrowDown` still stepping an integer box; and two source-level checks that the
component owns the WebKit pseudo-element rule and that no surface re-scopes it.

Mutation-tested rather than assumed: with the two `appearance` declarations
removed from `value-box.css`, the three face checks fail with `auto` and the
suite reports `16 checks passed, 3 failures`. Restored and re-run green.

`fast` is fully green at 250. Both tests CLAUDE.md lists as known-red passed
this run — `45-device-enabled-replay-red` is host-dependent and already fixed,
and the `47-live-param-kinds-flake` slider assertions passed under full-suite
load this time, which is consistent with it being an intermittent race rather
than anything this stitch touched.

## Not verified

**The arrows' visual absence was not observed.** Headless Chromium does not
paint the native spinner, and no DOM or pixel assertion can see it (see
`decisions.md`) — the verifier pins the declaration that removes it, which is a
weaker claim than "Bob no longer sees arrows." Confirming that is a look at the
Control, Patches, Seats and Show tabs in a real browser. Firefox's rendering of
`-moz-appearance:textfield` is likewise unobserved.

No physical device, iPad/touch, Pure Data, audible or hardware verification was
performed. This stitch changes CSS presentation only.
