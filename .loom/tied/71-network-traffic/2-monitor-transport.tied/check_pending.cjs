// Exercise the shipped socket's unhandled-event buffering with retained WS
// messages. No browser/network or runtime edits; this is a memory-growth probe.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let root = __dirname;
while (!fs.existsSync(path.join(root, 'tools/simfleet.py'))) {
  const parent = path.dirname(root);
  if (parent === root) throw new Error('repo root not found');
  root = parent;
}
const socketSource = fs.readFileSync(path.join(root, 'dashboard/static/js/ws.js'), 'utf8');
const events = fs.readFileSync(path.join(__dirname, 'ws-observations.jsonl'), 'utf8')
  .trim().split('\n').map(line => JSON.parse(line).event);
const facilitator = fs.readFileSync(path.join(root, 'dashboard/static/js/facilitator.js'), 'utf8');
const remoteTypes = [...facilitator.matchAll(/ws\.on\("([^"]+)"/g)].map(match => match[1]);
function probe(handled) {
  class FakeWebSocket {}
  FakeWebSocket.OPEN = 1;
  const context = {window: {}, location: {protocol: 'http:', host: 'localhost'},
    WebSocket: FakeWebSocket, setTimeout: () => 0};
  vm.createContext(context);
  vm.runInContext(socketSource, context);
  const socket = new context.window.BopSocket('/ws');
  for (const type of handled) socket.on(type, () => {});
  for (const event of events) socket.emit(event.type, event.data);
  return Object.fromEntries(Object.entries(socket.pending).map(([type, list]) => [type, list.length]));
}
// The main dashboard + Monitor handle the measured types except `sync`.
// Assert against all JS before claiming that lack of a consumer.
const scripts = fs.readdirSync(path.join(root, 'dashboard/static/js')).filter(f => f.endsWith('.js'));
if (scripts.some(f => /ws\.on\(["']sync["']/.test(fs.readFileSync(path.join(root, 'dashboard/static/js', f), 'utf8')))) {
  throw new Error('sync now has a consumer; update this measurement');
}
const main = probe([...new Set(events.map(event => event.type))].filter(type => type !== 'sync'));
const remote = probe(remoteTypes);
const syncCount = events.filter(event => event.type === 'sync').length;
if (main.sync !== syncCount || remote.sync !== syncCount) throw new Error('unexpected pending behavior');
const result = {scope: 'Shipped BopSocket.emit replay; no browser heap-byte/CPU claim',
  observations: events.length, main_unhandled: main, remote_unhandled: remote};
fs.writeFileSync(path.join(__dirname, 'pending-results.json'), JSON.stringify(result, null, 2)+'\n');
console.log(JSON.stringify(result));
