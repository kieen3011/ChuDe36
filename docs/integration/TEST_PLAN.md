# Integration Test Plan

Framework chính: `unittest`. Test Phase 1 dùng module production thật và được phép RED để chứng minh mismatch.

## Coverage matrix

| ID | Scenario | Expected after Phase 2 | Phase 1 status |
|---|---|---|---|
| T01 | Khởi tạo ba loại Sensor | 3 sensors đúng type/location | Existing PASS |
| T02 | Normal reading | Không có Alert Record | PASS |
| T03 | WARNING | Canonical WARNING | PASS |
| T04 | CRITICAL | Canonical CRITICAL | PASS |
| T05 | Hai metric vi phạm | Một alert, hai violated metrics | PASS |
| T06 | B humidity = 60 | WARNING | PASS |
| T07 | C temperature = 30 | WARNING | PASS |
| T08 | Disconnect | Một Error Record, Sensor ERROR | PASS |
| T09 | Disconnect liên tục | Một error mỗi outage | PASS |
| T10 | Recover | RECOVER riêng, reading bước sau | PASS |
| T11 | Invalid measurement | Error, không update/alert | PASS |
| T12 | bool/NaN/infinity | Bị từ chối | PASS |
| T13 | Stale reading | Không tạo alert | Existing PASS |
| T14 | Dedup alert hợp lệ | Lần hai trả False | PASS |
| T15 | Invalid rồi corrected cùng key | Corrected record True | PASS |
| T16 | Nhiều Sensor cùng location | Hoạt động độc lập, summary gộp location | PASS candidate |
| T17 | Summary tương thích TV5 | Không KeyError, một error counter | PASS |
| T18 | CSV export | CSV hợp lệ | PASS |
| T19 | JSON export | JSON chuẩn, không NaN | PASS |
| T20 | CLI entry point | Chạy đủ hệ thống, tạo output | PASS |
| T21 | Seed reproducibility | Cùng seed, cùng sequence | PASS candidate |
| T22 | Standard library statistics | Import không shadow | PASS |
| T23 | Regression suite | Toàn bộ test chạy bằng unittest | PASS |
| T24 | Replace failure CSV/JSON | Giữ destination cũ, cleanup temp, truyền exception | PASS Phase 3B |
| T25 | Serialization failure CSV/JSON | Giữ destination cũ, cleanup temp | PASS Phase 3B |
| T26 | Recovery pending reading | ACTIVE nhưng stale, không hiển thị NORMAL | PASS Phase 3B |
| T27 | Reading đầu sau recovery | Khôi phục freshness | PASS Phase 3B |
| T28 | Threshold isolation | Default và caller config được deep-copy | PASS Phase 3B |
| T29 | CLI demo | 4 alerts, 2 warning, 2 critical, 2 errors, A/B/C | PASS Phase 3B |
| T30 | CP1252 redirect | TV2/TV3 standalone demo exit 0 | PASS Phase 3B |

## Pytest to unittest mapping for TV4

| Existing pytest test | Planned unittest method | Assertion strength |
|---|---|---|
| `test_count_by_location_and_separate_severity` | `test_count_by_location_and_separate_severity` | Giữ nguyên |
| `test_single_event_when_both_metrics_violated` | `test_single_event_when_both_metrics_violated` | Giữ nguyên |
| `test_deduplication_by_sensor_id_and_timestamp` | `test_deduplication_by_sensor_id_and_timestamp` | Giữ nguyên |
| `test_record_error_separated_from_environmental_alerts` | `test_record_error_separated_from_environmental_alerts` | Giữ nguyên |
| `test_export_csv_and_json_to_provided_paths` | `test_export_csv_and_json_to_provided_paths` với `TemporaryDirectory` | Giữ nguyên |
| `test_invalid_alert_raises_error` | Hai test TypeError/ValueError cụ thể | Mạnh hơn |

Không xóa test pytest trong Phase 1. Việc chuyển đổi thuộc Phase 2.

## Phase 2 implementation order

1. Freeze DR-01 đến DR-04.
2. Đổi tên module statistics và chuyển test sang unittest.
3. Implement Simulation Adapter và state tests.
4. Implement Alert Adapter với structured violated metrics.
5. Sửa threshold boundary/delta bằng test biên.
6. Sửa Statistics validation/dedup/errors_by_type.
7. Tạo Summary compatibility view cho TV5.
8. Thêm composition root và CLI.
9. Chạy real E2E, export và toàn bộ regression suite.
