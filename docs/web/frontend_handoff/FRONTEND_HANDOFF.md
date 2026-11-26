# Frontend Handoff — Frozen Backend API

## Baseline va scope

- Backend branch base: `6352ba7d8b9bad090a7d412833726684b1a052d0`.
- Stable Python Core origin: `8428be86d16f8058a8dd866fb6c9310ed3d04ba0`.
- API version: `1`.
- MVP la stateless; moi run tra full timeline, khong co session registry.

Frontend chi can ba endpoint:

| Method | Path | Muc dich |
|---|---|---|
| GET | `/api/health` | Liveness va version |
| GET | `/api/config` | Modes, defaults, limits, sensors va thresholds |
| POST | `/api/simulations/run` | Chay random hoac demo |

## Cach dung

Random request dung fixture `random-request.json`. Demo chi gui `{"mode":"demo"}`; khong gui seed, step count, interval hoac threshold override.

Response co `timeline` day du. Frontend play, pause, next, previous, replay va doi playback speed bang cursor local; khong goi lai backend khi di chuyen timeline. Dung `timeline[n].cumulative_summary` cho thong ke tai buoc dang xem va `summary` cho ket qua cuoi cung.

Reading Record luon co bay field. `freshness` nam trong sensor wrapper, khong them vao reading. Khong hien thi stale/recovery-pending value nhu du lieu moi va khong tu tao alert tu reading.

## HTTP behavior

- Simulation response co `Cache-Control: no-store`.
- `X-Request-ID` trung voi `metadata.request_id` neu request ID hop le.
- Validation error dung canonical `error` object; frontend khong parse raw exception text.
- Public limit: 100 steps; body limit: 64 KiB.
- CORS development mac dinh cho `127.0.0.1:5173` va `localhost:5173`.

## Fixture provenance

`openapi.json`, config, random/demo response va error examples duoc sinh tu `create_app()` bang HTTPX ASGI transport trong clean Phase 4C environment. Demo fixture da xac minh 4 alerts, 2 WARNING, 2 CRITICAL va 2 errors.
