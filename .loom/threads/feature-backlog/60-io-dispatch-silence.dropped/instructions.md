# 60-io-dispatch-silence

**Status:** parked 2026-08-05 · not critical · **fold into `59/3` if that's
claimed first**
**Goal:** finish hardening io bridge dispatch — a test, and close the last
silent path.

## Background (fixed)

A patch's `io create …` reached the bridge as a bare `/io` and was dropped
silently. A hand-issued create masked it until a reboot. Fixed in `b6785cd` and
`bd2d989` (`pd/bopos~.pd` now emits `/io/<verb>` and `/io/<name> <cmd>`);
`io/main.py` now logs unrouted messages and replies `/io/error` on failed
creates. Reboot check passed.

Don't build "accept a bare `/io` with the verb as first arg" — nothing emits it
any more.

## Left

1. **No test.** `handle_io` is pure dispatch — easy browser- and hardware-free
   test. Pin: verb-before-peripheral precedence, `RESERVED_NAMES`, the
   `len(parts) == 1` guard (so `/io/lights/fill` doesn't misread `fill`'s first
   value), and that no branch is silent.
2. **Unknown `/io` verbs only log.** A typo'd verb still gets nothing on the
   wire; reply `/io/error` there.
