import socket, time, sys
sys.path.insert(0, "/Users/bob/repos/bopOS/python")
from pyOSC3 import OSCMessage
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def send(addr, fields, port):
    m = OSCMessage(addr)
    for v, t in fields: m.append(v, t)
    print(f"SEND :{port} {addr} {fields}", flush=True)
    sock.sendto(m.getBinary(), ("127.0.0.1", port)); time.sleep(0.4)
send("/p/gain", [(0.5, "f")], 47123)
for port in (47123, 47124):
    send("/e/do", [], port)
    send("/e/do", [(1.0, "f"), (2.0, "f")], port)
    send("/e/do", [("play", "s")], port)
