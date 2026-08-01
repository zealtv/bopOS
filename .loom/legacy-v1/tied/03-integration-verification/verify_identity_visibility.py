#!/usr/bin/env python3
"""Static guard for alias-only everyday identity surfaces."""

import pathlib


def repo_root():
    here = pathlib.Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "dashboard" / "server.py").is_file():
            return candidate
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
dashboard = (ROOT / "dashboard/static/js/dashboard.js").read_text()
facilitator = (ROOT / "dashboard/static/js/facilitator.js").read_text()
identity = (ROOT / "dashboard/static/js/device-identity.js").read_text()

checks = {
    "shared everyday helper exposes alias identity only":
        "Object.freeze({alias, primary})" in identity
        and "function technical" not in identity
        and "function uidTail" not in identity
        and "alias(deviceOrUid, installation) || device?.hostname" not in identity,
    "Device roster excludes technical identity":
        "const telemetry=[d.version" in dashboard
        and "Identity.technical(d)" not in dashboard,
    "Seats picker and binding note use alias identity":
        "Identity.primary(binding||seat.bound,installation)" in dashboard
        and "Identity.full(binding||seat.bound,installation)" not in dashboard
        and "Identity.uidTail(seat.bound)" not in dashboard,
    "Assets device selector uses alias identity":
        "Identity.primary(target.device,installation)" in dashboard
        and "Identity.full(target.device,installation)" not in dashboard,
    "facilitator cards use Seat plus alias without technical identity":
        "secondary: Identity.primary(d,installation)" in facilitator
        and "Identity.technical(d)" not in facilitator,
    "selected Device detail retains hostname and full UID":
        "<dt>Hostname</dt>" in dashboard
        and "<dt>UID</dt><dd><code>${esc(d.uid)}</code>" in dashboard,
}

for label, passed in checks.items():
    if not passed:
        raise AssertionError(label)
    print(f"PASS {label}")

print(f"\n{len(checks)}/{len(checks)} checks passed")
