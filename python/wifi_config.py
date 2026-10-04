"""Strict Wi-Fi wire validation and redacted state; no network backend here."""
import json
import subprocess

# ISO 3166-1 alpha-2, from the public-domain IANA iso3166.tab (2025-07-01).
COUNTRIES = frozenset("AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW".split())
HELPER = "/usr/local/sbin/bopos-set-wifi"


def ssid(value):
    if not isinstance(value, str):
        raise ValueError("invalid")
    try:
        length = len(value.encode("utf-8"))
    except UnicodeError:
        raise ValueError("invalid") from None
    if not 1 <= length <= 32:
        raise ValueError("invalid")
    return value


def validate(value, existing=None):
    if not isinstance(value, dict) or set(value) != {"country", "networks"}:
        raise ValueError("invalid")
    if not isinstance(value["country"], str) or value["country"] not in COUNTRIES:
        raise ValueError("invalid")
    if not isinstance(value["networks"], list):
        raise ValueError("invalid")
    result, seen = [], set()
    for row in value["networks"]:
        if not isinstance(row, dict) or set(row) != {"ssid", "hidden", "enabled", "psk"}:
            raise ValueError("invalid")
        name = ssid(row["ssid"])
        if name in seen or type(row["hidden"]) is not bool or type(row["enabled"]) is not bool:
            raise ValueError("invalid")
        secret = row["psk"]
        if secret is not None and (not isinstance(secret, str) or not 8 <= len(secret) <= 63
                                  or any(ord(c) < 32 or ord(c) > 126 for c in secret)):
            raise ValueError("invalid")
        if secret is None and existing is not None and name not in existing:
            raise ValueError("invalid")
        seen.add(name)
        result.append(dict(ssid=name, hidden=row["hidden"], enabled=row["enabled"], psk=secret))
    if not any(row["enabled"] for row in result):
        raise ValueError("invalid")
    return {"country": value["country"], "networks": result}


def metadata(config):
    return {"country": config["country"], "networks": [
        {key: row[key] for key in ("ssid", "hidden", "enabled")}
        for row in config["networks"]]}


def clean_list(value):
    """Stored authoring list may be empty; never retain extra fields/secrets."""
    if not isinstance(value, dict) or not isinstance(value.get("country"), str) or value.get("country") not in COUNTRIES:
        return {"country": "GB", "networks": []}
    rows = value.get("networks")
    if not isinstance(rows, list):
        return {"country": "GB", "networks": []}
    cleaned, seen = [], set()
    for row in rows:
        try:
            name = ssid(row.get("ssid"))
            if name in seen or type(row.get("hidden")) is not bool or type(row.get("enabled")) is not bool:
                raise ValueError("invalid")
        except (ValueError, AttributeError):
            return {"country": "GB", "networks": []}
        seen.add(name)
        cleaned.append({"ssid": name, "hidden": row["hidden"], "enabled": row["enabled"]})
    return {"country": value["country"], "networks": cleaned}


def redacted(value):
    """Project a helper/node observation onto the exact public Wi-Fi schema."""
    if not isinstance(value, dict) or value.get("managed") is not True:
        return {"managed": False}
    try:
        country = value["country"]
        if not isinstance(country, str) or country not in COUNTRIES:
            raise ValueError("invalid")
        active = value["active"]
        if active is not None:
            ssid(active)
        rows, seen = [], set()
        if not isinstance(value["networks"], list) or not isinstance(value["unmanaged"], list):
            raise ValueError("invalid")
        for row in value["networks"]:
            name = ssid(row["ssid"])
            if name in seen or any(type(row[key]) is not bool for key in ("hidden", "enabled", "secret")):
                raise ValueError("invalid")
            seen.add(name)
            rows.append({key: row[key] for key in ("ssid", "hidden", "enabled", "secret")})
        return {"managed": True, "country": country, "active": active,
                "networks": rows, "unmanaged": [ssid(name) for name in value["unmanaged"]]}
    except (ValueError, KeyError, TypeError):
        return {"managed": False}


def helper_status(helper=HELPER):
    try:
        result = subprocess.run(["sudo", "-n", helper, "--status"],
                                capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            return redacted(json.loads(result.stdout))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return {"managed": False}


def apply(payload, helper=HELPER):
    try:
        config = validate(json.loads(payload))
    except (ValueError, TypeError):
        return "err", "invalid", {"managed": False}
    observed = helper_status(helper)
    if not observed["managed"]:
        return "err", "unavailable", observed
    try:
        config = validate(config, {row["ssid"] for row in observed["networks"] if row["secret"]}
                          | set(observed["unmanaged"]))
    except ValueError:
        return "err", "invalid", observed
    try:
        result = subprocess.run(["sudo", "-n", helper], input=json.dumps(config),
                                capture_output=True, text=True, timeout=15)
        phase = {0: "applied", 2: "invalid", 3: "unavailable"}.get(result.returncode, "failed")
        state = redacted(json.loads(result.stdout))
        if phase == "applied" and not state["managed"]:
            phase = "failed"
        return "ok" if phase == "applied" else "err", phase, state
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "err", "failed", observed
