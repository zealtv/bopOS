# relay.py
"""
Engine-surface address shaping shared by the production helper and the
audition rig (engine-boundary ratification, 2026-07-12).

Both relays must present the identical selector-stripped localhost surface
to engines. Their socket topology legitimately differs — production: one
engine on 6661 behind a locked shared client; audition: one UDP target per
virtual node — but the address shaping is one implementation so the two
surfaces cannot drift apart.
"""


def shape_provided_term(parts, args):
    """Map selector-split LAN address parts to the engine-facing message.

    parts is the OSC address split on '/' with the leading fleet selector
    retained, e.g. ["all", "os", "master"]. Returns (address, args-list)
    for a relayed provided term, or None for everything else. Selector
    matching and delivery stay with the caller.
    """
    if len(parts) != 3 or not args:
        return None
    if parts[1:] == ["os", "master"]:
        return "/os/master", list(args[:1])
    if parts[1] == "p" and parts[2]:
        return "/p/" + parts[2], list(args)
    return None
