#!/usr/bin/env node
"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

let root = __dirname;
while (!fs.existsSync(path.join(root, "dashboard", "static", "js", "ws.js"))) {
  const parent = path.dirname(root);
  if (parent === root) throw new Error("cannot locate repository");
  root = parent;
}

class ImmediateWebSocket {
  constructor() { this.readyState = ImmediateWebSocket.OPEN; }
  set onopen(callback) { callback(); }
  set onclose(callback) { this.closeCallback = callback; }
  set onmessage(callback) {
    callback({data: JSON.stringify({type: "state", data: {ready: true}})});
  }
  send() {}
}
ImmediateWebSocket.OPEN = 1;

global.window = global;
global.location = {protocol: "http:", host: "localhost"};
global.WebSocket = ImmediateWebSocket;
vm.runInThisContext(fs.readFileSync(
  path.join(root, "dashboard", "static", "js", "ws.js"), "utf8"));

const socket = new global.BopSocket("/ws");
let connection = null;
let state = null;
socket.on("connection", value => { connection = value; });
socket.on("state", value => { state = value; });
assert.strictEqual(connection, true, "early connection event must be retained");
assert.deepStrictEqual(state, {ready: true}, "early state event must be retained");
console.log("[PASS] synchronous connection and state drain on late handler registration");

for (const filename of ["index.html", "facilitator.html"]) {
  const html = fs.readFileSync(path.join(root, "dashboard", "static", filename), "utf8");
  assert(html.includes("<small>loading...</small>"), `${filename} has the requested caption`);
  assert(!html.includes("getting the room ready"), `${filename} retires the old caption`);
}
console.log("[PASS] both pages use loading... and retire the old caption");
