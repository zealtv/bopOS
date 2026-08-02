"""Show document model, persistence, and edit operations (show-tab stitch 2).

Schema, storage location, uid scheme, and validation rules are fixed by
`.notes/show-tab-design-2026-07-18.md` sec 2; this module implements exactly
that. A show document is one JSON-shaped dict:

    {"schema": 1, "name": "opening-set", "items": [...]}

`items` is a flat, order-significant array mixing `"step"` and `"divider"`
entries (single-column-agnostic on purpose -- see the design note). Section
derivation (maximal runs of steps split on dividers) is a pure function over
that array, independent of persistence.

This module is deliberately separable: it never imports `server` or
`osc_bridge`, so it can be unit-tested headless and reused by the future
playback engine (stitch 3) without pulling in the WS/OSC surface.
"""

import copy
import json
import math
import os
import re
import secrets
import sys

SCHEMA = 1
UID_RE = re.compile(r"[0-9a-f]{8}")
TARGET_RE = re.compile(r"all|[0-9]+|g[0-9]+")
NAMED_GROUP_PREFIX = "group:"
PATCH_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
CONTENT_FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")
SCHEMA_FINGERPRINT_RE = re.compile(r"sha256:[0-9a-f]{64}")
MESSAGE_KINDS = frozenset(("osc", "reference"))
PRESET_ADDRESS_PREFIX = "/preset/"
THEN_ACTION_TYPES = frozenset((
    "stop", "play_again", "next_step", "previous_step",
    "any_in_section", "other_in_section", "goto",
    "next_section", "previous_section",
))

# Show arguments are OSC wire tags, not manifest declaration kinds. Keep this
# grammar local so a declaration-language change cannot alter stored messages.
_REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if _REPO_DIR not in sys.path:
    sys.path.insert(0, _REPO_DIR)
from python import manifest as patch_manifest  # noqa: E402

ARG_TYPES = ("i", "f", "s")


# --------------------------------------------------------------------------
# Construction and cleaning (validation)
# --------------------------------------------------------------------------

def empty_show(name=""):
    """A fresh show document: valid schema, no items."""
    return {"schema": SCHEMA, "name": str(name), "items": []}


def clean_uid(value):
    return value if isinstance(value, str) and UID_RE.fullmatch(value) else None


def clean_target(value):
    # 5c amendment (design note sec 2 amendment): a target is a non-empty
    # list of selectors -- "all", a decimal Seat id string, or "g<group-id>",
    # each the literal selector passed into OSCBridge.set_param. A legacy
    # single selector string still loads and normalizes to a one-item list;
    # duplicates collapse and "all" subsumes every other selector.
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value:
        return None
    selectors = []
    for raw in value:
        if not isinstance(raw, str):
            return None
        if raw.startswith(NAMED_GROUP_PREFIX):
            name = raw[len(NAMED_GROUP_PREFIX):]
            if not name or name != name.strip() or len(name) > 48:
                return None
            raw = NAMED_GROUP_PREFIX + name
        elif not TARGET_RE.fullmatch(raw):
            return None
        if raw not in selectors:
            selectors.append(raw)
    return ["all"] if "all" in selectors else selectors


def clean_arg(value):
    if not isinstance(value, dict):
        return None
    kind = value.get("type")
    if kind not in ARG_TYPES:
        return None
    raw = value.get("value")
    if kind == "s":
        return {"type": "s", "value": raw} if isinstance(raw, str) else None
    if isinstance(raw, bool):
        return None
    try:
        number = float(raw) if kind == "f" else int(raw)
    except (TypeError, ValueError):
        return None
    if kind == "f" and not math.isfinite(number):
        return None
    return {"type": kind, "value": number}


def clean_reference(value):
    """Validate one authored content reference carried by a Show message.

    The payload is deliberately content-generic: this foundation knows that
    composition content is a patch identified by name + fingerprint, but not
    what operation will consume it. The preset-message stitch adds the
    optional schema applicability fingerprint without changing the envelope.
    """
    if not isinstance(value, dict):
        return None
    content = value.get("content")
    if not isinstance(content, dict):
        return None
    name = content.get("name")
    fingerprint = content.get("fingerprint")
    if (not isinstance(name, str) or PATCH_NAME_RE.fullmatch(name) is None
            or not isinstance(fingerprint, str)
            or CONTENT_FINGERPRINT_RE.fullmatch(fingerprint) is None):
        return None
    cleaned = {"content": {"name": name, "fingerprint": fingerprint}}
    schema = value.get("schema")
    if schema is not None:
        if (not isinstance(schema, str)
                or SCHEMA_FINGERPRINT_RE.fullmatch(schema) is None):
            return None
        cleaned["schema"] = schema
    return cleaned


