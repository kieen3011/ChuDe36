# Frontend Export Contract

MVP khong co server export endpoint. Frontend export tu simulation response da nhan, khong chay lai simulation.

## JSON

- Xuat full response object bang UTF-8 JSON.
- Khong thay doi alerts, errors, summary hoac timestamp.
- JSON phai tu choi NaN va infinity.
- Suggested filename: `chude36-report.json`.

## CSV alerts

Thu tu canonical column:

```text
sensor_id,location_id,timestamp,severity,violated_metrics,temperature,humidity
```

- Mot alert la mot row, ke ca khi vi pham hai metric.
- `violated_metrics` duoc noi bang dau phay trong mot CSV cell va phai duoc CSV-quote dung chuan.
- Khong gop system errors vao environmental alert CSV.
- Suggested filename: `chude36-alerts.csv`.

Backend co pure in-memory reference serializers trong `web_api/services/serializers.py`. Frontend co the dung native browser Blob/download nhung output semantics phai giu nhu tren. Khong gui filesystem path ve backend.
