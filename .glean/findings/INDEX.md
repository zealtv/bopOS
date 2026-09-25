<!-- auto-generated; run glean.sh index to refresh -->

- [[commit-style]] — Commit messages in bopOS — When committing here, write a plain-prose subject line (match `git log`) and a body explaining why.
- [[cross-repo]] — kite-choir-brains coordinates the artwork — When work is spool- or Kite-Choir-specific, check kite-choir-brains' own loom first — coordinate, don't duplicate.
- [[dashboard-vocabulary]] — Dashboard names and UI rules — When writing dashboard UI or prose, use the shipped names and the ratified design rules.
- [[decision-gates]] — Some choices are Bob's to ratify — When a stitch reaches a user-facing, wire, or strategy decision, write a proposal and stop rather than implementing past it.
- [[fix-and-simplify-first]] — Fix and simplify before adding — When choosing between adding a capability and repairing or removing something, repair first — Bob: *"I want to fix and simplify things before making them more complicated."*
- [[hardware-claims]] — Don't claim hardware you didn't run — When a stitch involves real Pis, audio or peripherals, record which half ran — software gates and hardware checks are separate claims.
- [[horizon-refactor]] — One device, one engine, probably Pd — the assumption on its way out — When a design touches engines, launch, ports or per-device identity, phrase it so it survives several engine instances per device and a non-Pd engine.
- [[land-before-usage-limit]] — Land work before the usage window closes — When a session is long or near its usage limit, work in small slices that each verify and commit, so nothing is left mid-flight.
- [[manifest-and-patch-distribution]] — Patches reach devices only by push — When changing the manifest grammar or debugging a device on an old patch, remember `patches/` is gitignored: devices get patches from dashboard distribution, never from `git pull`.
- [[never-edit-pd]] — Never edit Pure Data patches — When a change would touch a `.pd` file, stop: Pd patching is Bob's domain, so write the needed edit down for him instead.
- [[osc-contract]] — The OSC contract is ratified; amend it, don't relitigate it — When touching anything on the wire, work from `docs/OSC-CONTRACT.md` (v1.17 as of 2026-09) — its §15 revision history is the authoritative record of how it got there.
- [[pd-float-precision]] — Keep large numbers and absolute time out of Pd — When a value travels to Pure Data over OSC, it must fit a 32-bit float — six significant figures at most.
- [[playwright-gotchas]] — Playwright gotchas in the dashboard journeys — When writing or debugging a `tests/verify_*.py` browser journey, these are the traps earlier sessions fell into.
- [[test-rig]] — The Finn Jet / Ciro Toast rig — When hardware verification is needed, the two-device rig is Finn Jet (fleet node) and Ciro Toast (standalone); `bop000` is a spare Zero 2 W.
- [[verification]] — Verify at the right level, and run tests from the venv — When checking a change, use `tools/run-tests.sh` from `~/.venvs/bopos` and pick the level from `docs/VERIFICATION.md`.
- [[ws-snapshot-handlers]] — Late websocket handlers only see snapshots listed in ws.js — When adding `ws.on(<type>, …)` in a script that loads after `dashboard.js`, check the type is in `SNAPSHOT_TYPES` in `ws.js`, or the handler can miss the connect burst forever.
- [[zero-indexing]] — Count from zero on the wire and in the model — When adding any index — elements, points, slots, instances — make it 0-based on the wire and in code (Bob, 2026-07-11).
