# Handoff — 2026-07-11 (Mac audition rig)

## Why this handoff exists

Bob is leaving the remote Linux machine `spectre` and continuing on the Mac
that will be used for composition/performance. The Mac has physical access,
the `bopOS` repository, and the AI-kit workflow repositories. This is the
right machine for the remaining macOS port-sharing check and the audible
audition-rig work.

No loom stitch was claimed on `spectre`. Start cleanly on the Mac and work one
stitch at a time.

## Repository state to acquire

At handoff, `spectre` is clean and synchronized at:

```text
86339a9 Tie spatial software and wait on the rig sweep
```

On the Mac, start in the `bopOS` repository, update from `origin/main`, and
then read `AGENTS.md`, `CLAUDE.md`, this handoff, and live loom status. Do not
discard local Mac changes if its checkout is dirty; reconcile them before
pulling or claiming work.

```sh
git status --short
git fetch origin
git pull --ff-only
./.loom/loom status
```

The previous `.notes/handoff-2026-07-11.md` has a stale recommendation to
start `seam-4`; the patch-seam and spatial software threads have since been
tied. This handoff supersedes that recommendation.

## First stitch: finish the macOS port spike

The next session must first resume the waiting stitch, not claim Stage 0 yet:

```sh
./.loom/loom claim audition-0-port-spike
```

Read the claimed stitch's `instructions.md` and `results.md`, then run the
documented macOS check from the repository root:

```sh
python3 .loom/threads/audition-rig/audition-0-port-spike.stitching/spike_port_sharing.py
bash .loom/threads/audition-rig/audition-0-port-spike.stitching/spike_pd.sh /tmp
```

Record the exact macOS version, architecture, PD version/path, commands, and
results in the stitch. In particular determine:

- whether all Python receivers see every broadcast;
- whether multiple stock PD instances can bind UDP 6660;
- whether every PD instance receives and applies the broadcast; and
- whether cleanup kills both `pd` and `pd-watchdog` processes.

Do not edit any `.pd` file. If stock PD cannot share port 6660 on macOS,
record the failure precisely. The already-identified fallback is one UDP
fan-out relay binding 6660 and forwarding to per-instance localhost ports;
that finding shapes Stage 0, but should not be implemented inside the spike.

Once the Mac result is fully recorded, run any stitch-local checks and tie
`audition-0-port-spike` according to the loom protocol. If an external issue
prevents the test, return it to `.waiting` with the blocker recorded rather
than claiming the next stitch.

## Second stitch: audible Stage 0

Only after the port spike is tied:

```sh
./.loom/loom claim audition-1-stage0-launcher
```

Build the Stage 0 composition rig described in its instructions:

- launch N real PD instances with distinct device identities;
- use the existing `start.sh` startup-message mechanism;
- route instance outputs to stereo through the Mac audio/JACK environment;
- use broadcast plus selector addressing, never shared-port unicast;
- keep flags/config compatible with `simfleet.py`;
- provide reliable cleanup; and
- verify three instances under dashboard control with audible/logged evidence.

The stitch was written Linux-first because Linux was the only verified host.
The Mac is the strategically important platform. Use the spike result to
choose between direct shared-port launch and the documented fan-out relay
seam. Keep platform-specific behavior explicit and preserve Linux operation.

Follow `docs/VERIFICATION.md`. Record anything not actually verified,
especially audio routing, dashboard control, touch behavior, and differences
between macOS and Linux. Do not claim `audition-2-listener-puck` until Stage 0
is complete and tied.

## Current project state

- Contract v1.1 provided terms are implemented.
- Patch-seam is complete and tied.
- Clock-sync software is complete; hardware measurement is waiting.
- Dashboard core phases are complete; rig adoption is waiting.
- Spatial authoring and synchronized cue start are complete; rig sweep waits.
- PD receiver edits remain Bob-owned in `.notes/pd-edits-for-bob.md`.
- Scene sequencing and audio input remain intentionally gated.
- At handoff there are 33 tied stitches and no active claims.

## Suggested opening prompt for the new Mac session

```text
Continue bopOS from .notes/handoff-2026-07-11-mac-audition.md. Read AGENTS.md
and CLAUDE.md, inspect the dirty state and live loom before changing anything,
then work exactly one stitch at a time. First reclaim and complete the macOS
half of audition-0-port-spike. Only after tying it, claim
audition-1-stage0-launcher and build/verify the audible Mac audition rig. Never
edit .pd files; record required PD work for Bob.
```
