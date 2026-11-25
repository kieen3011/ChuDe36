import math
import unittest

from sensor import (
    ColdStorageSensor,
    DryStorageSensor,
    Sensor,
    ServerRoomSensor,
)


class SensorTests(unittest.TestCase):
    def test_new_sensor_has_contract_schema_without_measurement(self):
        sensor = Sensor("S01", "A")

        self.assertEqual(
            sensor.get_reading(),
            {
                "sensor_id": "S01",
                "sensor_type": "GENERIC",
                "location_id": "A",
                "status": "ACTIVE",
                "temperature": None,
                "humidity": None,
                "timestamp": None,
            },
        )

    def test_subclasses_expose_the_contract_type_names(self):
        cases = (
            (ColdStorageSensor, "COLD_STORAGE"),
            (DryStorageSensor, "DRY_STORAGE"),
            (ServerRoomSensor, "SERVER_ROOM"),
        )

        for sensor_class, expected_type in cases:
            with self.subTest(sensor_class=sensor_class.__name__):
                sensor = sensor_class("S01", "A")
                self.assertIsInstance(sensor, Sensor)
                self.assertEqual(sensor.get_reading()["sensor_type"], expected_type)

    def test_invalid_initial_status_is_rejected(self):
        with self.assertRaises(ValueError):
            Sensor("S01", "A", "BROKEN")

    def test_set_status_accepts_every_contract_status(self):
        sensor = Sensor("S01", "A")

        for status in ("INACTIVE", "ERROR", "ACTIVE"):
            sensor.set_status(status)
            self.assertEqual(sensor.get_reading()["status"], status)

    def test_set_status_rejects_non_string_and_unknown_values(self):
        sensor = Sensor("S01", "A")

        with self.assertRaises(TypeError):
            sensor.set_status(None)
        with self.assertRaises(ValueError):
            sensor.set_status("active")

    def test_active_sensor_accepts_and_replaces_latest_measurement(self):
        sensor = Sensor("S01", "A")

        accepted = sensor.update_measurement(
            5, 90.5, "2026-11-24T08:00:00+07:00"
        )

        self.assertTrue(accepted)
        self.assertEqual(sensor.get_reading()["temperature"], 5.0)
        self.assertEqual(sensor.get_reading()["humidity"], 90.5)
        self.assertEqual(
            sensor.get_reading()["timestamp"], "2026-11-24T08:00:00+07:00"
        )

    def test_none_timestamp_is_preserved(self):
        sensor = Sensor("S01", "A")

        self.assertTrue(sensor.update_measurement(5.0, 90.0))
        self.assertIsNone(sensor.get_reading()["timestamp"])

    def test_non_active_sensor_rejects_update_and_keeps_old_measurement(self):
        for status in ("INACTIVE", "ERROR"):
            with self.subTest(status=status):
                sensor = Sensor("S01", "A")
                sensor.update_measurement(5.0, 90.0, "2026-11-24T08:00:00")
                before = sensor.get_reading()
                sensor.set_status(status)

                accepted = sensor.update_measurement(
                    8.0, 95.0, "2026-11-24T08:01:00"
                )

                self.assertFalse(accepted)
                after = sensor.get_reading()
                self.assertEqual(after["temperature"], before["temperature"])
                self.assertEqual(after["humidity"], before["humidity"])
                self.assertEqual(after["timestamp"], before["timestamp"])

    def test_bool_and_non_numeric_measurements_are_rejected_atomically(self):
        sensor = Sensor("S01", "A")
        sensor.update_measurement(5.0, 90.0, "2026-11-24T08:00:00")
        before = sensor.get_reading()

        for temperature, humidity in ((True, 90.0), (5.0, False), ("5", 90.0)):
            with self.subTest(temperature=temperature, humidity=humidity):
                with self.assertRaises(TypeError):
                    sensor.update_measurement(temperature, humidity)
                self.assertEqual(sensor.get_reading(), before)

    def test_non_finite_measurements_are_rejected_atomically(self):
        sensor = Sensor("S01", "A")
        sensor.update_measurement(5.0, 90.0, "2026-11-24T08:00:00")
        before = sensor.get_reading()

        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    sensor.update_measurement(value, 90.0)
                with self.assertRaises(ValueError):
                    sensor.update_measurement(5.0, value)
                self.assertEqual(sensor.get_reading(), before)

    def test_invalid_timestamp_type_and_format_are_rejected_atomically(self):
        sensor = Sensor("S01", "A")
        sensor.update_measurement(5.0, 90.0, "2026-11-24T08:00:00")
        before = sensor.get_reading()

        with self.assertRaises(TypeError):
            sensor.update_measurement(6.0, 91.0, 123)
        with self.assertRaises(ValueError):
            sensor.update_measurement(6.0, 91.0, "24/11/2026 08:01")
        self.assertEqual(sensor.get_reading(), before)

    def test_iso_timestamp_with_z_suffix_is_accepted(self):
        sensor = Sensor("S01", "A")

        self.assertTrue(sensor.update_measurement(5.0, 90.0, "2026-11-24T01:00:00Z"))
        self.assertEqual(sensor.get_reading()["timestamp"], "2026-11-24T01:00:00Z")

    def test_get_reading_returns_a_fresh_snapshot(self):
        sensor = Sensor("S01", "A")
        first = sensor.get_reading()
        first["status"] = "ERROR"

        self.assertEqual(sensor.get_reading()["status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