def preset_message_parts(message):
    """Return ``(patch, slug, duration_ms, curve)`` for a preset reference.

    Preset messages are authored composition references, not OSC datagrams.
    Keeping their small argument grammar here gives load, edit, playback and
    flattening one definition of the pseudo-address.
    """
    if not isinstance(message, dict):
        return None
    address = message.get("address")
    if not isinstance(address, str) or not address.startswith(PRESET_ADDRESS_PREFIX):
        return None
    parts = address.split("/")
    if (len(parts) != 4 or parts[:2] != ["", "preset"]
            or PATCH_NAME_RE.fullmatch(parts[2]) is None or not parts[3]):
        return None
    reference = message.get("reference")
    if (message.get("kind") != "reference" or not isinstance(reference, dict)
            or reference.get("content", {}).get("name") != parts[2]
            or "schema" not in reference):
        return None
    args = message.get("args", [])
    if not isinstance(args, list) or len(args) > 2:
        return None
    duration = curve = None
    if args:
        first = args[0]
        if (not isinstance(first, dict) or first.get("type") not in {"i", "f"}
                or isinstance(first.get("value"), bool)):
            return None
        try:
            duration = float(first["value"])
        except (KeyError, TypeError, ValueError):
            return None
        if not math.isfinite(duration) or duration < 0:
            return None
    if len(args) == 2:
        token = args[1]
        if not isinstance(token, dict) or token.get("type") != "s":
            return None
        raw = token.get("value")
        if not isinstance(raw, str) or not raw.startswith("c:"):
            return None
        try:
            curve = float(raw[2:])
        except ValueError:
            return None
        if not math.isfinite(curve):
            return None
    return parts[2], parts[3], duration, curve


def clean_message(value):
    if not isinstance(value, dict):
        return None
    uid = clean_uid(value.get("uid"))
    if uid is None:
        return None
    alias = value.get("alias")
    if alias is not None and not isinstance(alias, str):
        return None
    address = value.get("address")
    if not isinstance(address, str) or not address.startswith("/") or address.strip() != address:
        return None
    raw_args = value.get("args", [])
    if not isinstance(raw_args, list):
        return None
    args = []
    for raw_arg in raw_args:
        arg = clean_arg(raw_arg)
        if arg is None:
            return None
        args.append(arg)
    target = clean_target(value.get("target"))
    if target is None:
        return None
    kind = value.get("kind", "osc")
    if kind not in MESSAGE_KINDS:
        return None
    reference = value.get("reference")
    if kind == "reference":
        reference = clean_reference(reference)
        if reference is None:
            return None
    elif reference is not None:
        return None
    cleaned = {"kind": kind, "uid": uid, "alias": alias, "address": address,
               "args": args, "target": target}
    if reference is not None:
        cleaned["reference"] = reference
    if address.startswith(PRESET_ADDRESS_PREFIX) and preset_message_parts(cleaned) is None:
        return None
    return cleaned


def _group_entries(groups):
    if isinstance(groups, dict):
        values = groups.values()
    elif isinstance(groups, (list, tuple)):
        values = groups
    else:
        return []
    entries = []
    for value in values:
        if not isinstance(value, dict):
            continue
        group_id, name = value.get("id"), value.get("name")
        if (isinstance(group_id, bool) or not isinstance(group_id, int)
                or group_id < 0 or not isinstance(name, str) or not name):
            continue
        entries.append({"id": group_id, "name": name})
    return entries


