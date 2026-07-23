import socket, sys, time
sys.path.insert(0, "/Users/bob/repos/bopOS/python")
from pyOSC3 import decodeOSC
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try: s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except OSError: pass
s.bind(("", 5550))
print("listening 5550 for heartbeats (Ctrl-C to stop)", flush=True)
last = {}
while True:
    data, src = s.recvfrom(65535)
    try:
        d = decodeOSC(data)
    except Exception:
        continue
    if not d or str(d[0]) != "/hb":
        # also surface other traffic (replies) for context
        print(f"{time.strftime('%H:%M:%S')} {src[0]:15s} {d[0] if d else '?'} {d[2:] if d and len(d)>2 else ''}", flush=True)
        continue
    a = d[2:]
    uid, nid, ver, eng = a[0], a[1], a[2], a[3]
    ip = src[0]
    gap = ""
    now = time.time()
    if ip in last:
        gap = f" (+{now-last[ip]:.1f}s)"
    last[ip] = now
    print(f"{time.strftime('%H:%M:%S')} {ip:15s} HB id={nid} eng={eng} uid={uid} v={ver}{gap}", flush=True)
