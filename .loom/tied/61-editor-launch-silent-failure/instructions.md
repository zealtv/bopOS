# 61-editor-launch-silent-failure

Make **Launch editor** either work or say why. Today, on a machine without one
exact Pd build, it does neither: it reports `running`, then `stopped
unexpectedly`, and every diagnostic that would explain it is discarded.

Raised by Bob on 2026-08-10. On a **new dashboard install** he created a patch,
opened it in Pd, clicked *Launch editor*, and nothing happened. Bob's own first
guess was right, and it was the harder half of the bug to see: *"my first guess
would be the hardcoded binary. this machine has 0.55-0 and 0.56-2"*.

## The mechanism, traced end to end

`tools/audition.py:863-865` defaults `--pd-bin` to the literal path
`/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd` on darwin, `pd` on
Linux. `dashboard/server.py:3125-3132` builds the editor's supervisor command
and **never passes `--pd-bin`**, so on macOS that literal is the only value
there is. There is no flag, no env var, and no config that reaches it — the
default is not a default, it is a hardcoding. It pins the patch number as well
as the minor, so **0.55-0 misses it by one digit** and 0.56-2 by two.

What follows from a missing binary:

1. `start_engines` (`tools/audition.py:246`) calls `subprocess.Popen(command,
   …)` with no `try` — `FileNotFoundError`.
2. It is the first statement inside `run()`'s `try/finally`
   (`tools/audition.py:817-819`), which has **no `except`**, so it propagates
   before `send_ready()` and the process exits non-zero.
3. `launch_supervisor` (`dashboard/server.py:2989-3003`) has already returned
   `True` — it Popen'd *python*, which exists — so `start_edit` sets
   `editor["status"] = "running"` (`server.py:3138`) and broadcasts.
4. A moment later `supervisor_exited` (`server.py:2974-2987`) sets `stopped
   unexpectedly` and drops the mode to `off`.

So the operator sees a flicker to `running` and a settle on `stopped
unexpectedly`, with no Pd window and no cause named anywhere. Reported, quite
reasonably, as "nothing happens".

## Why this is two stitches and not one

`1-pd-binary-resolution` is the break. `2-supervisor-stderr-visibility` is the
reason the break took a code-reading session to find rather than a glance at a
status line: `launch_supervisor` passes `stdout=subprocess.DEVNULL,
stderr=subprocess.DEVNULL`, so the traceback that names the missing path
verbatim is thrown away before anyone can read it.

Fix them in that order — Bob is blocked on launching an editor *now*, and the
resolver unblocks the machine — but do not stop at the first. The second is the
one that pays off on the next failure of this class, and there will be one:
the same `DEVNULL` covers the **Simulation** supervisor too
(`start_simulation`, `server.py:3019`), which fails exactly as silently.

Standing constraint from Bob, still in force: *"I want to fix and simplify
things before making them more complicated."* Both of these are fixes. Neither
needs a design gate — resolving an executable and not discarding stderr are
plain engineering calls, not user-facing rulings.

## Recorded so nobody re-derives it

- The stopgap on an affected machine is a symlink at the expected name:
  `ln -s /Applications/Pd-0.56-2.app /Applications/Pd-0.55-2.app`. It works
  because the path resolves straight through the bundle. It is a stopgap, not
  the fix, and it rots at the next Pd release exactly as the hardcoding does.
- **This is at least the second machine it has bitten.**
  `.loom/legacy-v1/tied/pe-2-edit-mode/verify_pe2_edit_mode.py:128-130` already
  guards `os.path.isfile(pd_bin) and os.access(pd_bin, os.X_OK)` and prints
  `[SKIP] real GUI-PD launch -- PD executable unavailable`. A tied guard has
  been quietly skipping itself on any machine without that exact build,
  which is the same fact wearing a green tick.
- The four other silent-failure paths through the same button were ruled out
  by inspection in the diagnosing session, and are **not** in scope here. For
  the record, so a later session does not re-walk them: the dropdown filters
  on `item.valid` and `launch.disabled = !patches.length`
  (`dashboard/static/js/dashboard.js:963-985`), so an invalid manifest yields a
  disabled button; a suppressed `confirm()` returns false forever; a JS
  exception earlier in `renderEditor` would leave `onclick` unbound. All three
  present identically to the operator. Only the fourth — this one — was
  actually firing on Bob's machine.
