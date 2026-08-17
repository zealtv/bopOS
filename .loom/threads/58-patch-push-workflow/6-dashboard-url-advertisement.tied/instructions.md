# 6-dashboard-url-advertisement

The address the operator opens the dashboard at silently becomes the address
every node is told to fetch patches from. Open it at `0.0.0.0:8080` — which is
the address `run.sh` all but invites, since it prints `--host 0.0.0.0` in its
own banner comment — and every patch push in the venue fails, with the failure
surfacing as a `fetch: err` on the device row and nothing else.

Observed on eiko Maple, 2026-08-17, with Bob driving. See
`incident-2026-08-17-eiko-maple.md` beside this file for the full trace.

Bob's framing: *"if all we need to do is run the dash from the ip 192...xxx
then let's add a stitch to change the output of the run script to point to the
proper URL."* That is the headline and the smallest useful fix. It is not the
whole defect — see "The second half" below — and this stitch owns both, because
fixing only the printed URL leaves a bookmark-shaped landmine for anyone who
already has one.

## Measured starting state

`dashboard/server.py:2899-2912`:

```python
def public_url(self, ws, device_uid=None):
    configured = getattr(self.args, "public_url", None)
    if configured:
        return configured.rstrip("/")
    scheme = "https" if ws is not None and ws.url.scheme == "wss" else "http"
    host = ws.headers.get("host") if ws is not None else None
    request_hostname = ws.url.hostname if ws is not None else None
    loopback = request_hostname in (None, "localhost")
    if request_hostname not in (None, "localhost"):
        try:
            loopback = ipaddress.ip_address(request_hostname).is_loopback
        except ValueError:
            loopback = False
    if not loopback:
        return f"{scheme}://{host}"
```

`ipaddress.ip_address("0.0.0.0").is_loopback` is **False** (it is
`is_unspecified`), so `0.0.0.0` takes the `if not loopback` branch and is
handed to the node verbatim. The node then resolves `0.0.0.0` in *its own*
context, where it means "this host", and the HTTP GET fails against itself.
`::` has the identical property and the same hole.

The loopback path immediately below it is correct and well-reasoned — it
derives a device-reachable source address per device via `source_for_peer`,
with a named `ValueError` telling the operator to use `--public-url`. An
unspecified address should have been going down that same path all along. It is
strictly less usable than `localhost`, which works today.

`run.sh:29`:

```sh
echo "==> Dashboard starting (default http://localhost:8080/  ·  Ctrl-C to stop)"
exec "$PYTHON" "$SCRIPT_DIR/dashboard/server.py" --host 0.0.0.0 "$@"
```

The printed URL is `localhost`, which *works*. The trap is the surrounding
text: the header comment says "bound to all interfaces (--host 0.0.0.0) so real
nodes on the venue LAN can reach it", the flag is visible on the exec line, and
`dashboard/README.md:121` leads with the bare
`python dashboard/server.py --host 0.0.0.0` form. An operator reading any of
those and typing `0.0.0.0:8080` into a browser gets a dashboard that looks
completely healthy and cannot push a patch to anything.

Note the printed URL also ignores `--port`, so `./run.sh --port 9000` prints a
URL that is simply wrong.

## What the operator sees

Nothing that names the cause. The deploy runs, `/os/fetch` goes out on the
wire, the node replies `/os/fetched <slot> err`, the device row shows
`fetch: {"patch:treeo": "err"}` and `patch_badge: missing`, and every retry
re-derives the same unusable URL and fails the same way. There is no message
anywhere containing the string that would solve it.

Worth knowing while diagnosing: this looks very like `5-fetch-tombstone-lockout`
from the row, and is not. The distinguishing evidence is on the wire — a
tombstone lockout sends **no** `/os/fetch` at all, whereas this sends one and
gets `err` back. Check the OSC out console before reaching for the tombstone
explanation.

## The change

**1. `run.sh` prints a device-reachable URL.** Resolve the LAN address of the
interface the venue is on and print `http://<ip>:<port>/`, honouring `--port`
if the operator passed one. Keep it honest when it cannot tell — a machine with
several plausible interfaces should say so rather than pick confidently, and
`localhost` remains a correct fallback to print because the loopback path
handles it properly.

Judgement call this stitch must make and record: whether `run.sh` should also
pass `--public-url` for the address it just resolved. It would make the printed
URL and the fetch URL provably the same thing, which is the property that
actually matters — but it also hard-codes one interface at startup on a
multi-homed machine, where the existing per-device `source_for_peer` derivation
is strictly better. Cheapest defensible answer is probably *print, don't pass*,
and let `public_url` keep deriving per device. Do not assume it; decide it.

**2. The second half — `public_url` must refuse an unspecified address.**
Treat `0.0.0.0` and `::` the way `localhost` is treated: fall through to the
per-device route derivation. `ipaddress` gives this directly via
`.is_unspecified`, so this is a small change to one condition. This is what
protects the operator who already has `http://0.0.0.0:8080` bookmarked, or who
runs `server.py` directly without `run.sh` — neither of whom is helped by a
better banner.

Consider whether an unroutable *hostname* deserves the same treatment. It does
not obviously: a venue may legitimately reach the dashboard by a name the nodes
also resolve, and the `except ValueError: loopback = False` branch is what makes
that work. Leave it alone unless there is evidence, and say so either way.

**3. Say it once in the docs.** `dashboard/README.md`'s `--public-url` sentence
currently explains only the `localhost` derivation. It should name the
`0.0.0.0` trap explicitly, because that string is what an operator will search
for.

## Verification

Software gate. The whole defect is reachable headlessly: `public_url` is a pure
function of the websocket's host header and the device's IP, so a unit test can
pin `0.0.0.0`, `::`, `localhost`, `127.0.0.1` and a real LAN address against
their expected derivations without a browser or a node. That test is the
durable artifact — put it in `tests/` per the testing-strategy ruling, not in
the stitch.

The `run.sh` half is a shell assertion: run it with and without `--port`, check
the printed URL matches what the server bound and is not `0.0.0.0`.

Hardware gate is already discharged for the *healthy* path and does not need
redoing: eiko Maple converged end to end in 4 s once the fetch URL was
`http://192.168.8.223:8080` (fetch → `ok` in 70 ms, switch, badge `current`,
Pd up on `patches/treeo/main.pd`). What has **not** been observed on hardware is
the fix itself — that a node fed `0.0.0.0` now gets a derived URL instead. Do
that on the rig before tying, and record the split honestly if it does not run.

## Carry this finding forward

Two things about `public_url` are load-bearing and were not obvious:

* it is the one place where a **UI-side** detail (which URL the operator typed)
  silently determines a **node-side** outcome (whether a fetch can succeed), and
  it does so per websocket connection, so two operators on two addresses get two
  different fetch behaviours from the same running dashboard;
* its failure is attributed to the device. Every symptom — `err`, `missing`, a
  Sync button that appears to do nothing — points at the node, and the node is
  healthy. The 2026-08-17 session spent its whole diagnosis on the Pi before the
  cause turned out to be the browser's address bar.
