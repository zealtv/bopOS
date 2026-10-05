# 76-bob-review

**Status:** waiting on Bob · collected 2026-10-04 while working the projects queue
**Goal:** one place for everything from that session that needs Bob's review,
ruling or hands on hardware. Agents: don't work this stitch; it's Bob's.

Bob, 2026-10-04: *"anything i need to review put it in a single stitch so i can
look at it all at once after this session"*. Each item points at where the
evidence lives; the stitches named stay where they are. When an item is ruled,
record the ruling in the stitch it points at (resume it if it's waiting), then
move it to Ruled here. Tie this when Open and Hardware checks are empty.

## Open

8. **FYI: my calls on the project menu (66/7)**. Names keep spaces as typed,
   because the folder name is the name ("Kite Choir", as in the mockups):
   letters, digits, spaces, `.` `_` `-`, starting with a letter or digit. New
   error lines follow the existing pattern: "That project could not be
   opened." / "The project could not be created." / "The project could not be
   renamed." / "The site could not be created." Switching project is refused
   outside Live. Say if any of these should change.

13. **Shared node protocol (69/3)**: `69-complexity/3-shared-node-protocol.waiting/proposal.md`.
    One small shared module for validation, UID verb dispatch and replies,
    plus parity tests against the contract. Keep both OSC libraries for now;
    defer the horizon engine redesign. Found drift: audition is missing six
    verbs; assignment validation differs; enabled 0.5 is accepted as 0. The
    worst defect, malformed sync killing the node's listener, is already
    fixed. Approve the narrow extraction?

14. **Monitor transport labels (71/2)**: built and merged; parked until you OK
    the new wording. Screenshots: `screenshots/monitor-71-2-*.png`. Labels:
    "Capture filters", "Address starts with", "Exclude addresses", "Device
    UIDs", "All devices", "Include raw lines: Sync / Heartbeats / Points";
    "Sync, heartbeats, points excluded." / "All traffic classes included.";
    "Rates/s: sync N, heartbeats N, points N. N filtered · N unattributed";
    "⚠ N matching messages dropped · N previews shortened"; history notes
    ("Capture started; hidden or paused traffic was not retained.", "Capture
    paused; no history is collected.", "Capture filters changed; …",
    "Connection opened; …", "Connection lost; traffic during the gap is
    unknown."); System "N / N with 3+ samples". Full list in
    `71-network-traffic/2-monitor-transport.waiting/build-verification.md`.

15. **FYI: Module panels (59/9)**: built, merged and tied. Screenshots:
    `screenshots/modules-59-9-*.png`. The wording comes from the spec ("Modules",
    "Show in Monitor", "Pop-out"), plus one hover tip of mine on the panel ✕:
    "Close panel". Values show at Pd precision (six significant figures).
    Say if anything reads wrong.

16. **Editor input label (59/6)**: built and merged; parked until you OK the
    label. In Patch Edit, a new picker under "Manifest & editor" reads
    **"Input source"**: "—" (none), "simulated", or a device such as
    "Ciro Toast · live". Screenshots: `screenshots/editor-input-59-6-*.png`.
    OK as is?

## Hardware checks (Bob's hands; software halves are done)

1. **Wi-Fi slice 0**: with a Pi up, choose the network manager. The helper
   backend is a marked seam that reports `unavailable` until then. →
   `33b/2-network-config-implementation.waiting`.
2. **Wi-Fi switchover rehearsal**: both APs up, push the list, disable
   *testing*, devices reappear on the hidden show network; disable show 1, and
   the fallback takes over. → same stitch.
3. **IO control path (59/1)**: on a Pi, bridge replies reach `bopos.py` on
   7771; `io-scan` shows real addresses with kernel-claimed (`UU`, the DAC)
   marked; a scan doesn't disturb live peripherals; real driver writes and
   errors; the Finn Jet wrong-address LIS3DH case. Details in
   `59-i2c-inventory/1-scan-transport.tied/verification.md`.
4. **Performance mode (77)**: on a Pi, logging really stops writing to the SD
   card in Performance (tmpfs); the mode survives a hard power cut; the locks
   hold on the device; audio carries on uninterrupted when switching. Details
   in `77-performance-mode.tied/verification.md`.
5. **IO streaming (59/8)**: on a Pi, 7771/5551 traffic while a stream is
   open, the lease really stopping on expiry and on entering Performance, and
   the engine and audio unaffected. Details in
   `59-i2c-inventory/8-stream-port.tied/verification.md`.
6. **Clock-sync stage A (71/1)**: on the real fleet, a packet capture shows
   about 2 sync broadcasts/s and no broadcast offsets; routing survives DHCP
   changes and reboots on the installation AP; recorded audio timing is
   unchanged. Details in `71-network-traffic/1-clock-sync-traffic.tied/verification.md`.
7. **Module panels (59/9)**: on a Pi with a real ADC/OLED, tick Show in
   Monitor; values track the sensor, OLED text writes land, the pop-out
   window keeps streaming, and Performance disables the controls. Chromium
   only so far; Safari/Firefox and touch are untested.
8. **Editor input (59/6)**: with Pd running in Patch Edit, pick a real
   device; the patch sees its sensor values on 6662 as it would on the Pi.
   Pick simulated; slider and pad moves reach the patch, and patch OLED
   writes show in the preview.

## Ruled

1. Passphrase warning wording — **yes**, as it reads in the app (Bob, 2026-10-04,
   via Tengu) → recorded in `33b/2`.
2. Migrate `dashboard/shows/test.json` into the project's `show.json` and delete
   `dashboard/shows/` — **yes** (Bob, 2026-10-04) → recorded in `66-projects/5-one-show`.
3. OSC contract editorial — **rename it** (Bob, 2026-10-04). The facilitator
   allowlist is now "a project-level allowlist in `project.json` … the project
   promotes its verbs" (`docs/OSC-CONTRACT.md` ~859).
4. Venue snapshot `10x8-test` — **drop it** (Bob, 2026-10-04). Removed from
   `dashboard/installations/` (local, gitignored); a copy is in the lead
   session's scratchpad.
5. "New patch…" on the Patches tab — **keep** (Bob, 2026-10-04) → `66-projects/6-patch-versions`.
6. Header tidy screenshots — **look fine** (Bob, 2026-10-04) → `66-projects/8-header-tidy` tied.
7. Clear show — **yes, wording fine** (Bob, 2026-10-04): "Clear Show…", confirm "Remove all N steps from this show? You can undo this." → `66-projects/9-clear-show` (queued).
8. Multiple shows (66/10) — Bob, 2026-10-04: **yes** to the switching rule
   (every mode; refused while playing or paused); the new error lines and the
   default name **Show** are fine; **add "N steps"** to show rows; **yes,
   wrap the header earlier** (~1279px) → follow-up on `66-projects/10-multiple-shows`.
9. Clear Show wording — Bob, 2026-10-04: the one-step confirm ("Remove all 1 step…") is fine; **yes** to "Stop the show before clearing it." → `66-projects/9-clear-show`.
10. Header wraps to two rows at 1440px with the Performance toggle: **keep it** (Bob, 2026-10-04, after seeing the screenshots on Tengu; `screenshots/header-performance-*-1440.png`) → `77-performance-mode`.
11. Clock-sync traffic (71/1) — Bob, 2026-10-04: **approve stage A** (unicast offsets), **defer stage B** → building A in `71-network-traffic/1-clock-sync-traffic`.
12. Monitor transport (71/2) — Bob, 2026-10-04 via Tengu: **OK all**; "prefer simple and elegant solutions where possible; better to remove than add" (also in glean `fix-and-simplify-first`). New labels come back with screenshots.
