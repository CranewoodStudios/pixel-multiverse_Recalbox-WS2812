import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "recalbox"))

import pm_daemon


class RecordingUsb:
    def __init__(self):
        self.frames = []
        self.last_frame = None

    def send_colors(self, cols):
        frame = list(cols)
        self.frames.append(frame)
        self.last_frame = frame
        return True


class FadeEngineTests(unittest.TestCase):
    def test_blend_frames_interpolates_from_current_values(self):
        start = [(0, 0, 0, 0)] * pm_daemon.NUM_LEDS
        target = [(10, 20, 30, 40)] * pm_daemon.NUM_LEDS

        self.assertEqual(
            pm_daemon.blend_frames(start, target, 0.5),
            [(5, 10, 15, 20)] * pm_daemon.NUM_LEDS,
        )

    def test_output_tracks_last_sent_frame(self):
        usb = RecordingUsb()
        output = pm_daemon.FrameOutput(usb)
        frame = [(1, 2, 3, 4)] * pm_daemon.NUM_LEDS

        output.send_colors(frame)

        self.assertEqual(output.current_frame, frame)
        self.assertEqual(usb.frames, [frame])

    def test_fade_starts_from_current_frame(self):
        usb = RecordingUsb()
        output = pm_daemon.FrameOutput(usb, fps=50)
        output.send_colors([(10, 10, 10, 10)] * pm_daemon.NUM_LEDS)

        output.start_fade([(20, 20, 20, 20)] * pm_daemon.NUM_LEDS, ms_total=1000, now=1.0)
        output.update(now=1.5)

        self.assertEqual(usb.frames[-1], [(15, 15, 15, 15)] * pm_daemon.NUM_LEDS)

    def test_new_fade_replaces_active_fade_cleanly(self):
        usb = RecordingUsb()
        output = pm_daemon.FrameOutput(usb, fps=50)
        output.send_colors([(0, 0, 0, 0)] * pm_daemon.NUM_LEDS)
        output.start_fade([(100, 100, 100, 100)] * pm_daemon.NUM_LEDS, ms_total=1000, now=1.0)
        output.update(now=1.5)

        output.start_fade([(0, 0, 0, 0)] * pm_daemon.NUM_LEDS, ms_total=1000, now=1.5)
        output.update(now=2.0)

        self.assertEqual(usb.frames[-1], [(25, 25, 25, 25)] * pm_daemon.NUM_LEDS)

    def test_duplicate_frame_is_not_resent_when_usb_has_same_intent(self):
        usb = RecordingUsb()
        output = pm_daemon.FrameOutput(usb)
        frame = [(1, 2, 3, 4)] * pm_daemon.NUM_LEDS

        output.send_colors(frame)
        output.send_colors(frame)

        self.assertEqual(usb.frames, [frame])

    def test_initial_duplicate_frame_is_retained_for_disconnected_usb(self):
        usb = RecordingUsb()
        output = pm_daemon.FrameOutput(usb)
        frame = pm_daemon.all_off()

        output.send_colors(frame)

        self.assertEqual(usb.frames, [frame])


if __name__ == "__main__":
    unittest.main()
