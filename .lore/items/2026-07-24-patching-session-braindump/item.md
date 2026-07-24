# Patching-session braindump: precision input, reusable control surface, control tab, manifest presets

Bob's 2026-07-24 braindump after the deepest patching session yet — a patch
taken from the editor, through the simulator, onto a device. The system worked;
the session surfaced four wants: precision float entry everywhere a parameter
is controlled, a reusable control-surface component as an app-wide pattern, the
Dashboard tab reframed as a **Control** tab with target filtering, and presets
re-founded as a manifest-scoped primitive (save from the patch editor, load
onto seats/groups/all). The preset architecture is explicitly flagged as
needing a design pass, not just implementation.

## Source

Bob, 2026-07-24, dictated after the editor→simulator→device patching session.
Verbatim text in `content/braindump-2026-07-24.md`.

## The four asks

**1. Precision float input.** Sliders are good for gesture, but sequencing and
parameter control need exact numeric entry. Wanted *wherever* a float parameter
is controlled — not one tab's affordance but a property of the parameter
control itself.

**2. A reusable control surface.** Zooming in on one device today means Seats
tab → find the device — and with more parameters per device the detail no
longer fits vertically; the cue section is much too big (maybe off to the
side), while the parameters — the actual focus — get a short strip. The
per-seat grid may not be the right approach at all. The fix he sees: one
control-surface pattern reused across tabs —
- **Patch editor:** shows the patch's own control surface; moving its controls
  visibly drives the patch being edited.
- **Devices tab:** the same panel exposing a specific *device's* parameters, so
  you can grab a device directly regardless of which seat it holds.
- **Control tab** (renamed from Dashboard): the same view plus a target filter
  (all / groups / specific seats), and it carries the cues, master control, and
  presets.

**3. Dashboard → Control.** The tab rename is part of the reframe: it is the
targeting-and-control view built on the shared surface, not a bespoke grid.

**4. Presets as a manifest-scoped primitive.** A preset belongs to a patch and
its manifest and applies to a single device/seat; *collections* of presets then
apply to groups, seats, everything. Key workflow: while editing a patch with
its control panel open, "save preset" captures the current state; over on the
Control tab that preset loads onto a chosen seat, group, or all devices. Bob
asks for an architectural evaluation of what a preset should *be* — this is a
design gate, not a ratified design. (Today's presets are dashboard-side
parameter snapshots; this proposal moves their identity into the patch/manifest
layer.)

## Status

Braindump only. It motivates thread intake and a preset design proposal for
Bob's ratification; it does not itself ratify any design. The control-surface
consolidation touches the Seats/Devices/Dashboard information architecture and
should be treated as a design-gated restructure.
