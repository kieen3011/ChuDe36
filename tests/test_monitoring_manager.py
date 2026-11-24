import unittest

from monitoring_manager import MonitoringManager
from sensor import Sensor


class ExplodingSensor(Sensor):
    def get_reading(self):
        raise RuntimeError("reading failed")


class MonitoringManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = MonitoringManager()

    def test_register_and_lookup_preserve_sensor_reference(self):
        sensor = Sensor("S01", "A")

        self.manager.register_sensor(sensor)

        self.assertIs(self.manager.get_sensor("S01"), sensor)

    def test_register_rejects_non_sensor(self):
        with self.assertRaises(TypeError):
            self.manager.register_sensor(object())

    def test_register_rejects_duplicate_sensor_id(self):
        self.manager.register_sensor(Sensor("S01", "A"))

        with self.assertRaises(ValueError):
            self.manager.register_sensor(Sensor("S01", "B"))

    def test_register_validates_sensor_id_without_normalizing_it(self):
        with self.assertRaises(TypeError):
            self.manager.register_sensor(Sensor(1, "A"))
        with self.assertRaises(ValueError):
            self.manager.register_sensor(Sensor("   ", "A"))

        spaced = Sensor(" S01 ", "A")
        self.manager.register_sensor(spaced)
        self.assertIs(self.manager.get_sensor(" S01 "), spaced)
        self.assertIsNone(self.manager.get_sensor("S01"))

    def test_get_sensor_validates_lookup_id(self):
        for invalid_id, exception in ((1, TypeError), ("", ValueError), ("  ", ValueError)):
            with self.subTest(sensor_id=invalid_id):
                with self.assertRaises(exception):
                    self.manager.get_sensor(invalid_id)

    def test_remove_sensor_reports_found_and_missing(self):
        self.manager.register_sensor(Sensor("S01", "A"))

        self.assertTrue(self.manager.remove_sensor("S01"))
        self.assertFalse(self.manager.remove_sensor("S01"))

    def test_remove_sensor_validates_id(self):
        with self.assertRaises(TypeError):
            self.manager.remove_sensor(None)
        with self.assertRaises(ValueError):
            self.manager.remove_sensor("\t")

    def test_get_all_sensors_returns_new_list_with_original_references(self):
        first = Sensor("S01", "A")
        second = Sensor("S02", "B")
        self.manager.register_sensor(first)
        self.manager.register_sensor(second)

        sensors = self.manager.get_all_sensors()
        sensors.clear()

        self.assertEqual(self.manager.get_all_sensors(), [first, second])

    def test_collect_readings_includes_every_status_in_registration_order(self):
        active = Sensor("S01", "A")
        inactive = Sensor("S02", "B", "INACTIVE")
        error = Sensor("S03", "C", "ERROR")
        for sensor in (active, inactive, error):
            self.manager.register_sensor(sensor)

        readings = self.manager.collect_readings()

        self.assertEqual(
            [(item["sensor_id"], item["status"]) for item in readings],
            [("S01", "ACTIVE"), ("S02", "INACTIVE"), ("S03", "ERROR")],
        )

    def test_collect_readings_propagates_sensor_exception(self):
        self.manager.register_sensor(ExplodingSensor("S01", "A"))

        with self.assertRaisesRegex(RuntimeError, "reading failed"):
            self.manager.collect_readings()


if __name__ == "__main__":
    unittest.main()
