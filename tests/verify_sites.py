#!/usr/bin/env python3
"""Switch real dashboard sites, retain edits, and replay physical assignments."""
import json
import socket
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright
from verify_log_destination import (
    ROOT, UID, PhysicalPeer, free_port, physical_host, stop, wait_http, write_fixture,
)
from project_fixture import data_root


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-sites-") as root:
        patches, assets, project, manifest = write_fixture(root)
        host_root = data_root(project)
        sites = project.parent / "sites"
        other = {"room": {"width": 30, "depth": 20, "origin": [2, 3], "units": "m"},
                 "listener": {"x": 10, "y": 9, "heading": 90, "range": 4},
                 "positions": {"0": [[7, 8], [9, 10]]}}
        (sites / "Broadwalk.json").write_text(json.dumps(other))
        host = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM, host)
        url = f"http://127.0.0.1:{http_port}"
        dashboard = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard/server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(report_port), "--send-port", str(command_port),
            "--osc-target", host, "--data-dir", host_root,
            "--patches-dir", str(patches), "--assets-dir", str(assets),
            "--public-url", url, "--sim-no-engine", "--sim-audio-backend", "none",
        ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        peer = PhysicalPeer(host, command_port, report_port, manifest)
        try:
            peer.start()
            wait_http(url, dashboard)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url)
                page.wait_for_function("uid => installation.devices?.[uid]?.online", arg=UID)
                page.click("#tab-button-seats")
                assert page.locator("#site-select").input_value() == "default"
                assert page.locator("#venue-bar, #venue-save, #venue-load").count() == 0
                before = page.evaluate("JSON.stringify(installation.seats['0'])")
                peer.clear()
                page.locator("#site-select").select_option("Broadwalk")
                page.wait_for_function("installation.current_site === 'Broadwalk'")
                assert page.locator("#project-bar-site").inner_text() == "Broadwalk"
                assert page.evaluate("installation.room.width") == 30
                assert page.evaluate("installation.listener.heading") == 90
                assert page.evaluate("installation.seats['0'].positions") == [[7, 8], [9, 10]]
                assignment = ("/all/os/assign", [UID, 0, "Seat 0", 7., 8., 9., 10.])
                peer.wait_frame(lambda f: f == assignment)
                frames = peer.wait_frame(lambda f: f[0] == "/all/os/groups")
                assert assignment in frames, frames
                assert any(address.endswith("/os/groups") for address, args in frames), frames
                exported = page.request.get(url + "/bopos.devices")
                assert exported.ok and "7 8, 9 10" in exported.text(), exported.text()
                page.evaluate("ws.send('update_seat', {id:0, positions:[[11,12]]})")
                page.wait_for_function("installation.seats['0'].positions[0][0] === 11")
                # Switch immediately: selection must flush the pending edit.
                page.locator("#site-select").select_option("default")
                page.wait_for_function("installation.current_site === 'default'")
                assert page.evaluate("JSON.stringify(installation.seats['0'])") == before
                assert json.loads((sites / "Broadwalk.json").read_text())["positions"]["0"] == [[11, 12]]
                page.locator("#site-select").select_option("Broadwalk")
                page.wait_for_function("installation.current_site === 'Broadwalk'")
                page.reload()
                page.wait_for_function("installation.current_site === 'Broadwalk'")
                assert page.evaluate("installation.seats['0'].positions") == [[11, 12]]
                stored = json.loads(project.read_text())
                assert stored["current_site"] == "Broadwalk"
                assert "positions" not in stored["seats"]["0"]
                assert not {"room", "listener", "name"} & set(stored)
                page.goto(url + "/facilitator")
                page.wait_for_function("document.querySelector('#venue-name').textContent === 'Broadwalk'")
                assert not errors, errors
                browser.close()
        finally:
            peer.close()
            stop(dashboard)
    print("PASS: site selection, geometry isolation, edit flush, reload, assignment/group replay; no browser errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
