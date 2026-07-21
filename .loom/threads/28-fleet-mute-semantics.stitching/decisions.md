# decisions — 28-fleet-mute-semantics

## Verdict: not a defect. Fleet mute safety is intact.

Thread `23` flagged this as the one sweep failure that did not look like drift,
and I recommended pulling it out on the grounds that fleet mute is a safety
surface. **That suspicion was wrong**, and it is worth saying so plainly: the
three failures are one superseded assertion plus two cascades from it.

## What the guard asserted, and who reversed it

`verify_live_controls_backend.py` asserted:

```
check("fleet safety overlay blocks individual mute mutation",
      dashboard.state.device_muted_for("node-a") is True
      and not wire.frames and bool(ws.messages))
```

i.e. while fleet safety mute is on, an individual device unmute must be
**rejected**.

Bob's 2026-07-16 hands-on revision, tied as `18-decoupled-device-mute`, reverses
exactly that:

> - Persistent exact-device mute and session fleet safety mute are independent
>   controls with effective node mute remaining their logical OR.
> - **Keep the selected Device Mute/Unmute action available while fleet mute is
>   on**, so an operator can establish the state that will remain after fleet
>   release.
> - Verify: fleet on → device mute on → fleet off leaves that device muted;
>   **fleet on → device mute off changes persistent state while effective mute
>   stays on.**
>
> This supersedes only the old proposal's UI ruling that disabled Device
> controls during fleet safety…

So the guard pins the pre-revision ruling. `18`'s own guard is **green**, which
is the independent confirmation that the runtime implements the revision
correctly rather than merely differently.

## Observed behaviour (probe, not inference)

With fleet mute on, `set_device_mute(node-a, 0)`:

| | value |
|---|---|
| persistent intent (`device_muted_for`) | `False` — the operator's staged state |
| **effective mute** (`public_device.effective_muted`) | **`True`** — fleet OR holds |
| wire | `[("device-mute", "node-a", 0)]` — exact-UID, establishes post-release state |
| rejection message to the client | none |

That is Bob's specification line by line. **The audible safety property — a
device cannot actually unmute while fleet safety is on — is preserved.**

## The two cascades

Both followed mechanically from node-a now being persistently unmuted:

- `fleet release reasserts persistent per-UID state` expected the replay
  `("device-mute", "node-a", 1)`; the correct replay is `0`, because `0` is now
  the persistent state. The *subject* (release replays persistent per-UID state
  rather than blanket-unmuting) is unchanged and still asserted.
- `host-global device mute survives restart` asserted `True` after a reload,
  which the staging above had legitimately made `False`.

## Repairs

In `.loom/tied/12-dashboard-live-controls/verify_live_controls_backend.py`, in
place with an inline SUPERSEDED note naming this stitch:

1. The blocking assertion is **inverted** to the post-revision semantics: device
   mute stays mutable beneath fleet safety, the exact-UID frame is sent, no
   rejection is returned.
2. **A new check was added**, because inverting alone would have deleted a
   safety assertion and replaced it with nothing: `fleet safety still forces
   effective mute while staged` pins `effective_muted is True`. The repaired
   guard therefore asserts a *stronger* property than the original — the
   original only proved the intent was frozen, which is not the same as proving
   nothing can make noise.
3. The release-replay expectation becomes `0`.
4. Before the restart check, a persistent mute is **re-established**, so the
   check still proves persistence rather than proving that `False` survives a
   reload (which would assert nothing).

Verified green: this guard 0 failures, plus the neighbouring
`verify_device_mute_protocol.py` and `18-decoupled-device-mute`'s own guard.

## Found in passing — a separate red guard, not fixed here

`12-dashboard-live-controls/verify_live_controls_browser.py` **also fails**, on
a different subject: it times out waiting for
`[data-live-param][data-live-scope="seat"][data-live-id="1"][data-param-path="gate"]`.
It is a Playwright suite, so it was **not** in thread `23`'s 71-guard sweep — it
is an additional red guard beyond the 39.

Not a rename: `data-live-param`, `data-live-scope` and `data-param-path` are all
still emitted by `facilitator.js:172`. So it needs real diagnosis, which belongs
to the cleanup thread rather than here. Recorded in `27-tied-guard-rot`.

It is also the first datum on the **97 unswept Playwright suites**, and it went
red — so the true rot figure is above 39.
