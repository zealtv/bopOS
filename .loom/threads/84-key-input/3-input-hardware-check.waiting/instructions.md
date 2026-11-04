# 3-input-hardware-check

Bob's hands; he planned it for shortly after 2026-11-04. Software half: commits
on 2026-11-04 (`84-key-input`). Needs a node updated to that framework.

1. `groups pi` on the node shows `input`. Existing nodes weren't
   reprovisioned; if it's missing, run `sudo usermod -aG input pi` and
   restart bopOS. The bridge log says `Input eventN (...) not readable` when
   it is.
2. Plug in the Makey Makey. Within ~2 s the bridge log shows
   `Input eventN (<name>) open` for each of its interfaces.
3. In a patch: `[r bopos-io] → [route io] → [route key mouse]` → print.
   Front-side arrows and space arrive as `up 1`/`up 0` …; the click as
   `mouse left 1`/`0`; the back header as `w a s d f g`.
4. The tty1 console (HDMI, if attached) no longer echoes the keys: the grab
   held.
5. Unplug while holding a pad: a release arrives. Replug: it reopens and
   works without restarting bopOS.
6. If the Makey Makey's mouse-motion pins are used: `xy` and `move` arrive.
   Note roughly how far one touch moves `xy`; that measures the 2000-count
   span (an estimate as of 2026-11-04).
7. Optional: `python3 tools/iosim.py --key space` over SSH on the node
   reaches the patch beside the real device.

Record what ran (glean `hardware-claims`) in `verification.md` here.
8. With Patch Edit's input set to the node (needs `5-device-input-forwarding`
   on both the node and the dashboard): pressing a pad prints in the editor's
   Pd. Moving the mouse prints `xy` about 10 times a second, not faster.
   Switching the input away from the node while holding a pad sends a release.