def resolve_targets(value, groups):
    """Resolve portable group names to the current venue's wire selectors.

    Missing or ambiguous names are omitted from the result and returned as
    non-blocking warnings. Other valid selectors pass through unchanged.
    """
    targets = clean_target(value)
    if targets is None:
        return [], [{"code": "invalid_target", "target": value,
                     "message": "The message has an invalid target."}]
    if targets == ["all"]:
        return targets, []
    entries = _group_entries(groups)
    resolved, warnings = [], []
    for target in targets:
        if not target.startswith(NAMED_GROUP_PREFIX):
            if target not in resolved:
                resolved.append(target)
            continue
        name = target[len(NAMED_GROUP_PREFIX):]
        matches = sorted(
            (entry for entry in entries if entry["name"] == name),
            key=lambda entry: entry["id"],
        )
        if not matches:
            warnings.append({
                "code": "missing_group",
                "target": target,
                "message": f'Group "{name}" does not exist in this venue.',
            })
            continue
        if len(matches) > 1:
            warnings.append({
                "code": "ambiguous_group",
                "target": target,
                "message": f'Group "{name}" is ambiguous in this venue.',
            })
            continue
        selector = f'g{matches[0]["id"]}'
        if selector not in resolved:
            resolved.append(selector)
    return resolved, warnings


def show_target_warnings(show, groups):
    """Return every derived portable-target warning in document order."""
    warnings = []
    for item in show.get("items", []) if isinstance(show, dict) else []:
        if not isinstance(item, dict) or item.get("kind") != "step":
            continue
        for message in item.get("messages", []):
            _resolved, message_warnings = resolve_targets(
                message.get("target"), groups)
            warnings.extend({
                **warning,
                "step_uid": item.get("uid"),
                "message_uid": message.get("uid"),
            } for warning in message_warnings)
    return warnings


def show_reference_warnings(show, patch_fingerprints, schema_fingerprints):
    """Return derived, non-blocking drift warnings for preset references."""
    warnings = []
    for item in show.get("items", []) if isinstance(show, dict) else []:
        if not isinstance(item, dict) or item.get("kind") != "step":
            continue
        for message in item.get("messages", []):
            parts = preset_message_parts(message)
            if parts is None:
                continue
            patch, _slug, _duration, _curve = parts
            reference = message["reference"]
            authored_patch = reference["content"]["fingerprint"]
            current_patch = patch_fingerprints.get(patch)
            authored_schema = reference["schema"]
            current_schema = schema_fingerprints.get(patch)
            message_warnings = []
            if current_patch is None:
                message_warnings.append({
                    "code": "missing_patch",
                    "message": f'Patch "{patch}" is not installed.',
                })
            elif current_patch != authored_patch:
                message_warnings.append({
                    "code": "patch_drift",
                    "message": f'Patch "{patch}" has changed since this preset message was authored.',
                })
            if current_schema is None:
                message_warnings.append({
                    "code": "missing_schema",
                    "message": f'Patch "{patch}" has no current preset schema.',
                })
            elif current_schema != authored_schema:
                message_warnings.append({
                    "code": "schema_drift",
                    "message": f'Patch "{patch}" parameter schema has changed since this preset message was authored.',
                })
            warnings.extend({
                **warning,
                "step_uid": item.get("uid"),
                "message_uid": message.get("uid"),
            } for warning in message_warnings)
    return warnings


def clean_then_action(value):
    if not isinstance(value, dict) or value.get("type") not in THEN_ACTION_TYPES:
        return None
    if value["type"] == "goto":
        target_uid = clean_uid(value.get("target_uid"))
        if target_uid is None:
            return None
        return {"type": "goto", "target_uid": target_uid}
    return {"type": value["type"]}


def clean_step(value):
    if not isinstance(value, dict) or value.get("kind") != "step":
        return None
    uid = clean_uid(value.get("uid"))
    if uid is None:
        return None
    alias = value.get("alias")
    if alias is not None and not isinstance(alias, str):
        return None
    raw_messages = value.get("messages", [])
    if not isinstance(raw_messages, list):
        return None
    messages = []
    for raw_message in raw_messages:
        message = clean_message(raw_message)
        if message is None:
            return None
        messages.append(message)
    duration_s = value.get("duration_s")
    if isinstance(duration_s, bool) or not isinstance(duration_s, (int, float)):
        return None
    duration_s = float(duration_s)
    if not math.isfinite(duration_s) or duration_s < 0:
        return None
    play_count = value.get("play_count")
    if play_count is not None and (isinstance(play_count, bool)
                                   or not isinstance(play_count, int) or play_count < 1):
        return None
    # Guard (design note sec 4): duration_s == 0 is only valid with a finite
    # play_count -- an infinite loop needs positive duration or it busy-loops.
    if duration_s == 0 and play_count is None:
        return None
    raw_then = value.get("then_actions", [])
    if not isinstance(raw_then, list):
        return None
    then_actions = []
    for raw_action in raw_then:
        action = clean_then_action(raw_action)
        if action is None:
            return None
        then_actions.append(action)
    if not then_actions:
        then_actions = [{"type": "stop"}]
    return {"kind": "step", "uid": uid, "alias": alias, "messages": messages,
            "duration_s": duration_s, "play_count": play_count,
            "then_actions": then_actions}


