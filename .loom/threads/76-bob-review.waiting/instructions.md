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

## Hardware checks (Bob's hands; software halves are done)

2. **Wi-Fi switchover rehearsal**: both APs up, push the list, disable
   *testing*, devices reappear on the hidden show network; disable show 1, and
   the fallback takes over. → `33b/2-network-config-implementation.waiting`.
   The 2026-11-05 switchover moved noor-dusk by hand with `nmcli`; this one
   needs the helper backend filled in first (an agent can do that now that
   slice 0's facts are in).
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
9. **USB helper (67/17)**: reprovision a Pi with no stick inserted; the
   helper is root-owned in `/usr/local/sbin`; one stick mounts, a second is
   ignored, removing the second leaves the first mounted. Checklist in
   `67-repair-pass/17-usb-service-hardening.tied/pi-check.md`.
10. **Engine launch failures (67/18)**: on a Pi, a valid patch still launches
    and plays; an audio config that stops the engine starting is detected and
    rolled back, with audio resuming. Checklist in
    `67-repair-pass/18-engine-launch-failures.tied/pi-check.md`.
11. **Typed events in Pd (80/5)**: on the rig, a scheduled event with a text
    field arrives in Pd intact. Software half: `80-osc-input/3-event-fields-wire`
    (tied). → `80-osc-input/5-pd-event-fields.waiting`.
12. **qtable through bopOS (80/10)**: qtable → dashboard UDP 5552 → Finn Jet /
    Ciro Toast. Kite Choir `trig/play` events with text fields land in sync;
    `/bop/master` fades; `/bop/mute` silences. Software half:
    `80-osc-input/7-osc-input-port` (tied). →
    `80-osc-input/10-qtable-rig-check.waiting`.
14. **Key and mouse input (84/3)**: what's left after the 2026-11-05 session
    with Rachel (keys in a patch, the sim, forwarding from Theo River all
    reported working): the console stops echoing (step 4), unplug/replug
    recovers (5), mouse motion and its span (6). (The sim panel's
    wording was OK'd 2026-11-05.)
    Record in `84-key-input/3-input-hardware-check.waiting/verification.md`.

Moved here from `75-bob-rulings` on 2026-11-05, when that stitch was tied;
Bob's 2026-10-03 note still holds: any current device unless a check needs
specific hardware, and record which device and framework revision.

16. **Wrong-address peripheral**: an error, not zeros. Needs a device with an
    LIS3DH. → `67-repair-pass/3-io-bridge-hardening.waiting`.
17. **Invalid manifest**: write one with the retired `type` grammar, confirm
    the device stays visible, push a good patch, confirm it recovers. Any
    device. → `58-patch-push-workflow/4-invalid-manifest-lockout.waiting`.
18. **Device disable / mute all**: disable from the Device page, then mute
    all; is it actually silent? Most telling on a card with no hardware mixer
    (e.g. HiFiBerry). → `67-repair-pass/2-device-enabled-honesty.waiting`
    and `7-mute-all-honesty`.
19. **Package versions**: run the read-only comparison command in
    `docs/INSTALL.md` on a device; compare against `constraints.txt`.

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
13. Editor input on hardware (59/6, was hardware check 8) — **tested OK** (Bob, 2026-10-28) → `59-i2c-inventory/6-live-sensor-in-patch-edit` tied.
14. Editor input label (59/6, was open item 16) — **"Input source" is fine** (Bob, 2026-10-28) → `59-i2c-inventory/6-live-sensor-in-patch-edit.tied/bob-check.md`.
15. OSC tab mockup (80/8, was open item 19) — Bob pre-approved it; the mockup and `9-osc-tab` are both tied. Removed 2026-11-05.
16. Wi-Fi slice 0 (33b/2, was hardware check 1) — answered by observation: NetworkManager manages wlan0 on Bria Fox (2026-10-28) and noor-dusk (2026-11-05); the NM platform facts are in `33b/2` and glean `networkmanager-wifi`.
17. Wi-Fi power save soak (79, was hardware check 13) — **done**: 11/11 unaided rejoins on noor-dusk after 60 s AP restarts, power save still `off` (2026-11-05). Bob: *"i think we can close 79-wifi-powersave."* → `79-wifi-power-save` tied, `79/3` dropped.
18. Dashboard reconnect loop on Rachel's Mac (67/29, was hardware check 15) — **fixed by the port change** to 5580 (Bob, 2026-11-05) → `67-repair-pass/29-ws-close-reason-check` tied.
19. Wrong-key lockout (33b/3, was hardware check 20) — **dropped**: an edge case where a power cycle is fine (Bob, 2026-11-05).
20. Project menu calls (66/7, was open item 8) — **acknowledged** (Bob, 2026-11-05).
21. Monitor transport labels (71/2, was open item 14) — **OK** (Bob, 2026-11-05) → `71-network-traffic` tied.
22. Module panels (59/9, was open item 15) — **acknowledged** (Bob, 2026-11-05).
23. Update patch and push targets (58/1, 58/3, was open item 18) — **OK** (Bob, 2026-11-05) → both tied.
24. Shared node protocol (69/3, was open item 13) — **approve the narrow extraction** (Bob, 2026-11-05) → `69-complexity/3-shared-node-protocol/ruling.md`, resumed.
25. Node process ownership (67/19, was open item 17) — **approve, amended** (Bob, 2026-11-05): no shim (provision-level guard on Update bopOS instead), one `bopos` command for people, internal entry points kept separate → `67-repair-pass/19-node-process-ownership/ruling.md`, resumed.
26. Pd typed event fields (80/5, was open item 20) — headless Pd 0.55 test (2026-11-05): pass-through fine; **accept** the nested-identity/text-field ambiguity (authoring note in contract §3.2); `bopos~.pd` event `[list]` hides events from bare `[route]` → edit written into `64-pd-edits-owed` (Bob, 2026-11-05). Rig check stays as hardware item 11.
