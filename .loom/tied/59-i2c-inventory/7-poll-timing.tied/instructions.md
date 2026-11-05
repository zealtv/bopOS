# 7-poll-timing

Quick button presses are dropped, because the bridge samples slower than the
event it is meant to catch.

Raised by Bob 2026-08-05 once the chain was working end to end: *"quick button
presses are sometimes dropping."* Actioned in the same session.

## The arithmetic, measured on Ciro Toast

An ADS1115 read is not free, and there are two independent problems.

**(1) The conversion is slow at the default data rate.** Benchmarked on the
real chip at `0x4b`:

| `data_rate` | 4-channel read | 1 channel | ceiling |
|---|---|---|---|
| 128 SPS (library default) | **40.1 ms** | 9.8 ms | 25 Hz |
| 860 SPS (chip maximum) | 12.6 ms | 3.9 ms | 80 Hz |

`io_ads1115.py` never sets `data_rate`, so every node runs at 128 SPS.

**(2) `poll_rate` is not a rate.** The loop is

```python
while self.running:
    self.poll_and_send()
    time.sleep(1.0 / self.poll_rate)
```

The sleep is *added to* the read rather than being the period. At the default
`poll_rate = 10` with a 40 ms read, the true interval is 140 ms — an effective
**7.1 Hz**. The error grows with the number of peripherals and channels, so the
configured number gets less true the more hardware is attached, silently.

Together: a sample every ~140 ms. **A press shorter than that can fall entirely
between two samples and never exist.** A deliberate press is 100–200 ms and a
quick tap is 30–80 ms, so dropped taps are the expected behaviour, not
intermittent flakiness.

Nothing in PD can fix this. Debounce, `[change]` and `[timer]` all operate on
samples that were never taken.

## Deliver

1. **Set `data_rate = 860`** in `io_ads1115.py`, with a comment saying why, so
   the trade is visible: 860 SPS is noisier per sample, which is irrelevant for
   full-rail button swings and would matter for smooth analog sensing off the
   same board.
2. **Sleep the remainder of the period**, not a fixed amount, so `/io/poll 20`
   means 20 Hz. Clamp at zero: when a read is slower than the period the loop
   simply runs as fast as the hardware allows, which cannot spin, because the
   I2C reads are themselves the rate limit.

Deliberately **not** in scope, and listed so they are not lost:

- **Latching in the peripheral** (report min/max or "went low since last
  report") decouples detection from transport and is the durable answer if taps
  still slip through. It changes what `/adc`'s elements mean, so it is a design
  change rather than a fix.
- **Polling only channels in use** — 3 channels not 4 is 30 ms not 40.
- **The ALERT/RDY comparator pin** wired to a GPIO is the only option that gets
  edges without paying CPU for them. Catching a 30 ms event by polling costs
  continuous I2C traffic: at 50 Hz with 860 SPS that is ~63% of a thread, at
  25 Hz ~31%. `jackd` runs `-P70` realtime so audio is insulated, but this is
  not free and would be worse on a Zero.
- `io_ads1015.py` has the same unset-`data_rate` shape and should get the same
  treatment when someone has an ADS1015 to test against. Not changed blind.

## Verify

Measure the effective send rate on a real node, not the configured one: stop
the engine, stand a listener on 6662 in its place, create the peripheral, and
count messages per second. Record before and after.
