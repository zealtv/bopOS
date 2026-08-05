import sys, time, busio, board
import adafruit_ads1x15.ads1115 as ADS1115
import adafruit_ads1x15.ads1x15 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

addr = int(sys.argv[1], 16)
secs = float(sys.argv[2])
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115.ADS1115(i2c, address=addr)
ch = [AnalogIn(ads, p) for p in (ADS.Pin.A0, ADS.Pin.A1, ADS.Pin.A2, ADS.Pin.A3)]
lo = [9.0]*4; hi = [-9.0]*4; n = 0
t0 = time.time()
while time.time() - t0 < secs:
    v = [c.voltage for c in ch]
    for i, x in enumerate(v):
        lo[i] = min(lo[i], x); hi[i] = max(hi[i], x)
    n += 1
    time.sleep(0.05)
print("samples %d over %.0fs" % (n, secs))
for i in range(4):
    print("A%d  min %5.3f  max %5.3f  range %5.3f  %s"
          % (i, lo[i], hi[i], hi[i]-lo[i], "<== MOVED" if hi[i]-lo[i] > 0.2 else ""))
