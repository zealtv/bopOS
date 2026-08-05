import sys, time, busio, board
import adafruit_ads1x15.ads1115 as ADS1115
import adafruit_ads1x15.ads1x15 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

addr = int(sys.argv[1], 16)
secs = float(sys.argv[2])
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115.ADS1115(i2c, address=addr)
ch = [AnalogIn(ads, p) for p in (ADS.Pin.A0, ADS.Pin.A1, ADS.Pin.A2, ADS.Pin.A3)]
base = [c.voltage for c in ch]
lo = list(base); hi = list(base); events = 0
prev = [False]*4
t0 = time.time()
while time.time() - t0 < secs:
    v = [c.voltage for c in ch]
    for i, x in enumerate(v):
        lo[i] = min(lo[i], x); hi[i] = max(hi[i], x)
        down = abs(x - base[i]) > 0.5
        if down and not prev[i]:
            events += 1
            print("%6.2fs  A%d  %.3f V  (rest %.3f)" % (time.time()-t0, i, x, base[i]), flush=True)
        prev[i] = down
    time.sleep(0.02)
print("--- %ds window, %d edge(s)" % (secs, events))
for i in range(4):
    print("A%d  rest %5.3f  min %5.3f  max %5.3f  swing %5.3f  %s"
          % (i, base[i], lo[i], hi[i], hi[i]-lo[i], "<== MOVED" if hi[i]-lo[i] > 0.3 else ""))
