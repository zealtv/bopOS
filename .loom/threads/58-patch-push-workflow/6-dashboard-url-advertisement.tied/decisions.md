# Decisions — 6-dashboard-url-advertisement

## D1. `run.sh` prints, it does not pass `--public-url`

The stitch named this as a judgement call and it is settled as *print, don't
pass*, for the reason it anticipated: passing the flag would freeze one
interface at startup, and `public_url`'s per-device `source_for_peer`
derivation is strictly better on a multi-homed machine — it answers the
question per node, at fetch time, from the actual route. The banner's job is to
stop the operator typing an address that cannot work; it is not the mechanism
that makes fetches correct. With the second half in place (D2) the printed URL
and the fetch URL agree whichever of the printed addresses the operator opens,
including `localhost`.

## D2. `public_url` treats an unspecified address like loopback

`0.0.0.0` and `::` fall through to the per-device route derivation, via
`address.is_loopback or address.is_unspecified`. This is what protects the
operator with a `http://0.0.0.0:8080` bookmark and the one running
`server.py` directly, neither of whom ever reads `run.sh`'s banner.

## D3. An unresolvable *hostname* is left alone — stated, not skipped

The stitch asked for a verdict either way. No change: the `except ValueError`
branch is what lets a venue reach the dashboard by a name the nodes also
resolve, and there is no evidence of a name that resolves for the browser and
not for the nodes. `test_unresolvable_hostname_is_left_alone` pins it, so a
later broadening is a deliberate act rather than a drift.

## D4. A multi-homed machine gets no confident headline

First cut headlined the first address found and, on this laptop, that was the
Tailscale CGNAT address (`100.113.184.66`) ahead of the venue LAN
(`192.168.8.218`) — a confident wrong answer, which is the failure mode the
stitch warned against. Now: exactly one address gets a headline; several get a
list with RFC1918 first and no pick; none falls back to `localhost` with a
pointer to `--public-url`. `--port` is parsed from the passed-through arguments
in both `--port N` and `--port=N` forms, so the printed URL matches what the
server binds.

## D5. The stale `enum` note in CLAUDE.md is corrected in place

The incident's second false lead was caused by a CLAUDE.md sentence describing
the pre-`kind` grammar as if current. It is a dated record, so it is marked as
stale rather than rewritten, naming `python/manifest.py:20-24` as the authority.
