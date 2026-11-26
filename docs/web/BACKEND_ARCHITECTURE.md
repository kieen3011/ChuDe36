# Backend Architecture Candidate

## 1. Muc tieu

FastAPI la lop HTTP mong bao quanh Stable Python Core. Backend khong viet lai Sensor, DataSimulator, AlertSystem, StatisticsTracker hoac cac adapter. MVP la stateless: moi request mo phong tao object graph rieng, chay xong va tra response trong cung request.

```text
Browser
  -> FastAPI router + Pydantic validation
  -> SimulationService.run(request)
  -> request-scoped Core object graph
       MonitoringManager
       SimulationAdapter | DemoSimulation
       AlertSystem + AlertAdapter
       StatisticsTracker
       SnapshotCollector
  -> JSON response
```

## 2. Request lifecycle

1. Middleware gan request ID, gioi han body 64 KiB va FastAPI parse JSON bang Pydantic model.
2. Validator tu choi mode, seed, step count, interval, threshold va so khong huu han.
3. SimulationService tao moi toan bo dependency cho request.
4. Core chay dong bo, khong sleep. `step_interval_seconds` chi thay doi simulated time.
5. SnapshotCollector nhan actual event/readings/alerts/errors qua optional `record_step` hook.
6. Service tao history va response DTO tu cac ban sao record.
7. Object graph duoc giai phong sau response; khong luu session phia server.

## 3. SimulationService

Interface da trien khai:

```python
class SimulationService:
    def run(self, request: SimulationRunRequest, request_id: str | None = None) -> dict: ...
```

Service su dung factory request-scoped, khong nhan singleton mutable. `random` su dung SimulationAdapter va DataSimulator that. `demo` su dung approved DemoSimulation. MVP khong cho custom threshold.

## 4. SnapshotCollector

Collector la renderer headless co hook tuy chon va API renderer tuong thich:

```python
record_step(step_index=..., timestamp=..., events=..., readings=..., alerts=..., errors=..., cumulative_summary=...)
render_snapshot(readings, alerts, step_index, current_timestamp=None)
render_summary(summary)
```

Moi sensor duoc boc ngoai Reading Record bay truong:

```json
{
  "reading": {"sensor_id": "COLD-01", "sensor_type": "COLD_STORAGE", "location_id": "A", "status": "ACTIVE", "temperature": 5.0, "humidity": 90.0, "timestamp": "2026-11-24T08:00:00+07:00"},
  "freshness": "FRESH"
}
```

Gia tri freshness: `FRESH`, `STALE`, `NO_DATA`, `RECOVERY_PENDING`. Khong them truong vao Reading Record goc.

## 5. Frontend timeline replay

Response chua danh sach snapshot da sap theo `step_index`. Frontend luu response trong browser va dung timer UI de tang cursor. Timer nay khong goi lai backend va khong lien quan `step_interval_seconds`. Nguoi dung co the play, pause, tua hoac doi toc do ma khong thay doi simulated time.

Moi snapshot co `simulated_at`, event cua buoc, status/freshness va alert moi. Bieu do doc truc tiep cac history series cung timestamp. Cach nay phu hop serverless vi backend khong can process chay lien tuc.

## 6. Simulated time va real time

- `simulated_at`: tao tu simulation start time va step interval, dung cho reading/event/chart.
- `generated_at`: UTC wall clock luc backend tao response, chi dung cho metadata.
- `request_id`: correlation ID, khong phai simulation time hay persistent session ID.

## 7. Concurrency va isolation

- Khong co global manager, simulator, tracker, collector hoac mutable threshold.
- Cung seed + cung request tao cung simulation data, ngoai `request_id` va `generated_at`.
- Multiple workers va concurrent requests khong chia se state.
- MVP khong can lock, database, queue hoac background task.
- Endpoint la `def` hoac duoc chay trong worker thread vi core la CPU-bound synchronous code; khong block event loop bang `async def` goi truc tiep CPU work.

## 8. Compatibility

Console CLI va 92 core tests tiep tuc chay. File export CLI van duoc giu; HTTP request khong ghi file. Pure serializers chi thao tac trong bo nho.
