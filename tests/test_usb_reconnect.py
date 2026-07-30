import os
import sys
import time
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "recalbox"))

import pm_daemon


class FakeSerial:
    def __init__(self, port, baud, timeout=None):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.writes = []
        self.closed = False
        self.fail_writes = False

    def write(self, data):
        if self.fail_writes:
            raise OSError("simulated write failure")
        self.writes.append(data)

    def flush(self):
        if self.fail_writes:
            raise OSError("simulated flush failure")

    def close(self):
        self.closed = True


class SerialConnectionTests(unittest.TestCase):
    def test_no_device_is_rate_limited(self):
        calls = []
        logs = []

        def find_port():
            calls.append("find")
            return None

        conn = pm_daemon.SerialConnection(
            find_port=find_port,
            serial_factory=FakeSerial,
            log_func=lambda *a: logs.append(a),
            reconnect_interval=2.0,
        )

        self.assertIsNone(conn.ensure_connection(now=10.0))
        self.assertEqual(len(calls), 1)
        self.assertEqual(conn.next_reconnect_at, 12.0)

        self.assertIsNone(conn.ensure_connection(now=11.0))
        self.assertEqual(len(calls), 1)
        self.assertTrue(any("no compatible serial device" in " ".join(map(str, log)) for log in logs))

    def test_write_failure_disconnects_and_retains_frame(self):
        serials = []

        def factory(port, baud, timeout=None):
            ser = FakeSerial(port, baud, timeout)
            serials.append(ser)
            return ser

        conn = pm_daemon.SerialConnection(
            find_port=lambda: "/dev/ttyACM0",
            serial_factory=factory,
            log_func=lambda *a: None,
            reconnect_interval=2.0,
        )

        frame = [(1, 2, 3, 4)] * pm_daemon.NUM_LEDS
        self.assertTrue(conn.send_colors(frame))
        serials[0].fail_writes = True

        self.assertFalse(conn.send_colors(frame))
        self.assertFalse(conn.is_connected())
        self.assertTrue(serials[0].closed)
        self.assertEqual(conn.last_frame, frame)
        self.assertGreater(conn.next_reconnect_at, time.monotonic())

    def test_retained_frame_is_resent_after_reconnect(self):
        serials = []

        def factory(port, baud, timeout=None):
            ser = FakeSerial(port, baud, timeout)
            serials.append(ser)
            return ser

        conn = pm_daemon.SerialConnection(
            find_port=lambda: "/dev/ttyACM0",
            serial_factory=factory,
            log_func=lambda *a: None,
            reconnect_interval=2.0,
        )

        frame = [(7, 6, 5, 4)] * pm_daemon.NUM_LEDS
        conn.next_reconnect_at = time.monotonic() + 60.0

        self.assertFalse(conn.send_colors(frame))
        self.assertEqual(conn.last_frame, frame)
        self.assertEqual(serials, [])

        conn.next_reconnect_at = 0.0
        self.assertIsNotNone(conn.ensure_connection(now=time.monotonic()))
        self.assertEqual(len(serials), 1)
        self.assertEqual(serials[0].writes, [pm_daemon.pack_colors(pm_daemon._mapped_colors(frame))])


if __name__ == "__main__":
    unittest.main()
