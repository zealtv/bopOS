#!/usr/bin/env python3
"""Focused backend checks for PE-3 manifest authoring and New patch."""

import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))
sys.path.insert(0, REPO)

from dashboard.server import Dashboard  # noqa: E402
from python import manifest  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class FakeWS:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)

    def last(self, kind):
        return next((item for item in reversed(self.messages)
                     if item.get("type") == kind), None)


def args(root):
    return SimpleNamespace(
        state_file=os.path.join(root, "installation.json"), devices_file=None,
        listen_port=0, send_port=0, osc_target="127.0.0.1",
        assets_dir=os.path.join(root, "assets"),
        patches_dir=os.path.join(root, "patches"), public_url=None,
        sim_audio_backend="none", sim_no_engine=True,
        sim_engine_port_base=26661,
    )


def seed_patch(root):
    patch = os.path.join(root, "patches", "alpha")
    os.makedirs(patch)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"test entrypoint")
    value = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [{"name": "gain", "type": "f", "min": 0,
                    "max": 1, "default": 0.25, "dashboard": True}],
        "cues": [{"id": "snap", "label": "Snap"}],
        "caps": ["audio"], "slots": ["samples"],
    }
    saved, error = manifest.write_atomic(patch, value)
    if saved is None:
        raise RuntimeError(error)
    return patch


async def main_async():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "assets"))
        patch = seed_patch(root)
        dashboard = Dashboard(args(root))
        dashboard.set_supervisor_mode("edit")
        dashboard.state.data["editor"].update(
            active=True, patch="alpha", generation=7,
            declarations=[{"name": "gain", "type": "f"}],
            params={"gain": 0.7})

        ws = FakeWS()
        replacement = [{"name": "tone", "type": "i", "min": 1,
                        "max": 8, "default": 3, "dashboard": False}]
        await dashboard.handle_ws({"type": "save_patch_manifest", "data": {
            "patch": "alpha", "params": replacement,
            "cues": [{"id": "go", "label": "Go", "description": "Begin"}],
        }}, ws)
        loaded, error = manifest.load(patch)
        response = ws.last("manifest_saved")
        check("save preserves read-only manifest fields",
              error is None and loaded["engine"] == "test"
              and loaded["entrypoint"] == "main.bin"
              and loaded["caps"] == ["audio"] and loaded["slots"] == ["samples"],
              str(error))
        check("save returns PD receive follow-up metadata",
              response is not None
              and response["data"]["removed_params"] == ["gain"]
              and response["data"]["rename_candidates"]
              == [{"from": "gain", "to": "tone"}]
              and "gain" in response["data"]["pd_receive_warning"])
        check("active declarations refresh without restart",
              dashboard.state.data["editor"]["declarations"] == replacement
              and dashboard.state.data["editor"]["generation"] == 7
              and dashboard.state.data["editor"]["params"] == {"tone": 3})

        before = open(os.path.join(patch, manifest.MANIFEST_NAME),
                      "rb").read()
        invalid_ws = FakeWS()
        await dashboard.handle_ws({"type": "save_patch_manifest", "data": {
            "patch": "alpha",
            "params": [{"name": "gain\n", "type": "f", "default": 0}],
            "cues": [],
        }}, invalid_ws)
        after = open(os.path.join(patch, manifest.MANIFEST_NAME), "rb").read()
        check("trailing-newline param name is rejected with manifest untouched",
              invalid_ws.last("error") is not None and before == after)
        check("atomic writer leaves no temporary parts",
              not any(name.endswith(".part") for name in os.listdir(patch)))

        cue_before = open(os.path.join(patch, manifest.MANIFEST_NAME), "rb").read()
        invalid_cue_ws = FakeWS()
        await dashboard.handle_ws({"type": "save_patch_manifest", "data": {
            "patch": "alpha", "params": replacement,
            "cues": [{"id": "", "label": "Cannot fire"}],
        }}, invalid_cue_ws)
        cue_after = open(os.path.join(patch, manifest.MANIFEST_NAME), "rb").read()
        check("unfireable cue id is rejected with manifest untouched",
              invalid_cue_ws.last("error") is not None and cue_before == cue_after)

        outside = os.path.join(root, "outside.bin")
        with open(outside, "wb") as target:
            target.write(b"outside")
        link = os.path.join(patch, "linked.bin")
        os.symlink(outside, link)
        escaped = dict(loaded, entrypoint="linked.bin")
        checked, symlink_error = manifest.validate(escaped, patch)
        check("entrypoint symlink cannot escape patch directory",
              checked is None and "resolve inside" in symlink_error,
              str(symlink_error))

        template_dir = os.path.join(root, "patches", ".templates")
        os.makedirs(template_dir)
        source_template = os.path.join(REPO, "patches", ".templates",
                                       "bopos-template.pd")
        shutil.copyfile(source_template,
                        os.path.join(template_dir, "bopos-template.pd"))
        create_ws = FakeWS()
        await dashboard.handle_ws({"type": "create_patch",
                                   "data": {"name": "new-piece"}}, create_ws)
        new_patch = os.path.join(root, "patches", "new-piece")
        copied = os.path.join(new_patch, "main.pd")
        source_digest = hashlib.sha256(open(source_template, "rb").read()).hexdigest()
        copied_digest = hashlib.sha256(open(copied, "rb").read()).hexdigest()
        created, create_error = manifest.load(new_patch)
        check("New patch copies Bob's template byte-for-byte",
              bool(source_digest) and source_digest == copied_digest)
        check("New patch with template is catalog-valid",
              created is not None and create_error is None
              and create_ws.last("patch_created")["data"]["template_copied"] is True,
              str(create_error))
        catalog = await dashboard.catalog()
        catalog_new = next(item for item in catalog["patches"]
                           if item["name"] == "new-piece")
        check("catalog exposes manifest object but hides template directory",
              catalog_new["manifest"]["entrypoint"] == "main.pd"
              and not any(item["name"] == ".templates"
                          for item in catalog["patches"]))

        os.unlink(os.path.join(template_dir, "bopos-template.pd"))
        missing_ws = FakeWS()
        await dashboard.handle_ws({"type": "create_patch",
                                   "data": {"name": "manifest-only"}}, missing_ws)
        missing = os.path.join(root, "patches", "manifest-only")
        with open(os.path.join(missing, manifest.MANIFEST_NAME), encoding="utf-8") as source:
            missing_manifest = json.load(source)
        check("New patch without template writes manifest-only status",
              missing_manifest["entrypoint"] == "main.pd"
              and not os.path.exists(os.path.join(missing, "main.pd"))
              and missing_ws.last("patch_created")["data"]["template_copied"] is False
              and "add main.pd" in missing_ws.last("patch_created")["data"]["status"])

        duplicate_ws = FakeWS()
        await dashboard.handle_ws({"type": "create_patch",
                                   "data": {"name": "new-piece"}}, duplicate_ws)
        check("New patch refuses overwrite",
              duplicate_ws.last("error") is not None)
        dashboard.osc.close()
        await dashboard.state.close()


def main():
    asyncio.run(main_async())
    total = 12
    print("\n{}/{} passed".format(total - len(FAILURES), total))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
