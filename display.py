"""Hien thi snapshot va thong ke tren console."""


def _format_value(value):
    """Doi gia tri thieu hoac bool thanh N/A."""
    if value is None or isinstance(value, bool):
        return "N/A"
    return str(value)


def render_snapshot(readings: list[dict], alerts: list[dict], step_index: int) -> None:
    """Hien thi snapshot cua mot buoc ma khong thay doi du lieu dau vao."""
    alerts_by_sensor = {}
    for alert in alerts:
        sensor_id = alert.get("sensor_id")
        if sensor_id is not None:
            alerts_by_sensor[sensor_id] = alert

    print(f"\nBUOC MO PHONG {step_index}")
    print(
        "Sensor ID | Location | Sensor Type | Status | "
        "Temperature | Humidity | Alert Level"
    )
    print("-" * 96)

    for reading in readings:
        sensor_id = reading["sensor_id"]
        status = reading["status"]
        raw_temp = reading.get("temperature")
        raw_hum = reading.get("humidity")
        temperature = _format_value(raw_temp)
        humidity = _format_value(raw_hum)

        if status == "ACTIVE":
            alert = alerts_by_sensor.get(sensor_id)
            alert_level = alert["severity"] if alert is not None else "NORMAL"
            stale_label = ""
        else:
            alert_level = "N/A"
            has_last_value = (
                (raw_temp is not None and not isinstance(raw_temp, bool))
                or (raw_hum is not None and not isinstance(raw_hum, bool))
            )
            stale_label = " (gia tri cu)" if has_last_value else ""

        print(
            f"{sensor_id} | {reading['location_id']} | "
            f"{reading['sensor_type']} | {status} | "
            f"{temperature}{stale_label} | {humidity}{stale_label} | {alert_level}"
        )


def render_summary(summary: dict) -> None:
    """Hien thi tong ket thong ke do StatisticsTracker cung cap."""
    print("\nTONG KET")
    print(f"Tong canh bao: {summary['total_alerts']}")
    print(f"Tong loi: {summary['total_errors']}")
    print("\nTheo khu vuc:")

    by_location = summary.get("by_location") or {}
    if not by_location:
        print("Khong co canh bao moi truong.")
    else:
        print("Location | WARNING | CRITICAL | Total")
        print("-" * 40)
        for location_id, counts in by_location.items():
            print(
                f"{location_id} | {counts['WARNING']} | "
                f"{counts['CRITICAL']} | {counts['total']}"
            )

    print("\nLoi he thong:")
    errors_by_type = summary.get("errors_by_type") or {}
    if not errors_by_type:
        print("Khong co loi he thong.")
    else:
        for error_type, count in errors_by_type.items():
            print(f"{error_type}: {count}")