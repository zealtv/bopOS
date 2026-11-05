import socket, time, sys
sys.path.insert(0, "/Users/bob/repos/bopOS/python")
from pyOSC3 import OSCMessage
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for identity, fields in [("trig", []), ("trig", [("play","s")]), ("trig", [(16777216,"i")]), ("trig", [(16777215,"i")])]:
    m = OSCMessage("/e/" + identity)
    for v, t in fields: m.append(v, t)
    print("SEND", identity, fields, flush=True)
    sock.sendto(m.getBinary(), ("127.0.0.1", 47123)); time.sleep(0.4)
