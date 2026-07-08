#!/usr/bin/env bash
# PD half of the port-sharing spike: two headless PD instances open the real
# pd/bopos.osc.pd (netreceive -u -b 6660); a broadcast /all/aloha goes out;
# a 5550 listener counts the /rpt aloha replies. 2 replies = both instances
# received the same broadcast datagram. Run from anywhere inside the repo.
set -u
REPO="$(cd "$(dirname "$0")" && pwd)"
while [ ! -f "$REPO/tools/simfleet.py" ]; do
  REPO="$(dirname "$REPO")"
  [ "$REPO" = "/" ] && { echo "cannot find repo root"; exit 1; }
done
OUT="${1:-$(dirname "$0")}"
PD="${PD:-pd}"

command -v "$PD" >/dev/null || { echo "pd not found"; exit 1; }

python3 - "$OUT/replies.log" <<'EOF' &
import socket, sys, time
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", 5550))
sock.settimeout(0.5)
end = time.monotonic() + 14
with open(sys.argv[1], "w") as log:
    while time.monotonic() < end:
        try:
            datagram, source = sock.recvfrom(65535)
        except socket.timeout:
            continue
        log.write("{:.3f} {} {!r}\n".format(time.monotonic(), source, datagram))
        log.flush()
EOF
LISTENER=$!

"$PD" -nogui -noprefs -nosound -stderr -open "$REPO/pd/bopos.osc.pd" >"$OUT/pd-a.log" 2>&1 &
PD_A=$!
sleep 1
"$PD" -nogui -noprefs -nosound -stderr -open "$REPO/pd/bopos.osc.pd" >"$OUT/pd-b.log" 2>&1 &
PD_B=$!
sleep 4   # both loadbang alohas done; now the actual receive test

MARK=$(date +%s)
echo "--- sending broadcast /all/aloha 1 to 6660"
python3 - <<'EOF'
import socket, struct

def osc(address, *args):
    def pad(chunk):
        return chunk + b"\0" * ((4 - len(chunk) % 4) % 4)
    message = pad(address.encode() + b"\0")
    message += pad(b"," + b"".join(b"f" for _ in args) + b"\0")
    for value in args:
        message += struct.pack(">f", value)
    return message

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.sendto(osc("/all/aloha", 1.0), ("255.255.255.255", 6660))
EOF

sleep 4
kill "$PD_A" "$PD_B" 2>/dev/null
wait "$LISTENER" 2>/dev/null

echo "--- pd-a bind errors (empty = clean):"
grep -i "bind\|already in use\|error" "$OUT/pd-a.log" || true
echo "--- pd-b bind errors (empty = clean):"
grep -i "bind\|already in use\|error" "$OUT/pd-b.log" || true
echo "--- 5550 datagrams captured: $(wc -l < "$OUT/replies.log")"
echo "--- replies:"
cat "$OUT/replies.log"
