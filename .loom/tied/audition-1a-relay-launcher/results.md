# audition-1a relay launcher results

Implemented `tools/audition.py` as the single owner of the audition rig's LAN
command socket. It creates deterministic virtual identities, reports contract
heartbeats, applies the ratified `all`/exact-integer selector rules, strips the
selector, and relays matching packets to distinct localhost engine ports. The
Stage 0 LAN relay surface is deliberately limited to selected `/p/<name>` and
`/os/master`. Assignment, provisioning, sync, point, cue, and other framework
messages are rejected rather than impersonating helper behavior. `/id` is a
launcher-owned local catch-up message, not a relayed LAN surface.

The launcher reads the active manifest shape through `python/manifest.py`,
starts one owned process group per virtual node, exports `BOPOS_ENGINE_PORT`,
and sends `/id <id>` to each local engine after catch-up. PD also receives
`BOPOS_ENGINE_PORT <port>` and the existing `ID <id>` global in its startup
message, allowing each instance to bind before the `/id` catch-up. PD defaults to
PortAudio (`-pa`) on macOS and JACK on Linux; `--audio-backend` and the
engine-neutral `--engine-command` template preserve explicit alternatives.
Shutdown signals only the process groups this launcher created, waits for a
bounded interval, then escalates those groups if required. `--no-engine` keeps
the UDP relay active for deterministic verification without launching audio.
The LAN socket does not opt into address reuse: a second owner fails visibly.
Engine startup is also within the cleanup boundary, so failure to start a later
engine tears down earlier owned groups and closes the command socket.

An SC patch can declare `"engine": "sclang"` and its `.scd` entrypoint in the
manifest; the default launch is then `sclang <absolute-entrypoint>`. More
specialized SC server/language arrangements can use `--engine-command`, whose
shell-like template expands `{entrypoint}`, `{port}`, and `{id}` separately for
each node. Every engine also receives `BOPOS_ENGINE_PORT`,
`BOPOS_AUDITION_ID`, `BOPOS_ACTIVEPATCH`, and `BOPOS_ASSETS` in its environment.
The relay and `/id` catch-up target that node's `BOPOS_ENGINE_PORT`. No PD
arguments or startup messages are added outside the explicit PD engine branch.

## Verification

Run on macOS from the repository root on 2026-07-11:

```text
~/.venvs/bopos/bin/python .loom/threads/audition-rig/audition-1-stage0-launcher/audition-1a-relay-launcher.stitching/verify_audition.py
PASS: heartbeats, selector relay, /id catch-up, and owned teardown
```

The first sandboxed attempt could not bind a localhost UDP socket
(`PermissionError: [Errno 1] Operation not permitted`). Re-running the same
command with localhost socket permission passed. The test uses non-default UDP
ports and proves:

- three distinct `/hb` uid/id pairs;
- `/all` fanout and exact-id isolation;
- selector stripping and ignored unmatched selectors;
- rejection of sync, provisioning, and point messages outside the allowlist;
- one local `/id` catch-up per engine port;
- distinct PD startup `BOPOS_ENGINE_PORT` and `ID` values without launching PD;
- successful no-engine shutdown;
- exclusive LAN socket ownership and partial-start socket cleanup;
- owned fake-engine group teardown, including a SIGTERM-ignoring descendant,
  without stopping an unrelated process;
- concise rejection of unknown engine-command placeholders.

Also run:

```text
python3 -m py_compile tools/audition.py .loom/threads/audition-rig/audition-1-stage0-launcher/audition-1a-relay-launcher.stitching/verify_audition.py
git diff --check
```

Both passed with no output.

## Remaining boundaries

This browser-free test verifies the dashboard-facing heartbeat wire shape but
does not start the real dashboard backend. Real dashboard row discovery is part
of the sibling three-instance Mac gate. Current PD cannot yet select its local
receive port, so no real PD process or audio output was exercised. SC is absent
from this Mac; its port parameterization and multi-server audio remain
unverified. The relay intentionally does not implement helper clock sync, cue
scheduling, point decomposition, persistence, or unselected fleet messages.
