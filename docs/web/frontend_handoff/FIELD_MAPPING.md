# Frontend Field Mapping

| Backend field | Frontend use |
|---|---|
| `metadata.request_id` | Correlation/debug ID |
| `metadata.mode` | Nhan random/demo |
| `metadata.actual_step_count` | Gioi han timeline cursor |
| `metadata.simulated_start/end` | Khoang thoi gian mo phong |
| `timeline[].step_index` | Thu tu replay |
| `timeline[].simulated_at` | Timestamp dang hien thi |
| `timeline[].events` | Su kien thuc tai buoc |
| `timeline[].sensors[].reading` | Snapshot sensor bay field |
| `timeline[].sensors[].freshness` | FRESH/STALE/NO_DATA/RECOVERY_PENDING |
| `timeline[].alerts` | Alert moi cua buoc |
| `timeline[].errors` | Error moi cua buoc |
| `timeline[].cumulative_summary` | Counters tinh den buoc dang xem |
| `readings` | Final sensor snapshot |
| `temperature_history` | Series nhiet do theo sensor ID |
| `humidity_history` | Series do am theo sensor ID |
| `alerts` | Tat ca canonical environmental alerts |
| `errors` | Tat ca hardware/data errors |
| `summary` | Canonical final summary |
| `statistics.by_location` | Final aggregation theo A/B/C |
| `statistics.by_severity` | Final WARNING/CRITICAL totals |

Reading Record fields: `sensor_id`, `sensor_type`, `location_id`, `status`, `temperature`, `humidity`, `timestamp`.

Freshness presentation:

- `FRESH`: co the danh gia va hien thi nhu current value.
- `STALE`: gia tri cu; khong gan alert level moi.
- `NO_DATA`: hien thi N/A.
- `RECOVERY_PENDING`: sensor da active lai nhung dang cho reading moi.

Location IDs trong API la `A`, `B`, `C`. Frontend co the map sang nhan hien thi `Khu A/B/C` ma khong thay doi ID trong data.
