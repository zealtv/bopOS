#!/usr/bin/env python3
"""Living tests for the I2C cable-run soak scorer (tools/i2c_soak.py).

The soak gates a 54-unit PCB order for Kite Choir, so what it calls a PASS is a
decision, not a detail. These tests pin the two silent-failure rules that were
added on 2026-08-14 after Finn Jet showed that a replugged LIS3DH comes back at
its power-down defaults, answers the bus perfectly, and reports frozen zeros
with no error anywhere.
"""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
for sub in ("python", "tools"):
    if str(REPO / sub) not in sys.path:
        sys.path.insert(0, str(REPO / sub))

import i2c_soak  # noqa: E402


CLEAN_BUCKET = {"index": 3, "errors": 0}


def verdict(**kw):
    """judge() with a clean, passing run as the baseline; override one thing at a time."""
    args = {
        "txns": 500000, "errors": 0, "corruptions": 0, "stalls": 0, "wedges": 0,
        "rate": 0.0, "payload_changed": True, "worst_bucket": CLEAN_BUCKET,
        "resets": 0, "frozen_buckets": 0,
    }
    args.update(kw)
    return i2c_soak.judge(**args)


class ConfigLossTest(unittest.TestCase):
    """CTRL_REG1 read-back is the only positive evidence that the cable dropped 3V3."""

    def test_configured_device_is_not_lost(self):
        self.assertFalse(
            i2c_soak.config_is_lost(i2c_soak.CTRL1_100HZ_XYZ, i2c_soak.CTRL4_HIGH_RES))

    def test_power_down_default_is_lost(self):
        # The exact registers read off Finn Jet after a replug.
        self.assertTrue(
            i2c_soak.config_is_lost(i2c_soak.CTRL1_POWER_DOWN, 0x00))

    def test_ctrl4_alone_going_back_to_default_is_lost(self):
        # A brownout does not politely reset only the register we look at first.
        self.assertTrue(
            i2c_soak.config_is_lost(i2c_soak.CTRL1_100HZ_XYZ, 0x00))


class FrozenBucketTest(unittest.TestCase):
    """Liveness is judged per bucket, so a sensor dying at hour six is still visible."""

    def test_many_identical_reads_is_frozen(self):
        self.assertTrue(i2c_soak.bucket_is_frozen(i2c_soak.FROZEN_BUCKET_READS, False))

    def test_movement_clears_it_however_many_reads(self):
        self.assertFalse(i2c_soak.bucket_is_frozen(100000, True))

    def test_a_short_still_bucket_is_not_frozen(self):
        # Too few samples to distinguish a still sensor from a dead one.
        self.assertFalse(i2c_soak.bucket_is_frozen(i2c_soak.FROZEN_BUCKET_READS - 1, False))


class VerdictTest(unittest.TestCase):
    def test_baseline_run_passes(self):
        self.assertEqual(verdict()[0], "PASS")

    def test_a_device_reset_fails_an_otherwise_flawless_run(self):
        """The regression this whole change exists for.

        Zero transport errors, zero corruption, payload moved -- every counter the
        original scorer had says PASS. But the chip power-cycled, so in the field
        that spool reports frozen zeros and nothing logs it.
        """
        result, why = verdict(resets=1)
        self.assertEqual(result, "FAIL")
        self.assertIn("3V3", why)

    def test_a_frozen_bucket_fails_an_otherwise_flawless_run(self):
        result, why = verdict(frozen_buckets=2)
        self.assertEqual(result, "FAIL")
        self.assertIn("bucket", why)

    def test_run_lifetime_movement_does_not_excuse_a_frozen_bucket(self):
        # payload_changed latches true in the first minute; it must not mask a
        # sensor that died later in the run.
        self.assertEqual(verdict(payload_changed=True, frozen_buckets=1)[0], "FAIL")

    def test_reset_outranks_a_merely_marginal_error_rate(self):
        # Reported as the reset, not as "isolated errors" -- the operator must be
        # told the cable dropped power, not offered a pull-up tweak.
        result, why = verdict(errors=3, rate=6e-6, resets=1)
        self.assertEqual(result, "FAIL")
        self.assertIn("reset", why)

    def test_wedge_still_fails(self):
        self.assertEqual(verdict(wedges=1)[0], "FAIL")

    def test_corruption_still_fails(self):
        self.assertEqual(verdict(corruptions=1)[0], "FAIL")

    def test_isolated_errors_are_marginal_not_pass(self):
        self.assertEqual(verdict(errors=1, rate=2e-6)[0], "MARGINAL")

    def test_clustered_errors_fail(self):
        self.assertEqual(
            verdict(errors=40, rate=8e-5, worst_bucket={"index": 9, "errors": 31})[0], "FAIL")

    def test_no_transactions_is_invalid_not_pass(self):
        self.assertEqual(verdict(txns=0)[0], "INVALID")


class FakeMsg:
    """Stand-in for smbus2.i2c_msg. The read message is filled in by the fake bus."""

    def __init__(self, data=b""):
        self.data = data

    def __iter__(self):
        return iter(self.data)

    @staticmethod
    def write(addr, data):
        return FakeMsg(bytes(data))

    @staticmethod
    def read(addr, count):
        return FakeMsg(bytes(count))


