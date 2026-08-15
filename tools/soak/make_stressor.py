#!/usr/bin/env python3
"""Generate worst-case I2C interferer audio for the Kite Choir cable soak.

The interferer is dV/dt and dI/dt in the speaker pair, so crest factor matters
more than loudness. Music is the EASY case at a given peak level. These are not.

  gated-noise   full-scale white noise, hard-gated at 8 Hz. Broadband, plus big
                supply-current steps from the gate. The primary stressor.
  gated-square  full-scale square at 300 Hz, same gate, lowpassed ~8 kHz so it
                doesn't cook a tweeter while keeping essentially all the
                electrical slew (the amp's output LC filter limits it anyway).
  sweep         20 Hz -> 20 kHz log sweep, full scale. A DIAGNOSTIC, not a
                screen: run it only if something errors, to find the coupling
                frequency by correlating against the soak's bucket timestamps.
"""
import math, struct, sys, wave

SR = 48000

def gate(t, hz=8.0):
    return 1.0 if (t * hz) % 1.0 < 0.5 else 0.0

def lowpass(xs, fc, sr=SR):
    a = 1.0 / (1.0 + sr / (2 * math.pi * fc))
    y, out = 0.0, []
    for x in xs:
        y += a * (x - y)
        out.append(y)
    return out

def build(kind, secs):
    n = int(SR * secs)
    if kind == "gated-noise":
        import random
        random.seed(1)
        return [(random.random() * 2 - 1) * gate(i / SR) for i in range(n)]
    if kind == "gated-square":
        raw = [(1.0 if (i / SR * 300) % 1.0 < 0.5 else -1.0) * gate(i / SR)
               for i in range(n)]
        return lowpass(raw, 8000)
    if kind == "sweep":
        f0, f1 = 20.0, 20000.0
        k = math.log(f1 / f0)
        return [math.sin(2 * math.pi * f0 * secs / k * (math.exp(i / SR / secs * k) - 1))
                for i in range(n)]
    raise SystemExit("kinds: gated-noise gated-square sweep")

kind = sys.argv[1] if len(sys.argv) > 1 else "gated-noise"
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
out = sys.argv[3] if len(sys.argv) > 3 else kind + ".wav"
dbfs = float(sys.argv[4]) if len(sys.argv) > 4 else -6.0

samples = build(kind, secs)
peak = max(abs(s) for s in samples) or 1.0
gain = 10.0 ** (dbfs / 20.0)
frames = b"".join(struct.pack("<hh", *(int(s / peak * gain * 32767),) * 2)
                  for s in samples)

with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(frames)
print("wrote {} ({}s, {:+.1f} dBFS, stereo)".format(out, secs, dbfs))
