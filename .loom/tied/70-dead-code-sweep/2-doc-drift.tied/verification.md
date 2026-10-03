# Documentation path corrections — verification

2026-10-03. Software and editorial checks only; no devices contacted and no
`.pd` files edited. Git patch-route surfaces and waiting stitch 68 untouched.

## Changes and scope

- Corrected `pd/bopos.pd` to the existing `pd/bopos~.pd` twice in contract
  §4.2 and once each in OSC-REFERENCE and COMPOSING. The contract diff is
  exactly those two substitutions: no semantics or version change. §15
  records ratified amendments, so an editorial path correction adds no row.
- Corrected `io/main.py` to `python/io/main.py` in PERF, PORTS and the soak
  README, and clarified PERF's archive path as `.loom/tied/`. These are path
  corrections, not changes to ports, deployment or scheduling claims.
- Rechecked `set_points` across current dashboard, Python, tools and tests,
  plus hidden current guidance/protocol files while excluding historical
  `.loom`/`.lore` records and local editor metadata. The only occurrence was
  `OSCBridge.set_points` itself; removed it. Kept `send_points_frame`, sparse
  editing and the `/pt` wire unchanged.
- Added `tests/test_documented_paths.py`, automatically discovered by fast.
  It checks single-backtick concrete paths in README.md, docs/*.md and tracked
  public component READMEs against the repo root or the document directory.
  It ignores OSC/absolute/home/URL/command terms, explicit template/glob
  placeholders, generated `run/` outputs, and two named examples (the
  composer-owned `patches/my-piece/` and an OSC parameter identity).
  Hidden primitive protocol/history documents are outside component-guide
  discovery; references with `.loom` or `.lore` path components are ignored
  wherever they appear. The contract revision table is historical evidence
  and is not scanned. No history or placeholder was rewritten to satisfy the
  guard. Detector tests prove concrete typos remain candidates, missing files
  fail, document-relative files pass, and placeholders/history are allowed.

## Commands and results

```sh
rg -n 'set_points' dashboard python tools tests --glob '!*.pd'
~/.venvs/bopos/bin/python -B tests/test_documented_paths.py
~/.venvs/bopos/bin/python -m pyflakes dashboard/ python/ tools/ tests/test_documented_paths.py
PYTHONPYCACHEPREFIX=/tmp/bopos-doc-drift-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/osc_bridge.py tests/test_documented_paths.py
./tools/run-tests.sh fast
git diff --check
```

- Caller search: definition only before deletion; no matches after deletion.
- Focused guard: **5 tests passed**.
- Pyflakes, compilation and whitespace checks: **pass**.
- Fast suite: **367 tests passed**, exit 0, including the new guard. Run with
  localhost socket access required by existing tests; log retained at
  `/tmp/bopos-doc-drift-fast.log`.
- Browser tier not rerun: this change fixes documentation and removes an
  uncalled helper; the previous stitch's 23 browser journeys passed and no
  frontend or operator behaviour changed here.

Both children now satisfy the scoped parent goal. The element-selection
recommendation remains recorded in child 1 for Bob; its implementation is not
part of this completed sweep.
