# p3-global-transport-and-cue-lead

Global transport + cue policy. Builds on p2's exclusive playback (one
playing step makes "the" transport meaningful).

1. **Global transport strip controls:** play/pause, stop, next as icon
   buttons in the transport strip. Play starts the currently selected
   (focused) step, or the first step if none is selected; when a step is
   playing, the same button is pause/resume. Stop stops the playing step.
   Next triggers the playing step's then-action now (the per-step
   "trigger next" promoted globally). Stop-all's text label becomes a
   stop glyph (keep an accessible label/title). Reuse the p1-legible
   glyph set; keep the 5b header-height budget (compact controls with
   expanded hit areas — the 6b precedent).
2. **Forward-sync retirement.** All cues forward-sync by design: the
   engine always schedules `/cue` via `bridge.fire_cue()`; `fire_cue_now`
   stays for non-show surfaces unless it falls out naturally. Remove the
   per-step tick box and the mixed-sync hint from the step inspector.
   `show_model.clean_step` accepts and drops a stored `forward_sync` key
   (legacy shows load; saves no longer write it). Design note gets an
   amendment section, not a rewrite.
3. **Global cue lead time.** A settable lead-time control (default 500 ms)
   governing the forward-sync horizon. Placement: with the OSC consoles /
   transport area — pick what reads best and log the reasoning.
   Persist it in the installation state (not per-show), broadcast so
   clients agree, and pipe it through `fire_cue(lead_ms=...)`. Wire shape
   unchanged (§3.1: sharedTimeNs computed leader-side; lead is
   leader-internal policy).

Verify: `verify_show_transport.py` (house pattern, simfleet): global play
with nothing selected starts the first step; with a focused step starts
that one; pause/resume/stop/next drive the engine; a step's cue message
arrives scheduled (sharedTimeNs ≈ now + configured lead) after changing
the lead-time control; legacy show file with `forward_sync: true/false`
loads and round-trips without the key. Amend tied 5-inspector (sync hint
gone) and any strip-text assertions; log amendments.
