#!/usr/bin/env python3
"""Production sync loop/estimator over loopback simfleet; never sends LAN traffic.

Live's default execution destination is recorded, but _send_to is intercepted
in this measurement process to deliver to a loopback fleet. Other dashboard
traffic and WebSocket work are deliberately excluded. No runtime file is edited.
"""
import argparse
import asyncio
from collections import Counter
import json
from pathlib import Path
import random
import re
import socket
import statistics
import subprocess
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'tools/simfleet.py').is_file())
sys.path[:0] = [str(ROOT / 'dashboard'), str(ROOT)]
from osc_bridge import OSCBridge
from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder
sys.path.insert(0, str(ROOT / 'tools'))
from sync_measure import parse_fires, spread_stats


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def percentile(values, p):
    return sorted(values)[min(len(values)-1, int((len(values)-1)*p))] if values else None


def summary(values):
    return dict(count=len(values), median=statistics.median(values) if values else None,
                p95=percentile(values, .95), maximum=max(values) if values else None)


def datagram(address, args):
    builder = OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def model(nodes, rate=2.0, targeted=False):
    stamp = '123456789012345'
    ping = len(datagram('/sync/ping', [123, stamp]))
    pong = len(datagram('/sync/pong', [123, stamp, '02:53:49:4d:00:01', stamp]))
    offsets = sum(len(datagram('/%s/sync/offset' % n, ['-40000000'])) for n in range(1, nodes+1))
    query = len(datagram('/sync/query', [123, stamp, '02:53:49:4d:00:01']))
    ping_total = nodes * query if targeted else ping
    messages = rate * (3*nodes if targeted else 1+2*nodes)
    osc_bytes = rate * (ping_total + nodes*pong + offsets)
    return dict(nodes=nodes, rate=rate, messages_s=messages, osc_bytes_s=osc_bytes,
                ipv4_udp_bytes_s=osc_bytes+28*messages,
                broadcast_messages_s=0 if targeted else rate*(1+nodes),
                broadcast_osc_bytes_s=0 if targeted else rate*(ping+offsets),
                ping_size=ping, query_size=query, pong_size=pong, offset_sizes=[
                    len(datagram('/%s/sync/offset' % n, ['-40000000'])) for n in (1, 10, 100)])


async def run(nodes, warmup, duration):
    report_port, cmd_port = free_port(), free_port()
    while report_port == cmd_port:
        cmd_port = free_port()
    uids = ['02:53:49:4d:%02x:%02x' % ((i >> 8)&255, i&255) for i in range(1,nodes+1)]
    ids = {uid: i for i, uid in enumerate(uids, 1)}
    state = SimpleNamespace(data={}, devices={uid: {} for uid in uids},
                            seat_for_uid=lambda uid: {'id': ids[uid]} if uid in ids else None)
    bridge = OSCBridge(state, lambda *_: None, report_port, cmd_port, '255.255.255.255')
    counts, sizes = Counter(), Counter()
    rtts, errors = [], []
    offsets = {}
    measured = False
    loop = asyncio.get_running_loop()
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    observed_routes = set()

    def send_to(address, args, destination, route):
        nonlocal measured
        observed_routes.add((destination[0], route))
        packet = bridge._datagram(address, args)
        if measured and (address == '/sync/ping' or address.endswith('/sync/offset')):
            kind = 'ping' if address == '/sync/ping' else 'offset'
            counts[kind] += 1
            sizes[kind] += len(packet)
        if address.endswith('/sync/offset'):
            offsets[address.split('/')[1]] = int(args[0])
        sender.sendto(packet, ('127.0.0.1', cmd_port))
        return True
    bridge._send_to = send_to

    class Receiver(asyncio.DatagramProtocol):
        def datagram_received(self, packet, source):
            message = OscMessage(packet)
            args = list(message.params)
            if message.address == '/sync/pong':
                if measured:
                    counts['pong'] += 1
                    sizes['pong'] += len(packet)
                bridge.handle_pong(args)
                if measured and args[2] in bridge._sync:
                    facts = state.devices[args[2]].get('sync', {})
                    if facts:
                        rtts.append(facts['rtt']/1e6)
    transport, _ = await loop.create_datagram_endpoint(Receiver, local_addr=('127.0.0.1', report_port))
    log_path = HERE / ('simfleet-%s.log' % nodes)
    with log_path.open('w') as log:
        process = subprocess.Popen([sys.executable, str(ROOT/'tools/simfleet.py'),
            '--devices', str(nodes), '--target', '127.0.0.1',
            '--report-port', str(report_port), '--cmd-port', str(cmd_port),
            '--boot-secs', '0', '--hb-interval', '1',
            '--sync-skew-ms', '40', '--sync-jitter-ms', '0'],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        random.seed(7100+nodes)
        task = None
        try:
            await asyncio.sleep(1)
            if process.poll() is not None:
                raise RuntimeError(log_path.read_text())
            task = asyncio.create_task(bridge.sync_ping_loop())
            await asyncio.sleep(warmup)
            measured = True
            started = time.monotonic()
            await asyncio.sleep(duration)
            elapsed = time.monotonic()-started
            measured = False
            # Continue production sync during the event burst (lead 500ms).
            for index in range(20):
                bridge.send('/all/e/m%s' % index, [str(time.monotonic_ns()+500_000_000)])
                await asyncio.sleep(.1)
            await asyncio.sleep(1)
        finally:
            if task:
                task.cancel()
                await task
            transport.close()
            sender.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    text = log_path.read_text()
    true_skews = {int(i): int(value) for i,value in re.findall(r'id=(\d+).*?sync_skew=(-?\d+)ns', text)}
    for index, actual in true_skews.items():
        if str(index) in offsets:
            errors.append(abs(offsets[str(index)]-actual)/1e6)
    fires = parse_fires(text)
    spreads = spread_stats(fires)
    complete = sum(len(fires.get('m%s' % i, {})) == nodes for i in range(20))
    return dict(nodes=nodes, warmup_s=warmup, measured_s=elapsed,
                counts=dict(counts), osc_bytes=dict(sizes),
                messages_s={k:v/elapsed for k,v in counts.items()},
                osc_bytes_s={k:v/elapsed for k,v in sizes.items()},
                routes=sorted(observed_routes), synced_nodes=len(offsets),
                rtt_ms=summary(rtts), absolute_estimate_error_ms=summary(errors),
                event_spread_ms=summary([v/1e6 for v in spreads.values()]),
                complete_events=complete, requested_events=20, raw_log=log_path.name)


async def main(args):
    result = dict(scope='Loopback single-process simfleet; no Wi-Fi/audio claim',
                  model=[model(n) for n in (4,10,16,32,50,100)],
                  targeted_model=[model(n,.1,True) for n in (4,10,16,32,50,100)],
                  measured=[])
    for n in args.nodes:
        record = await run(n,args.warmup,args.duration)
        assert record['synced_nodes'] == n, record
        assert record['absolute_estimate_error_ms']['count'] == n, record
        assert record['complete_events'] == record['requested_events'] == 20, record
        assert record['event_spread_ms']['count'] == 20, record
        result['measured'].append(record)
        (HERE/'traffic-results.json').write_text(json.dumps(result,indent=2)+'\n')
        print('measured %s nodes' % n, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes', type=int, nargs='+', default=[4,16,32,50])
    parser.add_argument('--warmup', type=float, default=10)
    parser.add_argument('--duration', type=float, default=12)
    args = parser.parse_args()
    if any(n < 2 for n in args.nodes) or args.warmup <= 0 or args.duration <= 0:
        parser.error('nodes must be >=2; warmup and duration must be positive')
    asyncio.run(main(args))