class BrownedOutBus:
    """A bus whose sensor loses power partway through and comes back dead.

    This is the Finn Jet failure reproduced in software: after `healthy`
    transactions the chip reverts to its power-down defaults, and from then on it
    ACKs everything, returns a textbook WHO_AM_I, and emits zeros. Optionally a
    short NACK burst covers the moment of the dropout -- `burst=0` is the nastier
    case, a clean brownout with no transport error anywhere.
    """

    def __init__(self, bus, healthy=400, burst=0, total=1400):
        self.n = 0
        self.healthy = healthy
        self.burst = burst
        self.total = total
        self.ctrl1 = 0x00
        self.ctrl4 = 0x00

    def _phase(self):
        if self.n < self.healthy:
            return "ok"
        if self.n < self.healthy + self.burst:
            return "err"
        return "dead"

    def close(self):
        pass

    def write_byte_data(self, addr, reg, val):
        if reg == i2c_soak.REG_CTRL1:
            self.ctrl1 = val
        if reg == i2c_soak.REG_CTRL4:
            self.ctrl4 = val

    def read_byte_data(self, addr, reg):
        if reg == i2c_soak.REG_WHO_AM_I:      # first op of a probe cycle -- the tick
            self.n += 1
            if self.n > self.total:
                raise KeyboardInterrupt
        phase = self._phase()
        if phase == "err":
            raise OSError(121, "Remote I/O error")
        if reg == i2c_soak.REG_CTRL1:
            return self.ctrl1
        if reg == i2c_soak.REG_CTRL4:
            return self.ctrl4
        if reg == i2c_soak.REG_STATUS:
            return 0x00 if phase == "dead" else i2c_soak.STATUS_ZYXDA
        if reg == i2c_soak.REG_WHO_AM_I:
            return i2c_soak.WHO_AM_I_VALUE    # perfect, even when the chip is dead
        return 0

    def i2c_rdwr(self, write, read):
        phase = self._phase()
        if phase == "err":
            raise OSError(121, "Remote I/O error")
        if phase == "dead":
            self.ctrl1, self.ctrl4 = i2c_soak.CTRL1_POWER_DOWN, 0x00
            read.data = bytes(6)              # frozen zeros
        else:
            read.data = bytes([self.n & 0xFF, 0, 1, 0, 2, 0])


class SoakLoopTest(unittest.TestCase):
    """End-to-end through run(), because the pure scorer was never the weak part.

    judge() can be perfect while the loop never gathers the evidence to feed it.
    """

    def _run(self, tmpdir, config_check=250, **bus_kw):
        out = Path(tmpdir) / "soak.jsonl"
        args = SimpleNamespace(
            bus=1, address=0x19, label="test", duration=600, interval=0,
            bucket=10 ** 9, timeout=2.0, out=str(out), stop_on_wedge=False,
            config_check=config_check)
        with mock.patch.object(i2c_soak, "HAVE_SMBUS", True), \
             mock.patch.object(i2c_soak, "SMBus",
                               lambda bus: BrownedOutBus(bus, **bus_kw), create=True), \
             mock.patch.object(i2c_soak, "i2c_msg", FakeMsg, create=True), \
             mock.patch.object(i2c_soak, "bus_clock_hz", lambda bus: 100000), \
             mock.patch("os.path.exists", return_value=True), \
             mock.patch("sys.stdout", io.StringIO()):
            rc = i2c_soak.run(args)
        events = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
        summary = [e for e in events if e["event"] == "summary"][0]
        return rc, events, summary

    def test_silent_brownout_is_caught_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, events, summary = self._run(tmp)
        self.assertEqual(summary["failures"], 0, "no transport error -- that is the trap")
        self.assertTrue(summary["payload_changed"], "it moved early on -- also the trap")
        self.assertGreater(summary["resets"], 0)
        self.assertTrue(any(e["event"] == "config_reset" for e in events))
        self.assertEqual(summary["verdict"], "FAIL")
        self.assertEqual(rc, 1)

    def test_without_the_read_back_the_same_run_scores_pass(self):
        """Pins the regression: this is what the scorer did before 2026-08-14.

        Same bus, same dead sensor, config read-back effectively disabled -- and
        every counter the original had reports a flawless run.
        """
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, summary = self._run(tmp, config_check=10 ** 9)
        self.assertEqual(summary["resets"], 0)
        self.assertEqual(summary["verdict"], "PASS")
        self.assertEqual(rc, 0)

    def test_a_dropout_with_a_nack_burst_checks_config_at_the_burst_end(self):
        """The errors stopping is the moment that looks like recovery and is not."""
        with tempfile.TemporaryDirectory() as tmp:
            _, events, summary = self._run(tmp, burst=8, config_check=10 ** 9)
        self.assertGreater(summary["failures"], 0)
        reset = [e for e in events if e["event"] == "config_reset"]
        self.assertTrue(reset, "burst-end must trigger a read-back even with periodic off")
        self.assertEqual(reset[0]["why"], "burst-end")
        self.assertTrue(reset[0]["power_down_default"])
        self.assertEqual(summary["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
