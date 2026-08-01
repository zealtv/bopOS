(function () {
  // The server opens every connection with a burst of SNAPSHOT messages
  // (`Dashboard.websocket`): the current state of things, sent so a fresh
  // client can draw itself. They are not events — each one supersedes the last
  // and every consumer already expects to receive one at connect.
  //
  // That burst can arrive before all consumers have registered. The scripts are
  // separate classic `<script>` tags, so between `dashboard.js` (which opens
  // the socket and registers first) and `control-host.js`, `monitor.js` or
  // `show.js` the browser must FETCH several more files, and the event loop is
  // free to deliver socket messages during those fetches. The window is exactly
  // network-latency wide, which is why it opens under load.
  //
  // `pending` alone did not cover this: it buffered only while a type had NO
  // handlers, so it protected the FIRST registrant and silently dropped the
  // burst for every later one. Six `state` handlers register after
  // `dashboard.js`; the visible symptom (51) was a Control tab that never
  // painted a card, because `venueKnown` waits for a `state` that had already
  // been delivered to somebody else. Nothing recovered it: heartbeats are
  // `device_update`, and there is no periodic full-`state` broadcast.
  //
  // So snapshots are remembered — the LATEST per type, not a backlog — and
  // replayed to any handler that registers later. `tests/test_ws_snapshot.py`
  // pins this list against the server's actual connect burst, because the two
  // are genuinely coupled and drift would reintroduce the bug in silence.
  const SNAPSHOT_TYPES = new Set([
    "state", "distribution", "venues", "shows",
    "show", "show_warnings", "show_playback",
  ]);

  class ReconnectingSocket {
    constructor(path) {
      this.path = path;
      this.handlers = {};
      this.pending = {};
      this.latest = {};
      this.delay = 500;
      this.connect();
    }
    connect() {
      const scheme = location.protocol === "https:" ? "wss:" : "ws:";
      this.socket = new WebSocket(`${scheme}//${location.host}${this.path}`);
      this.socket.onopen = () => { this.delay = 500; this.emit("connection", true); };
      this.socket.onclose = () => { this.emit("connection", false); setTimeout(() => this.connect(), this.delay); this.delay = Math.min(this.delay * 2, 10000); };
      this.socket.onmessage = event => { const message = JSON.parse(event.data); this.emit(message.type, message.data); };
    }
    on(type, callback) {
      (this.handlers[type] ||= []).push(callback);
      // A snapshot the socket has already seen is current state, not history:
      // hand the new consumer the same thing an early one holds. Only the
      // latest is kept, so a handler registered long after connect is brought
      // up to date rather than replayed a backlog of superseded snapshots.
      if (SNAPSHOT_TYPES.has(type)) {
        if (type in this.latest) callback(this.latest[type]);
        return;
      }
      const pending = this.pending[type];
      if (pending) {
        delete this.pending[type];
        pending.forEach(data => callback(data));
      }
    }
    emit(type, data) {
      // Events queue for a first handler that may not exist yet; snapshots
      // supersede instead, and are replayed by `on` to every later handler.
      if (SNAPSHOT_TYPES.has(type)) {
        this.latest[type] = data;
      } else if (!(this.handlers[type] || []).length) {
        (this.pending[type] ||= []).push(data);
        return;
      }
      (this.handlers[type] || []).forEach(callback => callback(data));
    }
    send(type, data) { if (this.socket.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({type, data})); }
  }
  window.BopSocket = ReconnectingSocket;
})();
