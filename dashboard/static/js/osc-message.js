(function () {
  const ADDRESS_RE = /^\/(?!\/)(?:[^\s#*,?[\]{}]+\/?)*[^\s/#*,?[\]{}]$/;
  const INTEGER_RE = /^[+-]?\d+$/;
  const FLOAT_RE = /^[+-]?(?:\d+\.\d*|\.\d+|\d+[eE][+-]?\d+|\d*\.\d+[eE][+-]?\d+)$/;

  function typedArg(kind, value) {
    if (kind === "s") return {type: "s", value: String(value ?? "")};
    if (kind === "i") return {type: "i", value: Math.trunc(Number(value) || 0)};
    const number = Number(value) || 0;
    return {type: "f", value: Number(number.toPrecision(6))};
  }

  function tokenize(line) {
    const tokens = [];
    let value = "";
    let quote = null;
    let escaped = false;
    let quoted = false;
    let started = false;
    for (const character of line.trim()) {
      if (escaped) {
        value += character === "n" ? "\n" : character === "t" ? "\t" : character;
        escaped = false;
        started = true;
        continue;
      }
      if (character === "\\") {
        escaped = true;
        started = true;
        continue;
      }
      if (quote) {
        if (character === quote) {
          quote = null;
          quoted = true;
        } else {
          value += character;
        }
        started = true;
        continue;
      }
      if (character === '"' || character === "'") {
        quote = character;
        started = true;
        continue;
      }
      if (/\s/.test(character)) {
        if (started) {
          tokens.push({value, quoted});
          value = "";
          quoted = false;
          started = false;
        }
        continue;
      }
      value += character;
      started = true;
    }
    if (escaped) throw new Error("A trailing backslash needs a character.");
    if (quote) throw new Error("Close the quoted string.");
    if (started) tokens.push({value, quoted});
    return tokens;
  }

  function parseInteger(text) {
    const value = Number(text);
    if (!Number.isSafeInteger(value) || value < -2147483648 || value > 2147483647) {
      throw new Error(`Integer ${text} is outside signed 32-bit range.`);
    }
    return {type: "i", value};
  }

  function parseFloat(text) {
    const value = Number(text);
    if (!Number.isFinite(value)) throw new Error(`Float ${text} is not finite.`);
    if (value !== Number(Number(value).toPrecision(6))) {
      throw new Error(`Float ${text} needs more than 6 significant figures.`);
    }
    return {type: "f", value};
  }

  function parseArgument(token) {
    if (token.quoted) return {type: "s", value: token.value};
    const prefix = token.value.slice(0, 2);
    const body = token.value.slice(2);
    if (prefix === "s:") return {type: "s", value: body};
    if (prefix === "i:") {
      if (!INTEGER_RE.test(body)) throw new Error(`Invalid integer ${body || "(empty)"}.`);
      return parseInteger(body);
    }
    if (prefix === "f:") {
      if (!INTEGER_RE.test(body) && !FLOAT_RE.test(body)) {
        throw new Error(`Invalid float ${body || "(empty)"}.`);
      }
      return parseFloat(body);
    }
    if (INTEGER_RE.test(token.value)) return parseInteger(token.value);
    if (FLOAT_RE.test(token.value)) return parseFloat(token.value);
    return {type: "s", value: token.value};
  }

  function parseLine(line) {
    const tokens = tokenize(String(line || ""));
    if (!tokens.length) throw new Error("Type an OSC address and optional arguments.");
    const address = tokens.shift().value;
    if (!ADDRESS_RE.test(address)) {
      throw new Error("OSC address must be an absolute path without spaces or pattern characters.");
    }
    if (address.length > 255) throw new Error("OSC address is longer than 255 characters.");
    if (tokens.length > 64) throw new Error("An OSC send can contain at most 64 arguments.");
    return {address, args: tokens.map(parseArgument)};
  }

  window.OscMessage = {parseLine, typedArg};
})();
