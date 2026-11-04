# Verification so far

## Theo River, 2026-11-04 (agent over Bob's ssh session; Bob pressing pads)

Framework `32b8dd7`.

- Step 1: `groups` lists `input`.
- Step 2: `run/io.log` shows `Input event1 (JoyLabz  Makey Makey v1.30aa
  Keyboard) open` at 15:11:39, plus event2 (Mouse) and event3.
- Step 3: a loopback capture of UDP 6662 (a root Python AF_PACKET script in
  `/tmp`, removed afterwards) recorded `/io/key up|down|left|right|space` and
  `/io/mouse left` from the front pads, 15:18:48–15:19:11. The patch
  (template) had no key print, so Pd's reaction itself was not observed. The
  jumpers (back header) were not used.
- Not yet run: steps 4 (console echo), 5 (unplug/replug), 6 (mouse motion and
  the 2000-count span), 7 and 8.
