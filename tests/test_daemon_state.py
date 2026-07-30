import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "recalbox"))

import pm_daemon


class DaemonStateTests(unittest.TestCase):
    def test_duplicate_state_request_keeps_current_state(self):
        state = pm_daemon.make_state(pm_daemon.STATE_MENU, system_key="snes")
        seen_logs = []

        next_state = pm_daemon.set_state(state, pm_daemon.make_state(pm_daemon.STATE_MENU, system_key="snes"),
                                        log_func=lambda *a: seen_logs.append(a))

        self.assertIs(next_state, state)
        self.assertTrue(any("state unchanged:" in " ".join(map(str, log)) for log in seen_logs))

    def test_state_change_replaces_current_state(self):
        current = pm_daemon.make_state(pm_daemon.STATE_MENU)
        target = pm_daemon.make_state(pm_daemon.STATE_GAME_RUNNING, system_key="nes", rom_key="Mario")

        next_state = pm_daemon.set_state(current, target, log_func=lambda *a: None)

        self.assertEqual(next_state, target)

    def test_menu_and_game_running_have_idle_generators(self):
        menu = pm_daemon.make_state(pm_daemon.STATE_MENU)
        game = pm_daemon.make_state(pm_daemon.STATE_GAME_RUNNING, system_key="snes")

        self.assertIsNotNone(pm_daemon.idle_for_state(menu))
        self.assertIsNotNone(pm_daemon.idle_for_state(game))

    def test_fixed_states_do_not_have_idle_generators(self):
        for name in (pm_daemon.STATE_OFF, pm_daemon.STATE_SHUTDOWN,
                     pm_daemon.STATE_REBOOT, pm_daemon.STATE_SOLID):
            self.assertIsNone(pm_daemon.idle_for_state(pm_daemon.make_state(name)))

    def test_off_shutdown_and_reboot_render_all_off(self):
        for name in (pm_daemon.STATE_OFF, pm_daemon.STATE_SHUTDOWN, pm_daemon.STATE_REBOOT):
            self.assertEqual(pm_daemon.fixed_frame_for_state(pm_daemon.make_state(name)), pm_daemon.all_off())

    def test_solid_state_renders_requested_color(self):
        state = pm_daemon.make_state(pm_daemon.STATE_SOLID, color=(1, 2, 3, 4))

        self.assertEqual(pm_daemon.fixed_frame_for_state(state), pm_daemon.solid(1, 2, 3, 4))


if __name__ == "__main__":
    unittest.main()
