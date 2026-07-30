# Verification

Passed on 2026-07-30:

```text
./tools/run-tests.sh fast
Ran 255 tests — OK      (250 before; the guard adds 5)

./tools/run-tests.sh browser
19/19 browser verifiers passed
```

The guard is browser-free and runs in `fast`, as the instructions required. No
new dependency: no stylelint, no CSS parser.

## It catches the defect it was written for

Verified by **reverting `05c` and re-running**, not by trusting fixtures:

| control-panel.css | result |
|---|---|
| current (`05c` applied) | green |
| `05c` reverted — 68 host-scoped drawer rules | **red, 51 rules** (first version) |
| `05c` reverted, after the right-to-left fix | **red, 66 of 68** |

The two undetected rules set only `justify-self` and `position/bottom/right` —
positioning, which `POSITIONING` deliberately permits. So coverage of the
historical defect is 66/66 of the rules that the guard is *supposed* to flag.

That revert is also what exposed the two bugs recorded in `decisions.md`: the
first working version reported the reverted file as clean, because splitting the
selector list on every comma broke `:is()` and the resulting host
(`.show-inspector-section`) was unregistered. A self-test written from memory
passed throughout. The self-tests now assert the **verbatim** shipped selector.

## Self-tests

`test_detects_the_shapes_it_was_written_for` covers the `05b` and `05c` shapes.
`test_does_not_flag_legitimate_rules` covers the four ways a rule is fine: a
component styling itself, the panel styling its own control through a class that
is *also* a host (`.live-card .live-param-mod` — the case that makes this guard
non-trivial), a surface positioning what it hosts, and a bare-element subject.

`test_allowlist_entries_still_apply` and `test_allowlist_entries_name_an_owner`
guard the allowlist itself against rotting into a silent suppression.

## Not verified

The guard reads CSS **source**, so it cannot see runtime-attached classes
(`PrecisionField` adds `.value-box` in JS) or surfaces absent from the registry.
Both limitations are documented in the test file and in `decisions.md` rather
than left to be discovered by whoever trusts a green run too far.

No rendered output was checked, because nothing rendered changed: this stitch
adds a test and touches no CSS, JS or markup. The ten pre-existing violations it
found are allowlisted and owned by `05f-component-face-divergences`.
