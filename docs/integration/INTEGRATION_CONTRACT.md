# CHUDE36 Integration Contract Candidate

Baseline: `a703f835d4d35d2f01469fc115eca4927fc9430d`

Tài liệu này là contract đã được áp dụng cho Stable Python Core candidate.

## 1. Core identifiers

- Location ID chuẩn: `A`, `B`, `C`.
- `Khu A`, `Khu B`, `Khu C` chỉ là nhãn tương thích tại adapter.
- Sensor ID là chuỗi không rỗng và không được tự động normalize.

## 2. Reading Record

```python
{
    "sensor_id": str,
    "sensor_type": str,
    "location_id": str,
    "status": "ACTIVE" | "INACTIVE" | "ERROR",
    "temperature": float | None,
    "humidity": float | None,
    "timestamp": str | None,
}
```

Sensor vẫn cho phép `timestamp=None`. Simulation Event thì bắt buộc có timestamp của bước.

## 3. Simulation Event

```python
{
    "kind": "READING" | "DISCONNECT" | "RECOVER" | "INVALID_DATA",
    "sensor_id": str,
    "timestamp": str,
    "temperature": float | None,
    "humidity": float | None,
}
```

- `READING`: temperature và humidity là số hữu hạn, không phải bool.
- `DISCONNECT`, `RECOVER`: temperature và humidity bằng `None`.
- `INVALID_DATA`: giữ dữ liệu lỗi để ghi nhận, không cập nhật Sensor.
- Tối đa một event cho một sensor trong một bước.
- Adapter chỉ phát event, không thay đổi trạng thái Sensor.

## 4. Alert Record

```python
{
    "sensor_id": str,
    "location_id": str,
    "timestamp": str,
    "severity": "WARNING" | "CRITICAL",
    "violated_metrics": list[str],
    "temperature": float,
    "humidity": float,
}
```

- `NORMAL` trả `None`, không ghi Environmental Alert.
- Một reading chỉ tạo tối đa một Alert Record.
- Nếu cả hai metric vi phạm, `violated_metrics` chứa cả hai và severity lấy mức cao nhất.
- Adapter phải lấy metric vi phạm từ dữ liệu có cấu trúc, không parse message tiếng Việt.

## 5. Error Record candidate

```python
{
    "kind": "DISCONNECT" | "INVALID_DATA" | "UNKNOWN_SENSOR",
    "sensor_id": str | None,
    "location_id": str | None,
    "timestamp": str,
    "message": str,
}
```

`kind`, `timestamp`, `message` bắt buộc. Chính sách nullable của `sensor_id` và `location_id` đang chờ DR-02.

Hardware/Data Error không được chuyển thành Alert Record và không tăng số cảnh báo môi trường.

## 6. Summary Record

```python
{
    "session_id": str,
    "total_alerts": int,
    "warning_count": int,
    "critical_count": int,
    "error_count": int,
    "by_location": dict,
    "errors_by_type": dict[str, int],
}
```

TV5 compatibility adapter có thể thêm `total_errors = summary["error_count"]` vào một bản sao. Không lưu hoặc cập nhật hai counter độc lập.

## 7. Data integrity

- Từ chối bool, NaN và infinity trước khi thay đổi state hoặc dedup key.
- Không mutate dictionary/list do module khác cung cấp.
- JSON sử dụng dữ liệu hữu hạn và phải serialize với `allow_nan=False`.
- Chỉ reading mới được Sensor chấp nhận mới được đánh giá cảnh báo.
- Snapshot và stale measurement chỉ dùng để hiển thị.
- Freshness là metadata tại orchestration/display boundary, không thêm trường vào Reading Record.
- ACTIVE sau RECOVER vẫn là stale cho tới khi Sensor chấp nhận reading có timestamp của bước mới.
- Export ghi hoàn chỉnh vào temporary file cùng thư mục, flush/fsync và dùng `os.replace`. Nếu replace thất bại, exception được truyền về caller và destination cũ được giữ nguyên.

## 8. Display freshness compatibility

`render_snapshot(readings, alerts, step_index, current_timestamp=None)` giữ tương thích với caller cũ. Khi `current_timestamp` được cung cấp:

- timestamp trùng bước: fresh, có thể hiển thị NORMAL hoặc severity mới;
- ACTIVE nhưng timestamp cũ: recovery pending, hiển thị `N/A` cho alert level;
- không có measurement: hiển thị `N/A`;
- ERROR/INACTIVE có measurement: đánh dấu giá trị cũ.

## 9. Threshold evidence

Master Handoff V1.0 quy định:

| Location | Temperature | Humidity |
|---|---|---|
| A | `2 <= t <= 8` | `85 <= h <= 95` |
| B | `18 <= t <= 25` | `h < 60` |
| C | `t < 30` | `40 <= h <= 60` |

CRITICAL khi lệch khỏi biên an toàn từ `3°C` hoặc `10` điểm phần trăm trở lên. Với giới hạn `<`, giá trị bằng giới hạn là WARNING dù delta số học bằng 0.

Fixtures hiện tại xác nhận inclusive/exclusive boundaries trên. `alert_system.py` hiện mâu thuẫn ở B/C và sẽ chỉ được sửa trong Phase 2 sau khi contract candidate được duyệt.

## 10. Simulation Adapter state machine

Adapter giữ connection state riêng theo `sensor_id`: `CONNECTED` hoặc `DISCONNECTED`. Adapter có thể đọc Sensor status qua interface chỉ đọc nhưng không gọi `set_status()` và không update Sensor.

| Sensor status | Connection state | Raw result | Event candidate | Adapter state sau bước |
|---|---|---|---|---|
| ACTIVE | CONNECTED | Hợp lệ | `READING` | CONNECTED |
| ACTIVE | CONNECTED | Mất kết nối | `DISCONNECT` | DISCONNECTED |
| ERROR | DISCONNECTED | Vẫn mất kết nối | Không event theo DR-01 candidate | DISCONNECTED |
| ERROR | DISCONNECTED | Hợp lệ trở lại | `RECOVER`, không kèm READING | CONNECTED |
| ACTIVE | CONNECTED sau recovery | Hợp lệ ở bước kế | `READING` | CONNECTED |
| INACTIVE | Bất kỳ | Bất kỳ | Không event | Không đổi |
| ACTIVE | CONNECTED | Phi vật lý/bool/NaN/infinity | `INVALID_DATA` | CONNECTED |

Quy tắc:

- `RECOVER` và `READING` không xuất hiện cùng bước cho cùng sensor.
- Reading đầu tiên sau recovery chỉ xuất hiện ở bước kế tiếp.
- Mất kết nối liên tục đang phụ thuộc DR-01; test tương ứng bị BLOCKED.
- Adapter gọi thuật toán TV2 theo từng sensor, dùng `location_id` để map sang legacy zone label.
- Nhiều sensor cùng location có connection state và event độc lập theo `sensor_id`.
- Orchestrator là thành phần duy nhất áp dụng event vào Sensor lifecycle.
