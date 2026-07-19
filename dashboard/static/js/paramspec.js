(function () {
  "use strict";

  const DURATION = /^(?:\d+(?:\.\d*)?|\.\d+)(ms|s|m|h)$/;
  const OPTION = /^(c|curve|p|phase):(.*)$/;
  const FLOAT = /^\s*[+-]?(?:\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?|\.\d(?:_?\d)*)(?:e[+-]?\d(?:_?\d)*)?\s*$/i;
  const SHAPES = new Set(["sine", "tri", "saw", "square", "sh", "drift"]);

  function number(value, label = "value") {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new Error(`${label} must be numeric`);
    }
    return value;
  }

  function duration(value, label = "duration") {
    if (typeof value === "number") {
      number(value, label);
      if (value < 0) throw new Error(`${label} must not be negative`);
      return {ms: value, amount: String(Number(value)), unit: "ms"};
    }
    if (typeof value !== "string") throw new Error(`${label} must be a duration`);
    const match = value.match(DURATION);
    if (!match) throw new Error(`bad ${label}`);
    const amount = Number(value.slice(0, -match[1].length));
    const ms = amount * {ms: 1, s: 1000, m: 60000, h: 3600000}[match[1]];
    if (ms < 0) throw new Error(`${label} must not be negative`);
    return {ms, amount: String(Number(amount)), unit: match[1]};
  }

  function parse(args, declType) {
    if (!new Set(["f", "i"]).has(declType)) throw new Error("automation requires a numeric declaration");
    if (!Array.isArray(args) || !args.length) throw new Error("parameter message has no arguments");
    const positional = args.map(arg => arg?.value);
    const options = {curve: 0, phase: 0, free: false};
    const seen = new Set();
    while (positional.length && typeof positional[positional.length - 1] === "string") {
      const token = positional[positional.length - 1];
      const match = token.match(OPTION);
      let name;
      let value;
      if (token === "f" || token === "free") {
        name = "free";
        value = true;
      } else if (match) {
        name = match[1] === "c" || match[1] === "curve" ? "curve" : "phase";
        if (!FLOAT.test(match[2])) throw new Error(`bad option ${token}`);
        value = Number(match[2].replaceAll("_", ""));
        if (!Number.isFinite(value)) throw new Error(`bad option ${token}`);
        if (name === "phase" && (value < 0 || value > 1)) throw new Error("phase must be between 0 and 1");
      } else {
        break;
      }
      if (seen.has(name)) throw new Error(`duplicate ${name} option`);
      seen.add(name);
      options[name] = value;
      positional.pop();
    }
    if (!positional.length) throw new Error("parameter message contains only options");
    const head = positional[0];
    if (head === "stop") {
      if (positional.length !== 1 || seen.size) throw new Error("stop takes no arguments or options");
      return {mode: "stop"};
    }
    if (head === "lfo") {
      if (positional.length !== 5) throw new Error("lfo requires shape, min, max, and period");
      if (!SHAPES.has(positional[1])) throw new Error("unknown lfo shape");
      const period = duration(positional[4], "period");
      if (period.ms <= 0) throw new Error("lfo period must be greater than zero");
      return {
        mode: "lfo", shape: positional[1], min: number(positional[2], "minimum"),
        max: number(positional[3], "maximum"), period,
        phase: options.phase, free: options.free, curve: options.curve,
      };
    }
    if (seen.has("phase") || seen.has("free")) throw new Error("phase/free options are lfo-only");
    const loop = head === "loop";
    const values = loop ? positional.slice(1) : positional;
    if (loop && !values.length) throw new Error("loop requires a fade form");
    if (!loop && typeof head === "string") throw new Error("unknown keyword or option");
    let result;
    if (values.length === 1) {
      result = {mode: "value", value: number(values[0])};
    } else if (values.length === 2) {
      result = {mode: "fade", from: null, segments: [{value: number(values[0]), duration: duration(values[1])}], curve: options.curve};
    } else if (values.length === 3) {
      result = {mode: "fade", from: number(values[0]), segments: [{value: number(values[1]), duration: duration(values[2])}], curve: options.curve};
    } else if (values.length >= 4 && values.length % 2 === 0) {
      result = {mode: loop ? "loop" : "fade", from: null, segments: [], curve: options.curve};
      for (let index = 0; index < values.length; index += 2) {
        result.segments.push({value: number(values[index]), duration: duration(values[index + 1])});
      }
    } else if (values.length >= 5) {
      throw new Error("fade segment list must contain destination/duration pairs");
    } else {
      throw new Error("bad fade arity");
    }
    if (result.mode === "value" && seen.has("curve")) throw new Error("curve option requires automation");
    return result;
  }

  window.ParamSpec = Object.freeze({parse});
}());