def clean_divider(value):
    if not isinstance(value, dict) or value.get("kind") != "divider":
        return None
    uid = clean_uid(value.get("uid"))
    if uid is None:
        return None
    # `alias` is additive (stitch 04, named section dividers): older documents
    # without the field load with alias None.
    alias = value.get("alias")
    if alias is not None and not isinstance(alias, str):
        return None
    return {"kind": "divider", "uid": uid, "alias": alias}


def clean_item(value):
    if not isinstance(value, dict):
        return None
    if value.get("kind") == "step":
        return clean_step(value)
    if value.get("kind") == "divider":
        return clean_divider(value)
    return None


def clean_show(value, fallback_name=""):
    """Validate a loaded/incoming show document, or return None.

    Enforces schema, per-namespace uid uniqueness (items and messages are
    separate namespaces per the design note), and every item/message rule
    above. Callers that want a tolerant load (missing/corrupt file -> empty
    show) should fall back to `empty_show()` themselves; this function never
    does that silently so a bad WS payload can still be rejected.
    """
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        return None
    raw_items = value.get("items")
    if not isinstance(raw_items, list):
        return None
    items, seen_item_uids, seen_message_uids = [], set(), set()
    for raw_item in raw_items:
        item = clean_item(raw_item)
        if item is None or item["uid"] in seen_item_uids:
            return None
        seen_item_uids.add(item["uid"])
        if item["kind"] == "step":
            for message in item["messages"]:
                if message["uid"] in seen_message_uids:
                    return None
                seen_message_uids.add(message["uid"])
        items.append(item)
    name = value.get("name", fallback_name)
    if not isinstance(name, str):
        return None
    return {"schema": SCHEMA, "name": name, "items": items}


# --------------------------------------------------------------------------
# Section derivation (pure, unit-testable)
# --------------------------------------------------------------------------

def sections(show):
    """Maximal runs of consecutive step items, split on divider items.

    A divider is never part of a section. Leading/trailing/adjacent dividers
    produce zero-length gaps that are simply not emitted (design note sec 4).
    """
    result, current = [], []
    for item in show["items"]:
        if item["kind"] == "divider":
            if current:
                result.append(current)
            current = []
        else:
            current.append(item)
    if current:
        result.append(current)
    return result


def section_for(show, step_uid):
    """Return the section (list of step items) containing `step_uid`, or None."""
    for section in sections(show):
        if any(item["uid"] == step_uid for item in section):
            return section
    return None


# --------------------------------------------------------------------------
# Uid minting
# --------------------------------------------------------------------------

def _item_uids(show):
    return {item["uid"] for item in show["items"]}


def _message_uids(show):
    uids = set()
    for item in show["items"]:
        if item["kind"] == "step":
            uids.update(message["uid"] for message in item["messages"])
    return uids


def mint_uid(existing):
    """secrets.token_hex(4), retried on collision within `existing`."""
    while True:
        uid = secrets.token_hex(4)
        if uid not in existing:
            return uid


# --------------------------------------------------------------------------
# Item positioning
# --------------------------------------------------------------------------

def _index_after(entries, after_uid):
    """Insertion index for a list of uid-bearing dicts.

    `after_uid=None` inserts at the front (position 0); otherwise the index
    right after the entry whose uid matches. Returns None if `after_uid` is
    given but no entry has that uid, so callers can reject a stale reference
    instead of silently appending.
    """
    if after_uid is None:
        return 0
    for index, entry in enumerate(entries):
        if entry["uid"] == after_uid:
            return index + 1
    return None


# --------------------------------------------------------------------------
# Edit operations
#
# Every mutation returns (new_show, result, error): on success `error` is
# None and `new_show` is a fresh document (the input is never mutated in
# place); on failure `new_show is show` (unchanged) and `result` is None.
# Callers (the WS layer) are responsible for persisting `new_show` on
# success -- these functions are pure and touch no filesystem.
# --------------------------------------------------------------------------

