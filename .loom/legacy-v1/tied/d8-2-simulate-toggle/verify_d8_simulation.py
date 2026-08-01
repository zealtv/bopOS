#!/usr/bin/env python3
"""Focused managed-audition simulation lifecycle verification."""
import asyncio, json, os, sys, tempfile, time
from types import SimpleNamespace
sys.dont_write_bytecode = True
HERE=os.path.realpath(os.path.dirname(__file__)); REPO=HERE
while not os.path.isfile(os.path.join(REPO,"tools","audition.py")): REPO=os.path.dirname(REPO)
sys.path.insert(0,os.path.join(REPO,"dashboard"))
from server import Dashboard
from state import InstallationState

FAIL=[]
def check(label, ok):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if not ok: FAIL.append(label)

async def main():
  with tempfile.TemporaryDirectory() as temp:
    args=SimpleNamespace(state_file=os.path.join(temp,"installation.json"),devices_file=None,
      listen_port=15592,send_port=16692,osc_target="255.255.255.255",
      assets_dir=os.path.join(temp,"a"),patches_dir=os.path.join(temp,"p"),
      port=18192,public_url=None,sim_audio_backend="none",sim_no_engine=True)
    dash=Dashboard(args); await dash.start()
    try:
      for i in range(2):
        await dash.handle_ws({"type":"add_seat","data":{"id":i,"name":f"seat-{i}",
          "positions":[[i+1,1]],"patch":"demo-pd","params":{}}})
      await dash.handle_ws({"type":"set_simulation","data":{"active":True}})
      deadline=time.monotonic()+5
      while time.monotonic()<deadline and len([d for d in dash.state.devices.values() if d.get("virtual")])<2:
        await asyncio.sleep(.1)
      virtual=[d for d in dash.state.devices.values() if d.get("virtual")]
      check("toggle starts one managed audition node per seat", dash.sim_process is not None
            and dash.sim_process.poll() is None and len(virtual)==2)
      check("virtual rows map ordinary uids onto every seat",
            {dash.state.seat_for_uid(d["uid"])["id"] for d in virtual}=={0,1})
      check("simulation changes fleet send target to loopback", dash.osc.destination[0]=="127.0.0.1")
      source=open(os.path.join(REPO,"dashboard/static/js/spatial.js"),encoding="utf-8").read()
      check("listener puck is simulation-gated", "listener && installation.simulation?.active" in source)
      ui=open(os.path.join(REPO,"dashboard/static/js/dashboard.js"),encoding="utf-8").read()
      html=open(os.path.join(REPO,"dashboard/static/index.html"),encoding="utf-8").read()
      check("sidebar exposes managed Simulate mode", "simulate-toggle" in html
            and 'ws.send("set_simulation"' in ui)
      check("seat occupancy distinguishes live, sim and empty",
            "d?.virtual?'sim':(d?.online?'live':'empty')" in ui)
      process=dash.sim_process
      await dash.handle_ws({"type":"set_simulation","data":{"active":False}})
      check("toggle off reaps child and virtual rows", process.poll() is not None
            and not any(d.get("virtual") for d in dash.state.devices.values()))
      check("performance target restores on exit", dash.osc.destination[0]=="255.255.255.255")
    finally: await dash.stop()
    reloaded=InstallationState(args.state_file)
    check("restart never reloads virtual rows", not reloaded.devices
          and not reloaded.data["simulation"]["active"])
  print(f"\n{9-len(FAIL)}/9 passed"); return 1 if FAIL else 0
if __name__=="__main__": raise SystemExit(asyncio.run(main()))
