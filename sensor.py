"""Mo hinh cam bien cho he thong giam sat kho."""

from datetime import datetime
import math
from numbers import Real


class Sensor:
    """Cam bien co the luu phep do hop le gan nhat."""

    TYPE_NAME = "GENERIC"
    _VALID_STATUSES = frozenset({"ACTIVE", "INACTIVE", "ERROR"})

    def __init__(self, sensor_id, location_id, status="ACTIVE"):
        self._sensor_id = sensor_id
        self._location_id = location_id
        self._status = self._validate_status(status)
        self._last_measurement = None

    @staticmethod
    def _validate_status(status):
        if not isinstance(status, str):
            raise TypeError("status must be a string")
        if status not in Sensor._VALID_STATUSES:
            raise ValueError("unsupported sensor status")
        return status

    @staticmethod
    def _validate_number(value, field_name):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name} must be a real number")
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite")
        return float(value)

    @staticmethod
    def _validate_timestamp(timestamp):
        if timestamp is None:
            return None
        if not isinstance(timestamp, str):
            raise TypeError("timestamp must be a string or None")
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("timestamp must use ISO 8601 format") from error
        return timestamp

    def set_status(self, new_status):
        """Dat trang thai neu gia tri nam trong contract."""

        self._status = self._validate_status(new_status)

    def update_measurement(self, temperature, humidity, timestamp=None):
        """Thay phep do gan nhat neu cam bien dang hoat dong."""

        if self._status != "ACTIVE":
            return False

        valid_temperature = self._validate_number(temperature, "temperature")
        valid_humidity = self._validate_number(humidity, "humidity")
        valid_timestamp = self._validate_timestamp(timestamp)
        self._last_measurement = {
            "temperature": valid_temperature,
            "humidity": valid_humidity,
            "timestamp": valid_timestamp,
        }
        return True

    def get_reading(self):
        """Tra snapshot gom dung bay truong cua Reading Schema."""

        measurement = self._last_measurement or {}
        return {
            "sensor_id": self._sensor_id,
            "sensor_type": self.TYPE_NAME,
            "location_id": self._location_id,
            "status": self._status,
            "temperature": measurement.get("temperature"),
            "humidity": measurement.get("humidity"),
            "timestamp": measurement.get("timestamp"),
        }


class ColdStorageSensor(Sensor):
    """Cam bien danh cho kho lanh."""

    TYPE_NAME = "COLD_STORAGE"


class DryStorageSensor(Sensor):
    """Cam bien danh cho kho kho."""

    TYPE_NAME = "DRY_STORAGE"


class ServerRoomSensor(Sensor):
    """Cam bien danh cho phong may chu."""

    TYPE_NAME = "SERVER_ROOM"
