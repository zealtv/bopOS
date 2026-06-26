#!/usr/bin/env python3
# rssi_monitor.py
"""
Test utility: poll the io bridge's /system OSC queries and print the replies.

Exercises the real OSC round-trip (sends /system/rssi to the bridge and
listens for the reply), so it verifies the bridge end-to-end -- not just
read_wireless() in isolation.

The bridge replies to PD_PORT (default 6662), so this tool listens there.
That means PD / the autostart stack must NOT be running while you test
(stop it first: bash/stop.sh). If the port is busy it'll tell you.

Usage:
    python rssi_monitor.py                # poll /system/rssi every 1s
    python rssi_monitor.py -n 0.5         # every 0.5s
    python rssi_monitor.py --once         # one query, then exit
    python rssi_monitor.py --id           # also query /system/id each tick
    python rssi_monitor.py --bridge-port 8880 --reply-port 6662
"""

import argparse
import sys
import threading
import time
from datetime import datetime

from pyOSC3 import OSCServer, OSCClient, OSCMessage


def main():
    ap = argparse.ArgumentParser(description="Poll the io bridge /system OSC queries.")
    ap.add_argument("-n", "--interval", type=float, default=1.0,
                    help="seconds between polls (default 1.0)")
    ap.add_argument("--once", action="store_true", help="query once and exit")
    ap.add_argument("--id", action="store_true", help="also query /system/id each tick")
    ap.add_argument("--host", default="127.0.0.1", help="bridge host (default 127.0.0.1)")
    ap.add_argument("--bridge-port", type=int, default=8880,
                    help="bridge command port (default 8880)")
    ap.add_argument("--reply-port", type=int, default=6662,
                    help="port the bridge replies to / we listen on (default 6662 = PD_PORT)")
    args = ap.parse_args()

    # Listen for replies on the port the bridge sends to (PD_PORT).
    try:
        srv = OSCServer((args.host, args.reply_port))
    except OSError as e:
        print(f"Could not bind reply port {args.reply_port}: {e}")
        print("Is PD / the autostart stack running? Stop it first: bash/stop.sh")
        sys.exit(1)

    def on_reply(path, tags, a, source):
        ts = datetime.now().strftime("%H:%M:%S")
        if path == "/system/rssi" and len(a) >= 2:
            link = "no link" if a[1] == 0 else f"link {a[1]}"
            print(f"{ts}  RSSI {a[0]:>4} dBm   {link}")
        elif path == "/system/id":
            print(f"{ts}  ID   {a[0]}")
        else:
            print(f"{ts}  {path} {a}")

    srv.addMsgHandler("default", on_reply)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    cli = OSCClient()
    cli.connect((args.host, args.bridge_port))

    def query():
        cli.send(OSCMessage("/system/rssi"))
        if args.id:
            time.sleep(0.05)
            cli.send(OSCMessage("/system/id"))

    mode = "once" if args.once else f"every {args.interval}s"
    extra = " + /system/id" if args.id else ""
    print(f"Polling {args.host}:{args.bridge_port} /system/rssi{extra} ({mode}); "
          f"listening on {args.reply_port}. Ctrl+C to stop.")
    try:
        query()
        if args.once:
            time.sleep(0.5)
        else:
            while True:
                time.sleep(args.interval)
                query()
    except KeyboardInterrupt:
        print()
    finally:
        srv.close()


if __name__ == "__main__":
    main()
