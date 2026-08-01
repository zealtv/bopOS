# automation-3 notes — 2026-07-20

Implementation delegated to GPT 5.6 Sol via codex against `spec.md`;
visual decisions follow the ratified
`.loom/tied/automation-4-waveform-ux-gate/judgment.md` (Slice 1 only —
marker motion is `automation-5-waveform-marker`).

## What landed

- `dashboard/osc_bridge.py`: runtime-only automation tracking in
  `set_param` (classified via `python/paramgen.py::parse_message`),
  selector→seats resolution, fade-destination durable mirroring, entry
  clearing on constant/`stop` writes; `state.public()` now carries a
  top-level `automation` map (the `durable()` allowlist keeps it out of
  `installation.json` — verified).
- `dashboard/server.py`: `set_live_param`/`replay_live_params` clear
  touched entries.
- `dashboard/static/js/paramspec.js` (new): shared §3.2 parser extracted
  from `show.js` (`window.ParamSpec.parse`), loaded by both pages.
- `dashboard/static/js/facilitator.js` + CSS: `--auto` token (dark/light/
  `data-theme` triple per the judgment), static kind glyphs (fade `╱`,
  loop `⟳`, smooth `∿`, stepped `⌁`), aria-label automation state, honest
  `auto·mixed` aggregation, offline dimming, `.taking-over` drain with
  reduced-motion instant clear, one polite take-over announcement.

## Verification (run by orchestrator, 2026-07-20)

- `node --check` on show.js / facilitator.js / paramspec.js — OK.
- `verify_automation_takeover.py` (this dir) — 13/13 PASS (real server +
  simfleet through a recording datagram proxy + headless Chromium).
  One harness fix during bring-up: the facilitator page's `#ws-status` is
  an empty span when online, so the wait needs `state="attached"`.
- Regressions: tied automation-2 builder suite (27/27), automation-1
  engine parity, 6-message-editing — all green. `git diff --check` clean.

Dashboard restart forgets runtime automation state by design (devices keep
running their generators; the UI then shows stored constants). Recorded as
an accepted limitation in the spec.
