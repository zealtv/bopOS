# 3-peripheral-lifecycle

Let the operator instantiate a peripheral from the Device tab, and — the part
that matters — **see whether it worked**.

Anchored on `1-scan-transport`: that stitch builds the `bopos.py` ↔
`io/main.py` relay this one sends over.

## The defect this fixes, which exists with or without a UI

`io/main.py` replies `/io/error <name> no-bus|create-failed` when a create
fails (`python/io/main.py:156-165`). Its OSC client is constructed once,
hardcoded to `127.0.0.1:6662` (`python/io/main.py:40-41`), so that reply goes
to the engine — where, in `patches/fire-button/main.pd` and every other patch
in the repo, nothing routes it. On 2026-08-05 Bob's create failed twice over
(wrong type *and* wrong address, see `../session-2026-08-05-ciro-toast.md`)
and the only symptom available to him was silence.

**A failed create must be observable.** That is true independently of this
thread's UI and is the first thing to fix.

**And the bridge's own diagnostics are discarded too.** `bash/start.sh:63-66`
launches `io/main.py` with no redirection and no `-u`, so its stdout is both
lost and block-buffered. It already prints everything an operator needs —
`✓ Created adc (ads1115 @ 0x4B)`, `adc: 4-channel ADC ready`, the per-read
`Error reading <name>` — and none of it reaches anyone. Confirmed on Ciro
Toast 2026-08-05: relaunching the same process as
`python -u main.py > /tmp/io.log` turned a silent box into a running
commentary, with no code change at all. Giving the bridge a log file (and
`-u`) is a one-line fix in `start.sh` and is worth doing on its own, before
any of the OSC work here.

## Deliver

- **Create / destroy from the dashboard**, relayed to `io/main.py`, with the
  result reported back rather than assumed. `create` already exists;
  `io/main.py` has **no destroy verb at all** — adding one is in scope,
  because an operator who creates the wrong thing from a button must be able
  to take it back without restarting the stack.
- **The registry as state, not as a print.** `/io/report` currently prints the
  active peripherals to the bridge's stdout (`python/io/main.py:172-177`),
  which is unreachable. Make it a reply: name, type, address, and whether its
  last read succeeded.
- **Surface `/io/error`** wherever the operator triggered the create.

## Design questions to settle in-stitch

- **Who owns a peripheral — the patch or the operator?** Today the patch
  authors `io create` message boxes and is the only creator. If the dashboard
  can create too, an engine restart re-runs the patch's creates and the two
  can disagree. The honest v1 answer is probably that dashboard creates are
  **ephemeral test instruments** that do not persist across an engine restart,
  and the Device tab says so; a persisted operator-owned peripheral list is a
  much larger design (it is patch configuration, and patch configuration is
  distributed and fingerprinted). Recommend the small one and record why.
- **Type from address?** `python/io/` knows each module's default address, so
  the scan can *suggest* `ads1115` for `0x48–0x4b`, `mpr121` for `0x5A`, etc.
  It must stay a suggestion — the standing rule from `sys_i2c.py` is
  discovery, not assumption — but a suggestion would have saved this session,
  where the type was as wrong as the address.
- **Address override.** The board that prompted this sits at `0x4b`, not the
  module default `0x48`, so whatever the UI suggests must be editable.

## Verify

Browser journey against simfleet, plus a real create/destroy of the ADS1115 at
`0x4b` on Ciro Toast — the failure paths (`no-bus`, wrong address, wrong type)
are the ones worth exercising, since they are what actually happened.
