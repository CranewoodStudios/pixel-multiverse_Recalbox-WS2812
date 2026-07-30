import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "recalbox"))

import pm_daemon


class NonBlockingAnimationTests(unittest.TestCase):
    def test_timed_animation_returns_one_frame_per_due_update(self):
        first = [(1, 1, 1, 1)] * pm_daemon.NUM_LEDS
        second = [(2, 2, 2, 2)] * pm_daemon.NUM_LEDS
        anim = pm_daemon.TimedFramesAnimation([first, second], frame_ms=100)

        self.assertEqual(anim.update(1.0), first)
        self.assertIsNone(anim.update(1.05))
        self.assertEqual(anim.update(1.10), second)

    def test_timed_animation_finishes_without_blocking(self):
        frame = [(1, 1, 1, 1)] * pm_daemon.NUM_LEDS
        anim = pm_daemon.TimedFramesAnimation([frame], frame_ms=100)

        self.assertEqual(anim.update(1.0), frame)
        self.assertIsNone(anim.update(1.2))

        self.assertTrue(anim.is_finished())

    def test_menu_pulse_frame_rate_is_limited(self):
        anim = pm_daemon.MenuPulseAnimation(seconds=1.0, fps=10)

        self.assertIsNotNone(anim.update(1.0))
        self.assertIsNone(anim.update(1.05))
        self.assertIsNotNone(anim.update(1.10))

    def test_new_animation_can_replace_active_animation(self):
        active = pm_daemon.TimedFramesAnimation([pm_daemon.all_off()], frame_ms=100)
        active.update(1.0)

        replacement = pm_daemon.make_settings_changed_animation()
        active = replacement

        self.assertIs(active, replacement)
        self.assertIsNotNone(active.update(1.0))

    def test_repeat_frame_preserves_configured_delay_without_sleep(self):
        frame = [(3, 3, 3, 3)] * pm_daemon.NUM_LEDS

        repeated = list(pm_daemon.repeat_frame(frame, seconds=0.1, fps=30))

        self.assertEqual(len(repeated), 3)
        self.assertEqual(repeated, [frame, frame, frame])


if __name__ == "__main__":
    unittest.main()
