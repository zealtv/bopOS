import socket, time, sys
sys.path.insert(0, "/Users/bob/repos/bopOS/python")
from pyOSC3 import OSCMessage
cases = [
    ("zero-field", "trig", []),
    ("mixed f/i/s", "trig", [(0.5, "f"), (7, "i"), ("play", "s")]),
    ("A: /e/trig + text 'play'", "trig", [("play", "s")]),
    ("B: /e/trig/play, no fields", "trig/play", []),
    ("numeric-looking text '42'", "kite/trig", [("42", "s")]),
    ("int at 2^24", "trig", [(16777216, "i")]),
    ("numeric segment /e/scene/3", "scene/3", [(1.0, "f")]),
    ("text with ; , $ { }", "trig", [("a;b", "s"), ("x,y", "s"), ("$1", "s"), ("{q}", "s")]),
]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for label, identity, fields in cases:
    msg = OSCMessage("/e/" + identity)  # as fire_event_to_engine builds it
    for v, t in fields:
        msg.append(v, t)
    print(f"SEND {label}: /e/{identity} {fields}", flush=True)
    sock.sendto(msg.getBinary(), ("127.0.0.1", 47123))
    time.sleep(0.4)