def add_step(show, after_uid=None):
    index = _index_after(show["items"], after_uid)
    if index is None:
        return show, None, "after_uid not found."
    step = {"kind": "step", "uid": mint_uid(_item_uids(show)), "alias": None,
            "messages": [], "duration_s": 5.0, "play_count": 1,
            "then_actions": [{"type": "stop"}]}
    items = list(show["items"])
    items.insert(index, step)
    return {**show, "items": items}, step, None


def add_divider(show, after_uid=None):
    index = _index_after(show["items"], after_uid)
    if index is None:
        return show, None, "after_uid not found."
    divider = {"kind": "divider", "uid": mint_uid(_item_uids(show)), "alias": None}
    items = list(show["items"])
    items.insert(index, divider)
    return {**show, "items": items}, divider, None


def update_step(show, uid, patch):
    """Partial patch over alias/duration_s/play_count/then_actions.

    `messages` is not patchable here -- it is owned by add_message/
    update_message/move_message/remove_message.
    """
    if not isinstance(patch, dict):
        return show, None, "patch must be an object."
    items = list(show["items"])
    index = next((i for i, item in enumerate(items)
                  if item["uid"] == uid and item["kind"] == "step"), None)
    if index is None:
        return show, None, "Step not found."
    candidate = dict(items[index])
    if "alias" in patch:
        alias = patch["alias"]
        if alias is not None and not isinstance(alias, str):
            return show, None, "alias must be text or null."
        candidate["alias"] = alias
    if "duration_s" in patch:
        duration_s = patch["duration_s"]
        if (isinstance(duration_s, bool) or not isinstance(duration_s, (int, float))
                or not math.isfinite(duration_s) or duration_s < 0):
            return show, None, "duration_s must be a number >= 0."
        candidate["duration_s"] = float(duration_s)
    if "play_count" in patch:
        play_count = patch["play_count"]
        if play_count is not None and (isinstance(play_count, bool)
                                       or not isinstance(play_count, int) or play_count < 1):
            return show, None, "play_count must be a positive integer or null."
        candidate["play_count"] = play_count
    if "then_actions" in patch:
        raw_then = patch["then_actions"]
        if not isinstance(raw_then, list):
            return show, None, "then_actions must be a list."
        then_actions = []
        for raw_action in raw_then:
            action = clean_then_action(raw_action)
            if action is None:
                return show, None, "invalid then_action."
            then_actions.append(action)
        candidate["then_actions"] = then_actions or [{"type": "stop"}]
    if candidate["duration_s"] == 0 and candidate["play_count"] is None:
        return show, None, "duration_s == 0 requires a finite play_count."
    items[index] = candidate
    return {**show, "items": items}, candidate, None


def update_divider(show, uid, patch):
    """Partial patch over a divider's `alias` (stitch 04).

    Mirrors `update_step`'s alias branch exactly -- same partial-patch shape,
    same `(new_show, result, error)` contract -- so it rides the existing
    apply_show_mutation plumbing (undo, persistence, broadcast) unchanged.
    """
    if not isinstance(patch, dict):
        return show, None, "patch must be an object."
    items = list(show["items"])
    index = next((i for i, item in enumerate(items)
                  if item["uid"] == uid and item["kind"] == "divider"), None)
    if index is None:
        return show, None, "Divider not found."
    candidate = dict(items[index])
    if "alias" in patch:
        alias = patch["alias"]
        if alias is not None and not isinstance(alias, str):
            return show, None, "alias must be text or null."
        candidate["alias"] = alias
    items[index] = candidate
    return {**show, "items": items}, candidate, None


def move_item(show, uid, after_uid):
    if uid == after_uid:
        return show, None, "Cannot move an item after itself."
    items = list(show["items"])
    position = next((i for i, item in enumerate(items) if item["uid"] == uid), None)
    if position is None:
        return show, None, "Item not found."
    item = items.pop(position)
    index = _index_after(items, after_uid)
    if index is None:
        return show, None, "after_uid not found."  # `show` is untouched
    items.insert(index, item)
    return {**show, "items": items}, item, None


