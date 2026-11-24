# Thiết kế TV1 — Sensor Architecture and Integration

## Ý định

Hoàn thiện phần Kiên theo Master Handoff V1.0: mô hình cảm biến hướng đối tượng, registry cảm biến và Application Orchestrator. Kết quả phải đủ ổn định để TV2–TV5 tích hợp mà không thay đổi API đã thống nhất.

## Mục tiêu và giới hạn

- Triển khai `Sensor`, ba thin subclass và `MonitoringManager` đúng contract.
- Triển khai `main.py` làm orchestrator, chỉ phụ thuộc interface của TV2–TV5.
- Bảo vệ chống đánh giá stale reading và tách Environmental Alert khỏi Device/Data Error.
- Chỉ dùng Python standard library; không triển khai thay module TV2–TV5.
- Không bổ sung threshold, Random Walk, thống kê, export hoặc display logic.

## Cách tiếp cận

1. **Module tách theo trách nhiệm (chọn):** `sensor.py`, `monitoring_manager.py`, `main.py`, `config.py`. Cách này phản ánh ownership, dễ test độc lập và ít coupling.
2. Một module TV1 duy nhất: ít file hơn nhưng trộn domain model, registry và orchestration, khó tích hợp và bảo vệ ownership.
3. Package nhiều tầng: mở rộng tốt hơn nhưng quá mức cần thiết cho MVP tám ngày.

Chọn cách 1 vì phù hợp trực tiếp với baseline, DRY/YAGNI và repository hiện đang trống.

## Thiết kế

- `Sensor` là concrete base class. Trạng thái giới hạn trong `ACTIVE`, `INACTIVE`, `ERROR`; measurement cuối cùng chỉ thay thế sau khi toàn bộ input hợp lệ. ID được MonitoringManager kiểm tra khi đăng ký hoặc lookup, đúng phạm vi contract đã chốt.
- Timestamp dùng `datetime.fromisoformat`, chấp nhận ISO 8601 hợp lệ (bao gồm hậu tố `Z` sau khi chuẩn hóa để parser standard-library xử lý), giữ nguyên chuỗi đầu vào trong reading.
- `MonitoringManager` dùng `dict[str, Sensor]` để lookup trung bình O(1), giữ insertion order để snapshot ổn định.
- `run_simulation(...)` trong `main.py` nhận dependency qua tham số. Orchestrator chỉ gọi các interface contract, tạo timestamp xác định từ `start_time + step_index * step_interval`, và chỉ gọi `AlertSystem.evaluate()` ngay sau `update_measurement()` trả `True`.
- `DISCONNECT`, `RECOVER`, `INVALID_DATA` tạo Error Record cho tracker qua một schema TV1 tối thiểu, được ghi rõ là integration assumption do Master Handoff chưa khóa Error Record Schema.

## Kiểm thử

Dùng `unittest`. Unit test bao phủ validation, schema, inheritance, registry và exception propagation. Orchestrator test dùng test double cho TV2–TV5 vì repository chưa có implementation thật; không tuyên bố real integration PASS.

## Rủi ro tích hợp

- Error Record Schema và Summary Schema chưa được chốt đầy đủ.
- API constructor cụ thể của TV5 chưa có class contract, chỉ có hai hàm render; orchestrator chấp nhận object có các method tương ứng.
- TV2–TV5 chưa tồn tại nên chỉ xác minh mock integration.
