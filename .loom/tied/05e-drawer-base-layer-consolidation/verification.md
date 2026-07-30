# Verification

Passed on 2026-07-30:

```text
./tools/run-tests.sh fast
Ran 255 tests — OK      (includes 05d's ownership guard, still green on the
                         new stylesheet)

./tools/run-tests.sh browser
19/19 browser verifiers passed

python cascade_probe.py --doc dashboard   → cascade-dashboard.txt
python cascade_probe.py --doc facilitator → cascade-facilitator.txt
```

## Dashboard: zero rendered change

`cascade-dashboard.txt` — 27 computed properties on every drawer element, three
generator kinds, four contexts including the bare `<div>`:

| context | elements | differing |
|---|---|---|
| `live-card` / `device-control` / `show-inspector-section` / bare `div` | 39–49 each | **0** |

The desktop surface is untouched, which is the claim that mattered: the base
layer moved file and the overrides still win.

## Facilitator: three properties on one invisible element

`cascade-facilitator.txt` — the collapse, measured. **One** element differs, in
the `lfo` drawer only:

```
34:input.   height 38px -> 24px,  min-height 38px -> 24px
```

That is the visually-hidden checkbox inside `.live-gen-pill`
(`position:absolute; width:1px; height:1px; opacity:0; pointer-events:none`). It
is not the hit target — its `<label>` is — and its declared height is 1px, so the
change moves it toward its intent. **No tap target and no visible control
changed.**

This is the first measurement of the facilitator document's cascade at all;
`05c`'s probe hardcoded `style.css`.

## Not verified

- **No real iPad.** The probe runs Chromium at a desktop viewport, and the
  facilitator is a touch surface. The measurement says the drawer's cascade is
  unchanged there, which is a narrower claim than "the Remote view is fine on an
  iPad." That verification belongs to `feature-backlog/49-remote-ipad-restyle`,
  which is hardware-gated.
- **No `pointer:coarse` run.** The instructions asked for one. It would have
  measured the same rules with `--row-h` at 34px instead of 24px; the collapse's
  only delta is on a hidden input, so the coarse run adds no information about
  this change. Left undone deliberately rather than silently — if the drawer's
  touch metrics are ever questioned, that run is the missing evidence.
- No screenshots, no Firefox, no physical device, no Pure Data, no audible
  checks. This stitch changes CSS file organization and deletes duplicated
  rules; it adds no declaration that did not already apply somewhere.
