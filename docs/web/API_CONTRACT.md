# API Contract — Phase 4B

Base path: `/api`. Media type: `application/json`. API version: `1`.

## Endpoint matrix

| Method | Path | Success | Muc dich |
|---|---|---:|---|
| GET | `/api/health` | 200 | Liveness va version |
| GET | `/api/config` | 200 | Default, limits va approved core config |
| POST | `/api/simulations/run` | 200 | Chay random hoac demo va tra full timeline |

MVP khong co session endpoint hoac server export endpoint. Frontend se tai CSV/JSON tu response da nhan; pure in-memory serializers duoc giu cho consumer noi bo.

## Run request

```json
{
  "mode": "random",
  "seed": "CHUDE36-DEMO",
  "step_count": 10,
  "step_interval_seconds": 60.0,
  "thresholds": null
}
```

- `mode`: bat buoc, `random` hoac `demo`.
- `seed`: 1..128 ky tu; mac dinh `CHUDE36-DEMO`.
- `step_count`: strict integer 1..100; boolean bi tu choi.
- `step_interval_seconds`: strict finite number 0.001..3600; boolean, NaN va infinity bi tu choi.
- `thresholds`: chi nhan `null` hoac bo qua. Custom threshold chua duoc ho tro.
- Extra fields, filesystem path va serialized Python object bi tu choi.
- Demo request chi nhan `{"mode":"demo"}`; seed, step count, interval hoac thresholds duoc truyen ro rang deu la conflict.

Demo effective contract: 10 steps, interval 60 giay, khong seed. Ket qua: 4 alerts, 2 WARNING, 2 CRITICAL va 2 system errors.

## Run response

Response gom metadata, timeline, final readings, temperature/humidity history, alerts, errors, canonical summary va statistics theo location/severity. Timeline chua actual events, sensor wrappers, alert moi, error moi va cumulative summary tung buoc.

Reading Record giu dung bay field: `sensor_id`, `sensor_type`, `location_id`, `status`, `temperature`, `humidity`, `timestamp`. `freshness` nam ben ngoai record va chi co `FRESH`, `STALE`, `NO_DATA`, `RECOVERY_PENDING`.

Response simulation co `Cache-Control: no-store`. `X-Request-ID` trung voi `metadata.request_id`. Strict JSON khong chua NaN hoac infinity.

## Health va config

```json
{"status":"ok","api_version":"1","core_version":"8428be8"}
```

Config tra modes, defaults, public limits, sensor definitions, locations A/B/C, approved thresholds, freshness values va capabilities. Response dung deep copy, khong mutate Python Core.

## Canonical error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [{"field":"step_count","reason":"Input should be less than or equal to 100"}],
    "request_id": "correlation-id"
  }
}
```

| HTTP | Code | Khi nao |
|---:|---|---|
| 400 | `MALFORMED_JSON` | JSON syntax sai |
| 400 | `MALFORMED_REQUEST` | Content-Length khong hop le |
| 413 | `PAYLOAD_TOO_LARGE` | Body vuot 64 KiB |
| 422 | `VALIDATION_ERROR` | Schema/domain validation sai |
| 500 | `INTERNAL_ERROR` | Loi khong du kien, khong tra stack trace |

Swagger UI mac dinh tai `/docs`; dat `CHUDE36_DOCS_ENABLED=0` de tat `/docs`, `/redoc` va `/openapi.json`.

`openapi.json` freeze typed schema cho Reading Record, timeline, history, alerts, errors, summary, statistics va canonical error envelope. Runtime 422 khong dung FastAPI default error body.
