(function () {
  class ReconnectingSocket {
    constructor(path) { this.path = path; this.handlers = {}; this.pending = {}; this.delay = 500; this.connect(); }
    connect() {
      const scheme = location.protocol === "https:" ? "wss:" : "ws:";
      this.socket = new WebSocket(`${scheme}//${location.host}${this.path}`);
      this.socket.onopen = () => { this.delay = 500; this.emit("connection", true); };
      this.socket.onclose = () => { this.emit("connection", false); setTimeout(() => this.connect(), this.delay); this.delay = Math.min(this.delay * 2, 10000); };
      this.socket.onmessage = event => { const message = JSON.parse(event.data); this.emit(message.type, message.data); };
    }
    on(type, callback) {
      (this.handlers[type] ||= []).push(callback);
      const pending = this.pending[type];
      if (pending) {
        delete this.pending[type];
        pending.forEach(data => callback(data));
      }
    }
    emit(type, data) {
      const handlers = this.handlers[type] || [];
      if (!handlers.length) { (this.pending[type] ||= []).push(data); return; }
      handlers.forEach(callback => callback(data));
    }
    send(type, data) { if (this.socket.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({type, data})); }
  }
  window.BopSocket = ReconnectingSocket;
})();
