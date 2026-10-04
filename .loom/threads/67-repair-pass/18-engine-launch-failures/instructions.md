# 18-engine-launch-failures

**Status:** ready
**Goal:** `bash/start-engine.sh` exits non-zero when a required step fails,
so audio-config apply/rollback (`bopos.py _restart_audio_engine`) can trust it.

Evidence: `lore:2026-10-05-bopos-review-install-services` B3. A failing runcontext command is masked by
`eval "$(...)"`; a failing `record-active` is ignored; an engine that dies
at once still writes PID files and exits 0. Check each result (capture before
eval), notice immediate engine death, clean up only this launch's processes.
Keep the full-stack invalid-manifest skip (58/4 owns that gate).

Done when: the three cases fail before and pass after, plus a successful
launch; fast green.
