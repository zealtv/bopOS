(function () {
  // Snapshots replay latest-per-type. Pre-handler events expire; unconsumed
  // streams are discarded. Subscriptions install their handlers first.
  const SNAPSHOT_TYPES = new Set([
    "state", "distribution", "show", "show_warnings", "show_playback",
  ]);
  const STREAM_TYPES = new Set(["osc_in", "osc_out", "sync", "heartbeat",
    "point_frame", "telemetry", "capture_counters", "clock_summary", "io_samples", "editor_io"]);
  class ReconnectingSocket {
    constructor(path) {
      this.path = path;
      this.handlers = {};
      this.pending = {};
      this.latest = {};
      this.pendingOrder = [];
      this.pendingBytes = 0;
      this.pendingDropped = 0;
      this.pendingTimer = null;
      this.capture = {directions: [], uids: [], include: [], exclude: [], classes: [],
        map: false, clock: false};
      this.generation = 0;
      this.requestedCaptures = new Map();
      this.delay = 500;
      this.connect();
    }
    connect() {
      const scheme = location.protocol === "https:" ? "wss:" : "ws:";
      this.socket = new WebSocket(`${scheme}//${location.host}${this.path}`);
      this.socket.onopen = () => {
        this.delay = 500;
        this.opening = true;
        this.generation += 1;
        this.emit("connection", true);
        this.opening = false;
        this.sendCapture();
      };
      this.socket.onclose = () => {
        this.emit("connection", false);
        setTimeout(() => this.connect(), this.delay);
        this.delay = Math.min(this.delay * 2, 10000);
      };
      this.socket.onmessage = event => {
        const message = JSON.parse(event.data);
        this.emit(message.type, message.data);
      };
    }
    on(type, callback) {
      (this.handlers[type] ||= []).push(callback);
      if (type === "point_frame") this.requestCapture({map: true});
      this.prunePending();
      if (SNAPSHOT_TYPES.has(type)) {
        if (type in this.latest) callback(this.latest[type]);
        return;
      }
      const pending = this.pending[type];
      if (pending) {
        delete this.pending[type];
        this.pendingOrder = this.pendingOrder.filter(entry => {
          if (entry.type !== type) return true;
          this.pendingBytes -= entry.bytes;
          return false;
        });
        pending.forEach(data => callback(data));
      }
    }
    emit(type, data) {
      if (type === "capture_status") {
        if (!data.error) {
          this.acceptedCapture = this.requestedCaptures.get(data.generation) || this.acceptedCapture;
        } else if (data.requested_generation === this.generation && this.acceptedCapture) {
          this.generation = data.generation;
          this.capture = this.acceptedCapture;
        }
      }
      if (type === "telemetry") {
        if (data.generation !== this.generation) return;
        this.emit("capture_counters", data.status);
        for (const entry of data.entries) this.emit(entry.type, entry.data);
        return;
      }
      if (SNAPSHOT_TYPES.has(type)) {
        this.latest[type] = data;
      } else if (!(this.handlers[type] || []).length) {
        if (STREAM_TYPES.has(type)) return;
        this.prunePending();
        const bytes = new TextEncoder().encode(JSON.stringify(data) || "null").length;
        if (bytes > 65536) { this.pendingDropped += 1; return; }
        (this.pending[type] ||= []).push(data);
        this.pendingOrder.push({type, data, bytes, at: Date.now()});
        this.pendingBytes += bytes;
        this.prunePending();
        return;
      }
      (this.handlers[type] || []).forEach(callback => callback(data));
    }
    prunePending() {
      while (this.pendingOrder.length && (this.pendingOrder.length > 50
          || this.pendingBytes > 65536 || this.pendingOrder[0].at <= Date.now() - 5000)) {
        const entry = this.pendingOrder.shift();
        this.pendingBytes -= entry.bytes;
        this.pending[entry.type]?.shift();
        if (!this.pending[entry.type]?.length) delete this.pending[entry.type];
        this.pendingDropped += 1;
      }
      if (this.pendingTimer !== null) clearTimeout(this.pendingTimer);
      this.pendingTimer = this.pendingOrder.length
        ? setTimeout(() => { this.pendingTimer = null; this.prunePending(); },
          Math.max(1, this.pendingOrder[0].at + 5000 - Date.now())) : null;
    }
    requestCapture(changes) {
      const capture = {...this.capture, ...changes};
      if (JSON.stringify(capture) === JSON.stringify(this.capture)) return;
      this.capture = capture;
      this.generation += 1;
      if (!this.opening) this.sendCapture();
    }
    sendCapture() {
      if (this.socket.readyState !== WebSocket.OPEN) return;
      this.requestedCaptures.set(this.generation, this.capture);
      while (this.requestedCaptures.size > 16) this.requestedCaptures.delete(this.requestedCaptures.keys().next().value);
      this.send("capture_selection", {...this.capture, generation: this.generation});
    }
    send(type, data) {
      if (this.socket.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({type, data}));
    }
  }
  window.BopSocket = ReconnectingSocket;
})();
