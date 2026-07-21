# notes — 28-fleet-mute-semantics

## Verification

Guard repaired in place at
`.loom/tied/12-dashboard-live-controls/verify_live_controls_backend.py`.
Copy it out and run from the repo root:

```
~/.venvs/bopos/bin/python <copy>/verify_live_controls_backend.py
```

**0 failures.** Neighbours re-run and green as a cross-check that the repair
describes real behaviour rather than being fitted to it:

- `.loom/tied/18-decoupled-device-mute/verify_decoupled_device_mute.py` — 0
  failures. This is the load-bearing one: it is the guard for the very ruling
  the repaired assertions now follow, and it was **already green before I
  touched anything**, which is what established that the runtime is correct.
- `.loom/tied/12-dashboard-live-controls/verify_device_mute_protocol.py` — 0
  failures.

## Method note worth keeping

I probed the live behaviour before writing a single assertion — copied the
guard, replaced the failing `check(...)` with a `print(...)` of persistent
intent / wire frames / client messages / `effective_muted`, and ran it. Four
values, one run, and the repair wrote itself.

The temptation was to reason from `18-decoupled-device-mute`'s prose to what the
code "should" do and assert that. The prose and the code agreeing is exactly
what needed proving, so assuming it would have made the repaired guard circular.

## The wrong suspicion

Thread `23` (mine) flagged this as the likely live defect, on the reasoning that
three *behavioural* failures in a safety subsystem look different from
`AttributeError` drift. That reasoning was sound and the conclusion was wrong:
the failures were behavioural precisely because Bob had deliberately changed the
behaviour. **"Looks behavioural, not like drift" is not a defect signal** — it
only means the supersession happened at the ruling level rather than the API
level, which is if anything *more* likely to be intentional.

Cheap check that would have settled it in one step, worth doing first next time:
`grep -rl "<the subsystem>" .loom/tied/*/instructions.md` and read any stitch
whose title suggests it revised the rules. `18-decoupled-device-mute` says
"supersedes" in its own text.
