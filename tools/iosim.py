#!/usr/bin/env python3
"""
iosim.py -- fake the I2C bridge, so a patch can be developed without hardware.

`python/io/main.py` polls its peripherals and sends ONE OSC bundle per tick to
127.0.0.1:6662, where the engine's [netreceive -u -b 6662] -> [oscparse] ->
[s bopos-io] picks it up. Nothing about that is privileged: any process can
send the same messages, so a patch's [r bopos-io] -> [route <name>] chain can
be exercised with no bridge, no bus and no chip.

That makes this two tools in one:

  * on the laptop, it IS the peripheral -- develop the patch against simulated
    button presses;
  * on a real node, it injects a press ALONGSIDE the running bridge, which
    splits "is the patch wrong?" from "is the sensor wrong?" in one move.

Usage
-----
  # hold three buttons up (3.3 V) and pulse A0 low every 2 s, at 10 Hz
  iosim.py --name adc --rest 3.3,3.3,3.3,3.3 --press 0 --every 2

  # one press of A1, treating rest as low and press as high (A1 is inverted
  # on the Ciro Toast rig)
  iosim.py --name adc --rest 3.3,0,3.3,3.3 --press 1 --once

  # drive it by hand: type channel numbers, Enter to fire, q to quit
  iosim.py --name adc --rest 3.3,3.3,3.3,3.3 --interactive

  # watch what a bridge is really sending (only when PD is NOT holding 6662)
  iosim.py --listen

Defaults describe the ADS1115 on the Ciro Toast rig: four channels, resting
near rail, a press pulling one to ground.
"""

import argparse
import socket
import sys
import threading
import time

try:
    from pyOSC3 import OSCBundle, OSCMessage, OSCServer
except ImportError:
    sys.exit("iosim: needs pyOSC3 (pip install pyOSC3, or run from the bopos venv)")

DEFAULT_PORT = 6662     # where the engine listens for peripheral data
DEFAULT_HOST = "127.0.0.1"


def send(sock, host, port, name, values):
    """One bundle, one message -- exactly the shape io/main.py emits."""
    bundle = OSCBundle()
    msg = OSCMessage("/" + name)
    for v in values:
        msg.append(float(v))
    bundle.append(msg)
    sock.sendto(bundle.getBinary(), (host, port))


def run_send(args):
    rest = [float(x) for x in args.rest.split(",")]
    if args.press >= len(rest):
        sys.exit("iosim: --press %d but --rest has %d channels"
                 % (args.press, len(rest)))

    # A press drives the channel to the OTHER rail, whatever this one rests at.
    pressed = list(rest)
    pressed[args.press] = args.pressed_value
    if args.pressed_value is None:
        pressed[args.press] = 0.0 if rest[args.press] > 1.65 else 3.3

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    period = 1.0 / args.rate
    print("iosim -> %s:%d  /%s  rest %s  press A%d -> %.2f  at %g Hz"
          % (args.host, args.port, args.name, rest, args.press,
             pressed[args.press], args.rate))

    if args.interactive:
        return run_interactive(sock, args, rest)

    # Start at rest for a beat, so the patch's [change] has a baseline to
    # differ from -- a press as the very first value it ever sees is not an
    # edge, and that alone can look like a dead chain.
    t_next_press = time.time() + min(args.every, 1.0)
    holding_until = 0.0
    fired = 0
    try:
        while True:
            now = time.time()
            if now >= t_next_press and not (args.once and fired):
                holding_until = now + args.hold
                t_next_press = now + args.every
                fired += 1
                print("  press A%d  (%d)" % (args.press, fired))
            values = pressed if now < holding_until else rest
            send(sock, args.host, args.port, args.name, values)
            if args.once and fired and now >= holding_until:
                send(sock, args.host, args.port, args.name, rest)
                print("iosim: one press sent, done")
                return
            time.sleep(period)
    except KeyboardInterrupt:
        send(sock, args.host, args.port, args.name, rest)
        print("\niosim: released, stopped")


def run_interactive(sock, args, rest):
    """Type a channel number + Enter to pulse it. Empty line repeats. q quits.

    A background thread streams the CURRENT values at the poll rate, exactly as
    the bridge does. That is not decoration: the patch's [change] holds the last
    value it saw, so a simulator that only transmits during a press makes the
    first press look like no change at all and swallows it.
    """
    state = {"values": list(rest), "running": True}

    def pump():
        period = 1.0 / args.rate
        while state["running"]:
            send(sock, args.host, args.port, args.name, state["values"])
            time.sleep(period)

    pumper = threading.Thread(target=pump, daemon=True)
    pumper.start()

    print("streaming rest at %g Hz; type a channel number then Enter to press it;"
          " empty repeats; q quits" % args.rate)
    last = None
    try:
        while True:
            line = sys.stdin.readline()
            if not line or line.strip().lower() == "q":
                break
            token = line.strip()
            if token == "" and last is not None:
                token = last
            if not token.isdigit():
                continue
            ch = int(token)
            if ch >= len(rest):
                print("  no channel A%d" % ch)
                continue
            last = token
            pressed = list(rest)
            pressed[ch] = 0.0 if rest[ch] > 1.65 else 3.3
            state["values"] = pressed
            time.sleep(args.hold)
            state["values"] = list(rest)
            print("  A%d  %.2f -> %.2f -> %.2f" % (ch, rest[ch], pressed[ch], rest[ch]))
    except KeyboardInterrupt:
        pass
    state["running"] = False
    pumper.join(timeout=1.0)
    send(sock, args.host, args.port, args.name, rest)
    print("iosim: stopped")


def run_listen(args):
    """Print whatever arrives. Only works when nothing else holds the port."""
    print("iosim: listening on %s:%d -- ctrl-c to stop" % (args.host, args.port))
    server = OSCServer((args.host, args.port))

    def show(addr, tags, values, source):
        print("%8.2f  %-12s %s" % (time.time() % 1000, addr,
                                   "  ".join("%7.3f" % v if isinstance(v, float)
                                             else str(v) for v in values)))

    server.addMsgHandler("default", show)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.close()
        print("\niosim: stopped")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", default="adc",
                   help="peripheral name = OSC address, as given to io create (default: adc)")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help="engine's peripheral port (default: %d)" % DEFAULT_PORT)
    p.add_argument("--rest", default="3.3,3.3,3.3,3.3",
                   help="comma-separated resting values, one per element")
    p.add_argument("--press", type=int, default=0, help="channel index to press")
    p.add_argument("--pressed-value", type=float, default=None,
                   help="value while pressed (default: the opposite rail from rest)")
    p.add_argument("--rate", type=float, default=10.0, help="send rate in Hz")
    p.add_argument("--every", type=float, default=2.0, help="seconds between presses")
    p.add_argument("--hold", type=float, default=0.3, help="seconds to hold a press")
    p.add_argument("--once", action="store_true", help="send a single press and exit")
    p.add_argument("--interactive", action="store_true",
                   help="press channels by hand from stdin")
    p.add_argument("--listen", action="store_true",
                   help="receive and print instead of sending")
    args = p.parse_args()

    if args.listen:
        run_listen(args)
    else:
        run_send(args)


if __name__ == "__main__":
    main()
