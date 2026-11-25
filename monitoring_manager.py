"""Registry quan ly cac cam bien cua he thong."""

from sensor import Sensor


class MonitoringManager:
    """Dang ky cam bien va tao snapshot theo thu tu dang ky."""

    def __init__(self):
        self._sensors = {}

    @staticmethod
    def _validate_sensor_id(sensor_id):
        if not isinstance(sensor_id, str):
            raise TypeError("sensor_id must be a string")
        if not sensor_id.strip():
            raise ValueError("sensor_id must not be empty")

    def register_sensor(self, sensor):
        """Dang ky mot Sensor co ID chua ton tai."""

        if not isinstance(sensor, Sensor):
            raise TypeError("sensor must be a Sensor")
        sensor_id = sensor._sensor_id
        self._validate_sensor_id(sensor_id)
        if sensor_id in self._sensors:
            raise ValueError("sensor_id is already registered")
        self._sensors[sensor_id] = sensor

    def remove_sensor(self, sensor_id):
        """Xoa cam bien va cho biet ID co ton tai hay khong."""

        self._validate_sensor_id(sensor_id)
        return self._sensors.pop(sensor_id, None) is not None

    def get_sensor(self, sensor_id):
        """Tra Sensor theo ID chinh xac hoac None."""

        self._validate_sensor_id(sensor_id)
        return self._sensors.get(sensor_id)

    def get_all_sensors(self):
        """Tra list moi chua cac reference Sensor da dang ky."""

        return list(self._sensors.values())

    def collect_readings(self):
        """Tao snapshot cho tat ca Sensor theo thu tu dang ky."""

        return [sensor.get_reading() for sensor in self._sensors.values()]
