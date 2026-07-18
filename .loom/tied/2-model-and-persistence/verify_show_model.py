#!/usr/bin/env python3
"""Verification for 14-show-tab stitch 2 (show model + persistence).

Two halves:
  A. Headless, in-process checks of dashboard/show_model.py: schema
     round-trip, section derivation edge cases, every mutation op (including
     error paths and add_message uid freshness/collision-retry), and load
     tolerance for a missing/empty/corrupt show file.
  B. A real dashboard/server.py subprocess on non-default ports (no
     simfleet -- show edits emit no OSC in this stitch) exercised over a
     real websocket connection: the show catalog/CRUD WS surface end to end,
     plus a kill-and-restart of the server proving the show and the
     `current_show` pointer both survive.

Run:  ~/.venvs/bopos/bin/python verify_show_model.py
Deps: fastapi, uvicorn[standard], websockets (already in dashboard/requirements.txt).
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest.mock

import websockets

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

sys.path.insert(0, os.path.join(REPO, "dashboard"))
import show_model  # noqa: E402

HTTP_PORT = 18097
REPORT_PORT = 15586
CMD_PORT = 16696

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


# --------------------------------------------------------------------------
# Part A: headless show_model checks
# --------------------------------------------------------------------------

def sample_show():
    show = show_model.empty_show("opening-set")
    show, intro, _ = show_model.add_step(show)
    show, _, _ = show_model.update_step(show, intro["uid"], {
        "alias": "intro drone", "duration_s": 45.0, "play_count": 1,
        "then_actions": [{"type": "next_step"}], "forward_sync": False})
    show, _msg, _ = show_model.add_message(show, intro["uid"], {
        "alias": "gain up", "address": "/p/gain",
        "args": [{"type": "f", "value": 0.6}], "target": "all"})
    show, divider, _ = show_model.add_divider(show, intro["uid"])
    show, sparkle, _ = show_model.add_step(show, divider["uid"])
    show, _, _ = show_model.update_step(show, sparkle["uid"], {
        "alias": "seat 3 sparkle", "duration_s": 20.0, "play_count": None})
    show, _msg, _ = show_model.add_message(show, sparkle["uid"], {
        "address": "/p/fx/sparkle", "args": [{"type": "f", "value": 1.0}],
        "target": "3"})
    show, _msg, _ = show_model.add_message(show, sparkle["uid"], {
        "alias": "reset point", "address": "/pt", "args": [
            {"type": "i", "value": 0}, {"type": "f", "value": 5.0},
            {"type": "f", "value": 4.0}, {"type": "f", "value": 1.5},
            {"type": "i", "value": 0}], "target": "all"})
    return show


def test_schema_round_trip(directory):
    show = sample_show()
    show_model.save_show(directory, show)
    loaded = show_model.load_show(directory, show["name"])
    check("schema round-trip: save -> load equals the built document",
          loaded == show, json.dumps({"built": show, "loaded": loaded}, indent=2))
    check("schema round-trip: item order is preserved (steps/divider/steps)",
          [item["kind"] for item in loaded["items"]] == ["step", "divider", "step"])
    check("schema round-trip: message order within a step is preserved",
          [m["address"] for m in loaded["items"][2]["messages"]]
          == ["/p/fx/sparkle", "/pt"])


def test_section_derivation():
    def kinds(show_items):
        return {"schema": 1, "name": "x", "items": show_items}

    step = lambda uid: {"kind": "step", "uid": uid, "alias": None, "messages": [],
                        "duration_s": 1.0, "play_count": 1, "then_actions": [],
                        "forward_sync": False}
    divider = lambda uid: {"kind": "divider", "uid": uid}

    no_dividers = kinds([step("a1111111"), step("a2222222")])
    check("sections: no dividers -> one section of all steps",
          show_model.sections(no_dividers) == [[step("a1111111"), step("a2222222")]])

    leading = kinds([divider("d0000001"), step("a1111111")])
    check("sections: leading divider -> one section, no leading empty gap",
          show_model.sections(leading) == [[step("a1111111")]])

    trailing = kinds([step("a1111111"), divider("d0000001")])
    check("sections: trailing divider -> one section, no trailing empty gap",
          show_model.sections(trailing) == [[step("a1111111")]])

    adjacent = kinds([step("a1111111"), divider("d0000001"), divider("d0000002"),
                      step("a2222222")])
    check("sections: adjacent dividers -> two sections, empty gap between them skipped",
          show_model.sections(adjacent) == [[step("a1111111")], [step("a2222222")]])

    all_dividers = kinds([divider("d0000001"), divider("d0000002")])
    check("sections: only dividers -> no sections at all",
          show_model.sections(all_dividers) == [])

    empty = kinds([])
    check("sections: empty show -> no sections", show_model.sections(empty) == [])

    two_steps_between = kinds([divider("d0000001"), step("a1111111"), step("a2222222"),
                               divider("d0000002")])
    check("sections: dividers on both ends still yield exactly one middle section",
          show_model.sections(two_steps_between)
          == [[step("a1111111"), step("a2222222")]])


def test_add_and_positioning():
    show = show_model.empty_show("pos")
    show, first, error = show_model.add_step(show)
    check("add_step: succeeds with after_uid=None on an empty show",
          error is None and [i["uid"] for i in show["items"]] == [first["uid"]])

    show, second, error = show_model.add_step(show, None)
    check("add_step: after_uid=None inserts at the front",
          error is None and [i["uid"] for i in show["items"]]
          == [second["uid"], first["uid"]])

    show, third, error = show_model.add_step(show, first["uid"])
    check("add_step: after_uid=<uid> inserts right after that item",
          error is None and [i["uid"] for i in show["items"]]
          == [second["uid"], first["uid"], third["uid"]])

    _unchanged, result, error = show_model.add_step(show, "ffffffff")
    check("add_step: unknown after_uid is rejected, not silently appended",
          result is None and error is not None)

    show, divider, error = show_model.add_divider(show, second["uid"])
    check("add_divider: mints its own uid and inserts positionally",
          error is None and show["items"][1]["kind"] == "divider"
          and show["items"][1]["uid"] == divider["uid"])
    return show, (second, divider, first, third)


def test_move_and_remove():
    show, (second, divider, first, third) = test_add_and_positioning()
    order = lambda s: [i["uid"] for i in s["items"]]

    show, moved, error = show_model.move_item(show, third["uid"], None)
    check("move_item: after_uid=None moves an item to the front",
          error is None and order(show)[0] == third["uid"])

    _unchanged, _result, error = show_model.move_item(show, third["uid"], third["uid"])
    check("move_item: moving an item after itself is rejected",
          error is not None)

    _unchanged, _result, error = show_model.move_item(show, third["uid"], "ffffffff")
    check("move_item: unknown after_uid is rejected and leaves order intact",
          error is not None and order(_unchanged) == order(show))

    before_remove = order(show)
    show, removed, error = show_model.remove_item(show, divider["uid"])
    check("remove_item: removes exactly the targeted item",
          error is None and removed["uid"] == divider["uid"]
          and divider["uid"] not in order(show)
          and len(order(show)) == len(before_remove) - 1)

    _unchanged, _result, error = show_model.remove_item(show, divider["uid"])
    check("remove_item: removing an already-gone uid reports not-found",
          error is not None)


def test_update_step_validation():
    show = show_model.empty_show("guard")
    show, step, _ = show_model.add_step(show)

    show, updated, error = show_model.update_step(show, step["uid"], {
        "duration_s": 0.0, "play_count": 3})
    check("update_step: duration_s == 0 with a finite play_count is valid",
          error is None and updated["duration_s"] == 0.0 and updated["play_count"] == 3)

    _unchanged, _result, error = show_model.update_step(show, step["uid"], {
        "play_count": None})
    check("update_step: duration_s == 0 with play_count -> null is rejected",
          error is not None)

    show, updated, error = show_model.update_step(show, step["uid"], {
        "duration_s": 5.0, "play_count": None})
    check("update_step: positive duration_s with play_count null (loop) is valid",
          error is None and updated["play_count"] is None)

    _unchanged, _result, error = show_model.update_step(show, step["uid"], {
        "play_count": 0})
    check("update_step: play_count 0 is rejected (must be >= 1 or null)",
          error is not None)

    _unchanged, _result, error = show_model.update_step(show, step["uid"], {
        "duration_s": -1.0})
    check("update_step: negative duration_s is rejected", error is not None)

    _unchanged, _result, error = show_model.update_step(show, "ffffffff", {"alias": "x"})
    check("update_step: unknown uid reports not-found", error is not None)

    show, updated, error = show_model.update_step(show, step["uid"], {
        "then_actions": [{"type": "goto", "target_uid": "aaaaaaaa"}]})
    check("update_step: a well-formed goto then_action is accepted",
          error is None and updated["then_actions"]
          == [{"type": "goto", "target_uid": "aaaaaaaa"}])

    _unchanged, _result, error = show_model.update_step(show, step["uid"], {
        "then_actions": [{"type": "goto"}]})
    check("update_step: goto without target_uid is rejected", error is not None)

    _unchanged, _result, error = show_model.update_step(show, step["uid"], {
        "then_actions": [{"type": "not-a-real-action"}]})
    check("update_step: an unknown then_action type is rejected", error is not None)


def test_message_ops():
    show = show_model.empty_show("messages")
    show, step_a, _ = show_model.add_step(show)
    show, step_b, _ = show_model.add_step(show, step_a["uid"])

    show, message, error = show_model.add_message(show, step_a["uid"], {
        "address": "/p/gain", "args": [{"type": "f", "value": 0.5}], "target": "all"})
    check("add_message: succeeds and stamps a fresh uid",
          error is None and show_model.UID_RE.fullmatch(message["uid"]) is not None)

    _unchanged, _result, error = show_model.add_message(show, "ffffffff", {
        "address": "/p/gain", "args": [], "target": "all"})
    check("add_message: unknown step_uid reports not-found", error is not None)

    _unchanged, _result, error = show_model.add_message(show, step_a["uid"], {
        "address": "/p/gain", "args": [{"type": "x", "value": 1}], "target": "all"})
    check("add_message: an invalid arg type is rejected", error is not None)

    _unchanged, _result, error = show_model.add_message(show, step_a["uid"], {
        "address": "p/gain", "args": [], "target": "all"})
    check("add_message: an address missing a leading slash is rejected",
          error is not None)

    _unchanged, _result, error = show_model.add_message(show, step_a["uid"], {
        "address": "/p/gain", "args": [], "target": "g"})
    check("add_message: a malformed target selector is rejected", error is not None)

    show, updated, error = show_model.update_message(show, message["uid"], {
        "target": "3", "alias": "renamed"})
    check("update_message: partial patch updates only the given fields",
          error is None and updated["target"] == "3" and updated["alias"] == "renamed"
          and updated["address"] == "/p/gain")

    show, moved, error = show_model.move_message(
        show, message["uid"], step_b["uid"], None)
    check("move_message: relocates the message into the target step",
          error is None
          and moved["uid"] not in [m["uid"] for m in
                                   next(i for i in show["items"]
                                       if i["uid"] == step_a["uid"])["messages"]]
          and moved["uid"] in [m["uid"] for m in
                               next(i for i in show["items"]
                                   if i["uid"] == step_b["uid"])["messages"]])

    _unchanged, _result, error = show_model.move_message(
        show, message["uid"], "ffffffff", None)
    check("move_message: unknown target step reports not-found", error is not None)

    show, removed, error = show_model.remove_message(show, message["uid"])
    check("remove_message: removes exactly the targeted message",
          error is None and removed["uid"] == message["uid"]
          and all(message["uid"] not in [m["uid"] for m in item.get("messages", [])]
                  for item in show["items"]))

    _unchanged, _result, error = show_model.remove_message(show, message["uid"])
    check("remove_message: removing an already-gone uid reports not-found",
          error is not None)


def test_uid_freshness_and_collision_retry():
    show = show_model.empty_show("uids")
    show, step, _ = show_model.add_step(show)
    uids = set()
    for index in range(20):
        show, message, error = show_model.add_message(show, step["uid"], {
            "address": "/p/x", "args": [{"type": "i", "value": index}], "target": "all"})
        check(f"add_message #{index}: fresh uid", error is None and message["uid"] not in uids)
        uids.add(message["uid"])
    check("add_message: 20 messages minted 20 distinct uids", len(uids) == 20)

    # Force a collision on the first mint attempt and prove the retry loop
    # produces a second, different, still-unique uid rather than reusing one.
    scripted = iter([bytes.fromhex(next(iter(uids))), bytes.fromhex("deadbeef")])
    with unittest.mock.patch("show_model.secrets.token_bytes",
                             side_effect=lambda n: next(scripted)):
        show, message, error = show_model.add_message(show, step["uid"], {
            "address": "/p/y", "args": [], "target": "all"})
    check("add_message: collision on the first mint attempt retries to a fresh uid",
          error is None and message["uid"] == "deadbeef" and message["uid"] not in uids)


def test_load_tolerance(directory):
    check("load_show: missing file -> empty show",
          show_model.load_show(directory, "nope") == show_model.empty_show("nope"))

    empty_path = os.path.join(directory, "blank.json")
    with open(empty_path, "w", encoding="utf-8"):
        pass
    check("load_show: empty file -> empty show",
          show_model.load_show(directory, "blank") == show_model.empty_show("blank"))

    corrupt_path = os.path.join(directory, "corrupt.json")
    with open(corrupt_path, "w", encoding="utf-8") as target:
        target.write("{not json")
    check("load_show: corrupt JSON -> empty show",
          show_model.load_show(directory, "corrupt") == show_model.empty_show("corrupt"))

    wrong_schema_path = os.path.join(directory, "wrongschema.json")
    with open(wrong_schema_path, "w", encoding="utf-8") as target:
        json.dump({"schema": 99, "name": "wrongschema", "items": []}, target)
    check("load_show: wrong schema version -> empty show",
          show_model.load_show(directory, "wrongschema")
          == show_model.empty_show("wrongschema"))

    duplicate_uid_path = os.path.join(directory, "dupuid.json")
    with open(duplicate_uid_path, "w", encoding="utf-8") as target:
        json.dump({"schema": 1, "name": "dupuid", "items": [
            {"kind": "divider", "uid": "aaaaaaaa"},
            {"kind": "divider", "uid": "aaaaaaaa"}]}, target)
    check("load_show: duplicate item uids -> empty show (fails clean_show)",
          show_model.load_show(directory, "dupuid") == show_model.empty_show("dupuid"))


def test_create_show(directory):
    doc, error = show_model.create_show(directory, "fresh")
    check("create_show: makes an empty, saved document",
          error is None and doc == show_model.empty_show("fresh")
          and show_model.load_show(directory, "fresh") == doc)

    _doc, error = show_model.create_show(directory, "fresh")
    check("create_show: refuses to clobber an existing show", error is not None)


def run_part_a():
    print("-- Part A: headless show_model checks --")
    with tempfile.TemporaryDirectory(prefix="bopos-show-model-") as directory:
        test_schema_round_trip(directory)
        test_load_tolerance(directory)
        test_create_show(directory)
    test_section_derivation()
    test_add_and_positioning()
    test_move_and_remove()
    test_update_step_validation()
    test_message_ops()
    test_uid_freshness_and_collision_retry()


# --------------------------------------------------------------------------
# Part B: real dashboard/server.py + a real websocket connection
# --------------------------------------------------------------------------

def start_server(state_file, assets_dir, patches_dir, log):
    return subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard", "server.py"),
        "--port", str(HTTP_PORT), "--listen-port", str(REPORT_PORT),
        "--send-port", str(CMD_PORT), "--osc-target", "127.0.0.1",
        "--state-file", state_file, "--assets-dir", assets_dir,
        "--patches-dir", patches_dir,
    ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)


def read_log(log):
    log.flush()
    with open(log.name) as source:
        return source.read()


async def wait_http(url, attempts=40):
    import urllib.request
    for _ in range(attempts):
        try:
            urllib.request.urlopen(url, timeout=0.5).close()
            return True
        except Exception:
            await asyncio.sleep(0.25)
    return False


async def drain_connect_messages(ws, wanted, timeout=5.0):
    """Collect the on-connect broadcast burst until every wanted type is seen."""
    collected = {}
    deadline = asyncio.get_event_loop().time() + timeout
    while set(collected) < set(wanted):
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        collected[message["type"]] = message["data"]
    return collected


async def send_and_wait(ws, kind, data, wanted_types, timeout=5.0):
    await ws.send(json.dumps({"type": kind, "data": data}))
    collected = {}
    deadline = asyncio.get_event_loop().time() + timeout
    while set(collected) < set(wanted_types):
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        collected.setdefault(message["type"], []).append(message["data"])
    return collected


async def run_part_b():
    print("-- Part B: real server + websocket CRUD round-trip --")
    with tempfile.TemporaryDirectory(prefix="bopos-show-server-") as root:
        state_file = os.path.join(root, "installation.json")
        assets_dir = os.path.join(root, "assets")
        patches_dir = os.path.join(root, "patches")
        server_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
        server = start_server(state_file, assets_dir, patches_dir, server_log)
        step_uid = message_uid = None
        try:
            booted = await wait_http(f"http://127.0.0.1:{HTTP_PORT}/", attempts=60)
            check("server booted and answers HTTP", booted)
            if not booted:
                print(read_log(server_log)[-2000:])
                return

            async with websockets.connect(f"ws://127.0.0.1:{HTTP_PORT}/ws") as ws:
                connect = await drain_connect_messages(
                    ws, {"state", "distribution", "venues", "shows", "show"})
                check("connect burst includes shows catalog and full-state show",
                      "shows" in connect and "show" in connect, repr(connect.keys()))
                check("fresh installation has no shows and no current show",
                      connect["shows"] == {"names": [], "current": None})
                check("fresh installation's show is the empty placeholder",
                      connect["show"] == show_model.empty_show(""))

                result = await send_and_wait(
                    ws, "add_step", {"after_uid": None}, {"error"})
                check("editing before any show is loaded is refused",
                      "error" in result, repr(result))

                result = await send_and_wait(
                    ws, "create_show", {"name": "verify show"}, {"shows", "show"})
                check("create_show sanitizes the name and broadcasts shows + show",
                      result.get("shows") == [{"names": ["verify-show"], "current": "verify-show"}]
                      and result.get("show") == [show_model.empty_show("verify-show")],
                      repr(result))

                result = await send_and_wait(ws, "create_show", {"name": "verify-show"}, {"error"})
                check("create_show refuses to clobber an existing show over the wire",
                      "error" in result, repr(result))

                result = await send_and_wait(ws, "add_step", {"after_uid": None}, {"show"})
                show_doc = result["show"][-1]
                check("add_step over the wire persists and broadcasts the new step",
                      len(show_doc["items"]) == 1 and show_doc["items"][0]["kind"] == "step")
                step_uid = show_doc["items"][0]["uid"]

                result = await send_and_wait(ws, "update_step", {
                    "uid": step_uid, "alias": "intro", "duration_s": 8.0,
                    "play_count": 2, "then_actions": [{"type": "next_step"}],
                }, {"show"})
                show_doc = result["show"][-1]
                check("update_step over the wire applies a partial patch",
                      show_doc["items"][0]["alias"] == "intro"
                      and show_doc["items"][0]["duration_s"] == 8.0
                      and show_doc["items"][0]["play_count"] == 2, repr(show_doc))

                result = await send_and_wait(ws, "add_divider", {"after_uid": step_uid}, {"show"})
                show_doc = result["show"][-1]
                divider_uid = show_doc["items"][1]["uid"]
                check("add_divider over the wire inserts positionally",
                      show_doc["items"][1]["kind"] == "divider")

                result = await send_and_wait(ws, "add_message", {
                    "step_uid": step_uid,
                    "message": {"address": "/p/gain",
                               "args": [{"type": "f", "value": 0.6}], "target": "all"},
                }, {"show"})
                show_doc = result["show"][-1]
                message_uid = show_doc["items"][0]["messages"][0]["uid"]
                check("add_message over the wire mints a fresh uid and persists it",
                      show_model.UID_RE.fullmatch(message_uid) is not None)

                result = await send_and_wait(ws, "update_message", {
                    "uid": message_uid, "target": "3", "alias": "gain up",
                }, {"show"})
                show_doc = result["show"][-1]
                check("update_message over the wire applies its patch",
                      show_doc["items"][0]["messages"][0]["target"] == "3"
                      and show_doc["items"][0]["messages"][0]["alias"] == "gain up")

                result = await send_and_wait(
                    ws, "move_item", {"uid": divider_uid, "after_uid": None}, {"show"})
                show_doc = result["show"][-1]
                check("move_item over the wire moved the divider to the front",
                      show_doc["items"][0]["uid"] == divider_uid)

                result = await send_and_wait(
                    ws, "remove_item", {"uid": divider_uid}, {"show"})
                show_doc = result["show"][-1]
                check("remove_item over the wire removed the divider",
                      all(item["uid"] != divider_uid for item in show_doc["items"]))

                result = await send_and_wait(
                    ws, "save_show_as", {"name": "verify-show-copy"}, {"shows", "show"})
                check("save_show_as duplicates the current show under a new name and adopts it",
                      sorted(result["shows"][-1]["names"])
                      == ["verify-show", "verify-show-copy"]
                      and result["shows"][-1]["current"] == "verify-show-copy",
                      repr(result["shows"]))

                result = await send_and_wait(
                    ws, "load_show", {"name": "verify-show"}, {"shows", "show"})
                check("load_show switches the current show back",
                      result["shows"][-1]["current"] == "verify-show"
                      and result["show"][-1]["name"] == "verify-show")

                result = await send_and_wait(
                    ws, "delete_show", {"name": "verify-show-copy"}, {"shows"})
                check("delete_show removes a non-current show without touching the loaded one",
                      result["shows"][-1] == {"names": ["verify-show"], "current": "verify-show"})

                final_show = await send_and_wait(ws, "list_shows", {}, {"shows"})
                final_state = final_show["shows"][-1]
                check("final catalog before restart has exactly one show, current",
                      final_state == {"names": ["verify-show"], "current": "verify-show"})

        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()

        log_text = read_log(server_log)
        check("server logged no traceback during Part B editing",
              "Traceback" not in log_text, log_text[-800:])

        # -- restart persistence: kill, restart, reconnect, expect the same
        # current show name and its last-saved document -------------------
        server_log2 = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
        server2 = start_server(state_file, assets_dir, patches_dir, server_log2)
        try:
            booted = await wait_http(f"http://127.0.0.1:{HTTP_PORT}/", attempts=60)
            check("server restarted and answers HTTP again", booted)
            async with websockets.connect(f"ws://127.0.0.1:{HTTP_PORT}/ws") as ws:
                connect = await drain_connect_messages(
                    ws, {"state", "distribution", "venues", "shows", "show"})
                check("restart: current_show pointer survived in installation.json",
                      connect["shows"] == {"names": ["verify-show"], "current": "verify-show"},
                      repr(connect["shows"]))
                restored = connect["show"]
                check("restart: the show document itself survived on disk",
                      restored["name"] == "verify-show"
                      and step_uid in [item["uid"] for item in restored["items"]]
                      and restored["items"][0]["alias"] == "intro"
                      and restored["items"][0]["messages"][0]["uid"] == message_uid
                      and restored["items"][0]["messages"][0]["target"] == "3",
                      json.dumps(restored, indent=2))
        finally:
            if server2.poll() is None:
                server2.terminate()
                try:
                    server2.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server2.kill()

        log_text2 = read_log(server_log2)
        check("server logged no traceback on restart",
              "Traceback" not in log_text2, log_text2[-800:])

        for log in (server_log, server_log2):
            try:
                os.unlink(log.name)
            except OSError:
                pass


def main():
    run_part_a()
    asyncio.run(run_part_b())
    print(f"\n{len(FAILURES)} failure(s)")
    if FAILURES:
        print("FAILED:", "; ".join(FAILURES))
        return 1
    print("show-model verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
