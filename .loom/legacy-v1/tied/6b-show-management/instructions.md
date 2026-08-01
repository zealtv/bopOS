# 6b-show-management — create, load, and switch shows

Bob's 2026-07-19 Show tab feedback: "there's no way to, for example,
create a new live set or load another live set." (His other point — no
way to add a step — is already scoped in `6-message-editing`; don't
duplicate it here.)

Shows persist as files under `dashboard/shows/` (stitch 1 schema, stitch
2 load/save surface). This stitch adds the operator surface for managing
*which* show is loaded. "Live set" is Bob's Ableton vocabulary — the UI
term stays **show** per the thread's naming ruling.

Scope:

- New show: create a fresh empty show file (prompted name, validated to
  a safe filename), becomes the active show.
- Load/switch: pick among existing show files in `dashboard/shows/`;
  switching stops playback (transport must not keep driving steps from
  a show that is no longer loaded) and loads the selected file.
- Rename and delete if cheap; duplicate ("save as") is welcome but
  optional — note what's deferred.
- The active show persists across dashboard restart and broadcasts so a
  second client agrees which show is loaded.
- Placement: compact control in the Show tab header area, consistent
  with existing dashboard idioms; touch first-class.

Requires stitch 2 (persistence surface); independent of 6/7 — claimable
alongside them.

Verify: `verify_show_management.py`, Playwright, house pattern. Cover:
create new show, add content, switch to another show and back
(persistence intact both sides), switch-while-playing stops transport,
active show survives server restart, second client convergence.
