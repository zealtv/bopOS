# sys_wireless.py
"""
WiFi link metrics from /proc/net/wireless (pure stdlib, no subprocess).

Single source of truth for link health so the same value can feed an OSC
query, a future heartbeat, or a status screen ("computed once").
"""

WIRELESS_PROC = "/proc/net/wireless"


def read_wireless(iface=None):
    """
    Return (rssi_dbm, link_quality) for `iface`, or for the first listed
    wireless interface when `iface` is None. Return (None, None) when no
    wireless interface is present (e.g. WiFi down). Both values are ints.

    /proc/net/wireless row looks like:
        wlan0: 0000   70.  -29.  -256  ...
                      ^^^   ^^^^
                      qual  signal level (dBm)
    """
    try:
        with open(WIRELESS_PROC) as f:
            for line in f:
                line = line.strip()
                if ":" not in line:
                    continue
                row_iface = line.split(":", 1)[0].strip()
                if iface is None or row_iface == iface:
                    fields = line.split()
                    quality = int(float(fields[2].rstrip(".")))
                    rssi_dbm = int(float(fields[3].rstrip(".")))
                    return rssi_dbm, quality
    except (OSError, ValueError, IndexError):
        pass
    return None, None