def remove_item(show, uid):
    items = list(show["items"])
    position = next((i for i, item in enumerate(items) if item["uid"] == uid), None)
    if position is None:
        return show, None, "Item not found."
    removed = items.pop(position)
    # TODO(stitch 3): if `removed` is a step currently playing/paused, the
    # playback engine must stop it before this mutation lands (design note
    # sec 3, remove_item row) -- there is no playback state to stop yet.
    return {**show, "items": items}, removed, None


def duplicate_item(show, uid):
    """Clone a step or divider in place, minting fresh uids throughout.

    02-edit-bar-and-inline-step-name / decisions.md: the edit bar's Duplicate
    action is a real model operation, not a client-side copy -- it mints a
    fresh uid for the item and (for a step) every nested message, and inserts
    the clone immediately after the original. `then_actions` (including
    `goto` targets) are copied verbatim: they reference existing step uids
    that remain valid post-duplication, so nothing is rewritten.
    """
    items = list(show["items"])
    position = next((i for i, item in enumerate(items) if item["uid"] == uid), None)
    if position is None:
        return show, None, "Item not found."
    duplicate = copy.deepcopy(items[position])
    duplicate["uid"] = mint_uid(_item_uids(show))
    if duplicate["kind"] == "step":
        message_uids = _message_uids(show)
        for message in duplicate["messages"]:
            fresh_uid = mint_uid(message_uids)
            message_uids.add(fresh_uid)
            message["uid"] = fresh_uid
    items.insert(position + 1, duplicate)
    return {**show, "items": items}, duplicate, None


def add_message(show, step_uid, message):
    """Mint a fresh uid and append; also used for paste (design note sec 3)."""
    items = list(show["items"])
    index = next((i for i, item in enumerate(items)
                  if item["uid"] == step_uid and item["kind"] == "step"), None)
    if index is None:
        return show, None, "Step not found."
    candidate = dict(message) if isinstance(message, dict) else {}
    candidate["uid"] = mint_uid(_message_uids(show))
    cleaned = clean_message(candidate)
    if cleaned is None:
        return show, None, "Invalid message."
    step = dict(items[index])
    step["messages"] = list(step["messages"]) + [cleaned]
    items[index] = step
    return {**show, "items": items}, cleaned, None


def _find_message(show, uid):
    """Return (step_index, message_index) or (None, None)."""
    for step_index, item in enumerate(show["items"]):
        if item["kind"] != "step":
            continue
        for message_index, message in enumerate(item["messages"]):
            if message["uid"] == uid:
                return step_index, message_index
    return None, None


def update_message(show, uid, patch):
    if not isinstance(patch, dict):
        return show, None, "patch must be an object."
    step_index, message_index = _find_message(show, uid)
    if step_index is None:
        return show, None, "Message not found."
    items = list(show["items"])
    candidate = dict(items[step_index]["messages"][message_index])
    if "alias" in patch:
        alias = patch["alias"]
        if alias is not None and not isinstance(alias, str):
            return show, None, "alias must be text or null."
        candidate["alias"] = alias
    if "address" in patch:
        address = patch["address"]
        if not isinstance(address, str) or not address.startswith("/") or address.strip() != address:
            return show, None, "address must be a non-empty OSC address."
        candidate["address"] = address
    if "args" in patch:
        raw_args = patch["args"]
        if not isinstance(raw_args, list):
            return show, None, "args must be a list."
        args = []
        for raw_arg in raw_args:
            arg = clean_arg(raw_arg)
            if arg is None:
                return show, None, "invalid arg."
            args.append(arg)
        candidate["args"] = args
    if "target" in patch:
        target = clean_target(patch.get("target"))
        if target is None:
            return show, None, "invalid target."
        candidate["target"] = target
    if "kind" in patch or "reference" in patch:
        if "kind" in patch:
            candidate["kind"] = patch["kind"]
        if "reference" in patch:
            if patch["reference"] is None:
                candidate.pop("reference", None)
            else:
                candidate["reference"] = patch["reference"]
        cleaned = clean_message(candidate)
        if cleaned is None:
            return show, None, "invalid message reference."
        candidate = cleaned
    step = dict(items[step_index])
    messages = list(step["messages"])
    messages[message_index] = candidate
    step["messages"] = messages
    items[step_index] = step
    return {**show, "items": items}, candidate, None


