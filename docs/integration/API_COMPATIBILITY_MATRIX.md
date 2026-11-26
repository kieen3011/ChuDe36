# API Compatibility Matrix

## Hiện trạng tại baseline

| Luồng | API producer | API consumer | Trạng thái | Phase 2 proposal |
|---|---|---|---|---|
| TV2 → Orchestrator | `DataSimulator.next_reading(zone_id, ...)` | `generate_events(step_index, timestamp)` | Incompatible | `SimulationAdapter.generate_events(...)` |
| TV1 → TV3 | Reading Record dictionary | `AlertSystem.evaluate(sensor_id, location, temperature, humidity, timestamp)` | Incompatible | `AlertAdapter.evaluate(reading)` |
| TV3 → TV4 | `location`, `alert_level`, `message` | canonical Alert Record | Incompatible | Structured result mapping in adapter |
| TV4 → TV5 | `error_count` | `total_errors`, `errors_by_type` | Incompatible | Derived compatibility view |
| TV1 → TV5 | Reading Record | `render_snapshot(readings, alerts, step)` | Compatible | Keep |
| TV1 → TV4 error | dictionary | `record_error(dict)` | Structurally accepted | Freeze Error Record |
| TV4 export | `export_csv`, `export_json` | Orchestrator | Compatible | Keep |

## Kiến trúc trước tích hợp

```text
DataSimulator --X--> main.py --X--> AlertSystem --X--> StatisticsTracker --X--> Display
       next_reading       reading dict        legacy alert          summary mismatch
```

## Kiến trúc candidate sau tích hợp

```text
DataSimulator
    |
SimulationAdapter  -> canonical Simulation Event
    |
main.py / Sensor / MonitoringManager
    |
AlertAdapter       -> None | canonical Alert Record | Error Record
    |
StatisticsTracker  -> canonical Summary Record
    |
Summary compatibility view -> display.py
```

Adapters bảo toàn thuật toán TV2/TV3. Orchestrator tiếp tục sở hữu lifecycle và routing; adapter không thay đổi Sensor.

## Location mapping

| Core ID | Legacy adapter label | Display name |
|---|---|---|
| `A` | `Khu A` | Kho lạnh trái cây |
| `B` | `Khu B` | Kho hạt khô |
| `C` | `Khu C` | Phòng máy chủ |

Mapping phải là dữ liệu cấu hình rõ ràng, không nối chuỗi tùy ý ở nhiều module.

## Phase 2 result

| Luồng | Kết quả |
|---|---|
| TV2 → SimulationAdapter → main | PASS |
| Reading → AlertAdapter → TV3 | PASS |
| AlertAdapter → TV4 canonical Alert Record | PASS |
| TV4 Summary → compatibility view → TV5 | PASS |
| Error Record → TV4 errors_by_type | PASS |
| CSV/JSON export | PASS |
| CLI composition root | PASS |
