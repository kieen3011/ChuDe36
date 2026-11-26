# Integration Decision Log

## Approved by Product Owner

| ID | Decision | Status |
|---|---|---|
| D01 | Core Location ID là `A/B/C` | APPROVED |
| D02 | Hybrid adapter-first cho TV2 và TV3 | APPROVED |
| D03 | Reading/Event/Alert schemas theo contract | APPROVED |
| D04 | Summary dùng `error_count`, thêm `errors_by_type` | APPROVED |
| D06 | `unittest` là framework chính | APPROVED |
| D07 | Đổi `statistics.py` thành `statistics_tracker.py` ở Phase 2 | APPROVED FOR PHASE 2 |
| D08 | CLI mặc định 10 bước, 60 giây/bước, seed cấu hình, không sleep | APPROVED CANDIDATE |
| D10 | Validation trước state/dedup, JSON không NaN, không stale alert | APPROVED |
| D11 | Export fail-closed bằng temp file và `os.replace`, không copy trực tiếp lên destination | APPROVED PHASE 3B |
| D12 | Freshness truyền tại display boundary, không đổi Reading Record | APPROVED PHASE 3B |
| D13 | Mỗi AlertSystem deep-copy threshold configuration | APPROVED PHASE 3B |
| D14 | CLI có `random` mặc định và `demo` deterministic | APPROVED PHASE 3B |

## Threshold verification

| Evidence | A | B | C | Delta |
|---|---|---|---|---|
| Master Handoff V1.0 | `2–8`, `85–95` inclusive | `18–25`, humidity `<60` | temperature `<30`, humidity `40–60` | `3°C`, `10%` |
| `tests/fixtures.py` | Khớp | Khớp, max exclusive | Khớp, max exclusive | Không chứa delta |
| `alert_system.py` | Phần lớn khớp | Sai boundary, delta `5/15` | Sai boundary, delta `5/15` | Mâu thuẫn |

Kết luận candidate: dùng Master Handoff V1.0 cho delta `3°C/10%`. Đây là bằng chứng contract gốc, không suy luận từ implementation.

## Decisions approved for Phase 2

### DR-01 — Continuous disconnect counting — APPROVED

Chỉ phát `DISCONNECT` và ghi một error ở bước chuyển `CONNECTED → DISCONNECTED`; các bước tiếp tục mất kết nối không tạo error mới. Một lần `RECOVER` kết thúc outage.

Ảnh hưởng: error_count theo số outage thay vì số bước mất kết nối.

### DR-02 — Nullable Error Record identifiers — APPROVED

- `sensor_id` bắt buộc với `DISCONNECT` và `INVALID_DATA` khi event có ID hợp lệ.
- `sensor_id` có thể `None` khi event thiếu/sai kiểu ID.
- `location_id` có thể `None` với `UNKNOWN_SENSOR` hoặc khi không thể lookup Sensor.
- `timestamp` luôn bắt buộc và phải bằng timestamp của bước.

### DR-03 — Seed mặc định — APPROVED

Dùng chuỗi public `CHUDE36-DEMO`, không dùng MSSV thật.

### DR-04 — TV5 compatibility shape — APPROVED

Tạo bản sao Summary và thêm `total_errors` dẫn xuất từ `error_count`. Không duy trì hai counter.

## Implementation boundary

- Adapter được triển khai trong `integration_adapters.py`.
- Legacy API của TV3 được giữ; structured method được bổ sung tối thiểu.
- `statistics.py` đã đổi thành `statistics_tracker.py`.
- Chưa commit, push hoặc merge.

## Phase 3B release decisions

- Random mode tiếp tục dùng DataSimulator thật, không chỉnh thuật toán để ép cảnh báo.
- Demo mode phát event xác định nhưng vẫn đi qua Sensor, AlertSystem và StatisticsTracker production.
- Standalone demo chỉ cấu hình `errors="replace"` cho stdout bên trong entry point; import module không đổi encoding toàn hệ thống.
- Dữ liệu demo công khai dùng `CHUDE36-DEMO`, không dùng định danh cá nhân.
