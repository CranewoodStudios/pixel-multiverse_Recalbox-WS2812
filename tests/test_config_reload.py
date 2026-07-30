import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "recalbox"))

import pm_daemon


class ConfigReloadTests(unittest.TestCase):
    def setUp(self):
        self.old_systems = pm_daemon.SYSTEMS_JSON
        self.old_buttons = pm_daemon.BUTTONS_JSON
        self.old_cfg = pm_daemon._cfg
        self.old_buttons_cfg = pm_daemon._buttons_cfg
        self.old_num_leds = pm_daemon.NUM_LEDS
        self.old_order = pm_daemon.ORDER
        self.old_coord_map = pm_daemon._coord_map
        self.old_pattern_queue = pm_daemon._pattern_queue
        self.tmp = tempfile.TemporaryDirectory()
        pm_daemon.SYSTEMS_JSON = os.path.join(self.tmp.name, "systems.json")
        pm_daemon.BUTTONS_JSON = os.path.join(self.tmp.name, "buttons.json")

    def tearDown(self):
        self.tmp.cleanup()
        pm_daemon.SYSTEMS_JSON = self.old_systems
        pm_daemon.BUTTONS_JSON = self.old_buttons
        pm_daemon.apply_runtime_config(
            self.old_cfg,
            self.old_buttons_cfg,
            self.old_num_leds,
            self.old_order,
            self.old_coord_map,
            self.old_pattern_queue,
        )

    def write_json(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f)

    def test_reload_rebuilds_led_count_order_and_patterns(self):
        self.write_json(pm_daemon.SYSTEMS_JSON, {"defaults": {"attract": "breath"}})
        self.write_json(pm_daemon.BUTTONS_JSON, {
            "buttons": {
                "enabled": True,
                "num_leds": 3,
                "led_map": [{"coord": [0, 0], "value": 2}],
                "attract_program": [{"pattern": "linear", "params": {"direction": "left_to_right"}}],
            }
        })

        self.assertTrue(pm_daemon.reload_runtime_config_safely())

        self.assertEqual(pm_daemon.NUM_LEDS, 3)
        self.assertEqual(pm_daemon.ORDER, [0, 1, 2])
        self.assertEqual(pm_daemon._coord_map, {(0, 0): 2})
        self.assertEqual(pm_daemon._pattern_queue, [("linear", {"direction": "left_to_right"})])

    def test_malformed_reload_keeps_previous_valid_configuration(self):
        self.write_json(pm_daemon.SYSTEMS_JSON, {"defaults": {"attract": "breath"}})
        self.write_json(pm_daemon.BUTTONS_JSON, {"buttons": {"enabled": True, "num_leds": 4}})
        self.assertTrue(pm_daemon.reload_runtime_config_safely())

        with open(pm_daemon.BUTTONS_JSON, "w") as f:
            f.write("{malformed")

        self.assertFalse(pm_daemon.reload_runtime_config_safely())
        self.assertEqual(pm_daemon.NUM_LEDS, 4)
        self.assertEqual(pm_daemon.ORDER, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