def move_message(show, uid, to_step_uid, after_uid=None):
    step_index, message_index = _find_message(show, uid)
    if step_index is None:
        return show, None, "Message not found."
    items = list(show["items"])
    target_index = next((i for i, item in enumerate(items)
                         if item["uid"] == to_step_uid and item["kind"] == "step"), None)
    if target_index is None:
        return show, None, "Target step not found."
    source_step = dict(items[step_index])
    source_messages = list(source_step["messages"])
    message = source_messages.pop(message_index)
    source_step["messages"] = source_messages
    items[step_index] = source_step
    # Re-read the target step -- it may be the same step as the source, in
    # which case the pop above already updated it in `items`.
    target_step = dict(items[target_index])
    target_messages = list(target_step["messages"])
    insert_index = _index_after(target_messages, after_uid)
    if insert_index is None:
        return show, None, "after_uid not found in target step."  # `show` is untouched
    target_messages.insert(insert_index, message)
    target_step["messages"] = target_messages
    items[target_index] = target_step
    return {**show, "items": items}, message, None


def remove_message(show, uid):
    step_index, message_index = _find_message(show, uid)
    if step_index is None:
        return show, None, "Message not found."
    items = list(show["items"])
    step = dict(items[step_index])
    messages = list(step["messages"])
    removed = messages.pop(message_index)
    step["messages"] = messages
    items[step_index] = step
    return {**show, "items": items}, removed, None


def flatten_preset_message(show, uid, messages):
    """Replace one preset reference with literal messages as one mutation."""
    step_index, message_index = _find_message(show, uid)
    if step_index is None:
        return show, None, "Message not found."
    original = show["items"][step_index]["messages"][message_index]
    if preset_message_parts(original) is None:
        return show, None, "Message is not a preset reference."
    if not isinstance(messages, list) or not messages:
        return show, None, "Preset has no applicable parameters to flatten."
    existing = _message_uids(show)
    flattened = []
    for raw in messages:
        candidate = dict(raw) if isinstance(raw, dict) else {}
        candidate["uid"] = mint_uid(existing)
        existing.add(candidate["uid"])
        cleaned = clean_message(candidate)
        if cleaned is None or cleaned["kind"] != "osc":
            return show, None, "Invalid flattened preset message."
        flattened.append(cleaned)
    items = list(show["items"])
    step = dict(items[step_index])
    next_messages = list(step["messages"])
    next_messages[message_index:message_index + 1] = flattened
    step["messages"] = next_messages
    items[step_index] = step
    return {**show, "items": items}, flattened, None


# --------------------------------------------------------------------------
# Persistence -- dashboard/shows/<name>.json, atomic .tmp+os.replace like
# InstallationState.venues_dir()/save_venue()/read_venue().
# --------------------------------------------------------------------------

def shows_dir(state_path):
    directory = os.path.join(os.path.dirname(os.path.abspath(state_path)), "shows")
    os.makedirs(directory, exist_ok=True)
    return directory


def list_shows(directory):
    try:
        return sorted(name[:-5] for name in os.listdir(directory) if name.endswith(".json"))
    except OSError:
        return []


def save_show(directory, doc):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, doc["name"] + ".json")
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as target:
        # sort_keys only orders each object's own keys; `items` stays a JSON
        # array and is never reordered (design note sec 2).
        json.dump(doc, target, indent=2, sort_keys=True)
        target.write("\n")
    os.replace(temporary, path)


def load_show(directory, name):
    """Tolerant load: a missing, empty, or corrupt file yields an empty show."""
    path = os.path.join(directory, name + ".json")
    try:
        with open(path, encoding="utf-8") as source:
            text = source.read()
    except OSError:
        return empty_show(name)
    if not text.strip():
        return empty_show(name)
    try:
        loaded = json.loads(text)
    except ValueError:
        return empty_show(name)
    cleaned = clean_show(loaded, fallback_name=name)
    return cleaned if cleaned is not None else empty_show(name)


def delete_show(directory, name):
    try:
        os.remove(os.path.join(directory, name + ".json"))
        return True
    except OSError:
        return False


def create_show(directory, name):
    """A fresh, empty, saved show. Refuses to clobber an existing file."""
    if name in list_shows(directory):
        return None, "A show with that name already exists."
    doc = empty_show(name)
    save_show(directory, doc)
    return doc, None
