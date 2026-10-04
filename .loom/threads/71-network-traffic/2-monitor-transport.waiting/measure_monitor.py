#!/usr/bin/env python3
"""Actual dashboard OSC + websocket transport against 50 loopback nodes.

No runtime source edits: count at instance-local publication hooks, serve the
production websocket handler, and drain real websocket connections. Fixtures
are temporary beneath this stitch; logs/results remain here. No LAN targets.
"""
import argparse
import asyncio
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p/'tools/simfleet.py').is_file())
sys.path[:0] = [str(ROOT/'dashboard'), str(ROOT)]
from server import Dashboard
import points
from fastapi import FastAPI, WebSocket
import uvicorn
import websockets


def port(kind=socket.SOCK_DGRAM):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def source_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ('dashboard/server.py', 'dashboard/osc_bridge.py', 'dashboard/static/js/monitor.js',
             'dashboard/static/js/ws.js', 'tools/simfleet.py')}


def tap_class(address):
    if address.startswith('/sync/') or re.fullmatch(r'/\d+/sync/offset', address):
        return 'sync'
    if address == '/hb':
        return 'heartbeat'
    if address == '/pt' or address.startswith('/pt/'):
        return 'points'
    return 'ordinary'


async def run(args):
    initial_hashes = source_hashes()
    phase = None
    connections, readers, records = [], [], []
    with tempfile.TemporaryDirectory(prefix='fixture-', dir=HERE) as temp:
        work = Path(temp)
        http_port, report_port, cmd_port = port(socket.SOCK_STREAM), port(), port()
        while report_port == cmd_port:
            cmd_port = port()
        options = SimpleNamespace(data_dir=str(work/'data'), devices_file=None,
            assets_dir=str(work/'assets'), patches_dir=str(work/'patches'),
            listen_port=report_port, send_port=cmd_port, osc_target='127.0.0.1',
            port=http_port, host='127.0.0.1', sim_no_engine=True,
            sim_audio_backend='none', sim_engine_port_base=16661, public_url=None)
        dash = Dashboard(options)
        # The coming stream listener is unrelated to this benchmark; avoid
        # occupying the actual installation's 5551 while measuring its WS path.
        if hasattr(dash.osc, 'stream_port'):
            dash.osc.stream_port = port()
        for i in range(1, 51):
            uid = '02:53:49:4d:%02x:%02x' % ((i >> 8)&255, i&255)
            dash.state.seats[str(i)] = dash.state.clean_seat(
                dict(id=i, name='Measure %s' % i, bound=uid, params={}, groups=[]))
        original_queue, original_broadcast = dash.queue_broadcast, dash.broadcast

        def queued(kind, data=None):
            if phase is not None:
                phase['queued'][kind] += 1
                if kind in ('osc_in', 'osc_out'):
                    phase['tap_classes'][tap_class(data['address'])] += 1
            original_queue(kind, data)

        async def published(kind, data=None):
            if phase is not None:
                phase['publications'][kind] += 1
            await original_broadcast(kind, data)

        dash.osc.broadcast = queued
        dash.broadcast = published
        app = FastAPI()

        @app.websocket('/ws')
        async def endpoint(ws: WebSocket):
            await dash.websocket(ws)

        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=http_port,
            lifespan='off', access_log=False, log_level='warning', ws='websockets',
            ws_per_message_deflate=False))
        http_task = asyncio.create_task(server.serve())
        fleet = None
        log = (HERE/'simfleet-50.log').open('w')
        try:
            while not server.started:
                if http_task.done():
                    await http_task
                    raise RuntimeError('websocket server failed to start')
                await asyncio.sleep(.05)
            random.seed(712)
            await dash.start()
            fleet = subprocess.Popen([sys.executable, str(ROOT/'tools/simfleet.py'),
                '--devices', '50', '--target', '127.0.0.1', '--report-port', str(report_port),
                '--cmd-port', str(cmd_port), '--boot-secs', '0',
                '--hb-interval', str(args.heartbeat), '--patches-dir', str(work/'patches'),
                '--assets-dir', str(work/'assets')], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            await asyncio.sleep(args.warmup)
            assert fleet.poll() is None, 'simfleet failed; inspect simfleet-50.log'
            assert len(dash.state.devices) == 50, len(dash.state.devices)
            assert sum(bool(d.get('sync', {}).get('samples', 0) >= 3)
                       for d in dash.state.devices.values()) == 50

            async def receive(ws, index):
                async for raw in ws:
                    event = json.loads(raw)
                    current = phase
                    if current is not None:
                        peer = current['peers'][index]
                        peer['frames'][event['type']] += 1
                        peer['bytes'][event['type']] += len(raw.encode('utf-8'))
                        if index == 0:
                            raw_log.write(json.dumps(dict(phase=current['name'], event=event),
                                                     separators=(',', ':'))+'\n')

            with (HERE/'ws-observations.jsonl').open('w') as raw_log:
                for name, count, moving in (
                    ('no-clients-static', 0, False), ('one-client-static', 1, False),
                    ('one-client-moving', 1, True), ('three-clients-moving', 3, True)):
                    while len(connections) < count:
                        ws = await websockets.connect(f'ws://127.0.0.1:{http_port}/ws',
                                                      compression=None, max_size=2**24)
                        readers.append(asyncio.create_task(receive(ws, len(connections))))
                        connections.append(ws)
                    dash.state.data['points'] = {0: points.sanitize_point(dict(
                        id=0, x=1, y=1, motion=dict(type='orbit', center=[1,1],
                                                 radius=.5, period=8)))} if moving else {}
                    # Exclude connect snapshots and the inventory requests they
                    # trigger; remain on the unmodified always-on tap path.
                    await asyncio.sleep(3)
                    phase = dict(name=name, clients=count, moving=moving,
                        queued=Counter(), publications=Counter(), tap_classes=Counter(),
                        peers=[dict(frames=Counter(), bytes=Counter()) for _ in connections])
                    started = time.monotonic()
                    await asyncio.sleep(args.duration)
                    record, phase = phase, None
                    record['elapsed_s'] = time.monotonic()-started
                    records.append(record)
                    print('%s: %s WS messages / %.2fs' % (name,
                        sum(sum(p['frames'].values()) for p in record['peers']),
                        record['elapsed_s']), flush=True)
            hashes = source_hashes()
            result = dict(scope='Loopback transport peers; no browser rendering, hardware or Wi-Fi',
                environment=dict(platform=platform.platform(), python=platform.python_version()),
                nodes=50, heartbeat_interval_s=args.heartbeat, warmup_s=args.warmup,
                compression=False, source_hashes=initial_hashes,
                source_unchanged_during_run=(hashes == initial_hashes), phases=records)
            (HERE/'monitor-results.json').write_text(json.dumps(result, indent=2)+'\n')
        finally:
            phase = None
            for ws in connections:
                await ws.close()
            if readers:
                await asyncio.gather(*readers, return_exceptions=True)
            if fleet is not None and fleet.poll() is None:
                fleet.terminate()
                try:
                    fleet.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    fleet.kill()
                    fleet.wait(timeout=5)
            log.close()
            await dash.stop()
            server.should_exit = True
            await http_task


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=12)
    parser.add_argument('--warmup', type=float, default=12)
    parser.add_argument('--heartbeat', type=float, default=10)
    args = parser.parse_args()
    if min(args.duration, args.warmup, args.heartbeat) <= 0:
        parser.error('timing values must be positive')
    asyncio.run(run(args))
