# Web Backend Test Plan

## 1. Framework va gates

Core gate van la `python -m unittest discover -v` voi toi thieu 92 tests. API tests dung `unittest` va HTTPX `ASGITransport`; HTTPX chi la development dependency.

## 2. Endpoint matrix

| ID | Test | Expected |
|---|---|---|
| API-01 | GET health | 200, schema/version, no simulation side effect |
| API-02 | GET config | 200, defaults/limits/copy, no mutable alias |
| API-03 | POST random | 200, real DataSimulator, deterministic with same seed |
| API-04 | POST demo | 200, approved 4/2/2/2 invariants |
| API-05 | Invalid mode | 422 canonical error |
| API-06 | Step count bool/0/101/string | 422 |
| API-07 | Seed empty/129 chars/wrong type | 422 |
| API-08 | Interval bool/0/NaN/infinity/too large | 400 or 422 per parser stage |
| API-09 | Bat ky custom threshold object | 422 |
| API-10 | Extra fields | 422 |
| API-11 | Malformed JSON | 400 canonical error |
| API-12 | Pure CSV serializer | Parseable, canonical alert schema |
| API-13 | Pure JSON serializer | Strict JSON, khong NaN/infinity |

## 3. Timeline va freshness

- Snapshot count bang step count.
- Step index lien tuc va simulated timestamp cach dung interval.
- Reading Record van dung bay truong.
- Initial sensor chua co data la `NO_DATA`.
- Disconnect co ERROR va stale/old measurement ro rang.
- Repeated disconnect khong tang outage error.
- Sau recover la `RECOVERY_PENDING`, alert level khong NORMAL moi.
- Reading accepted ke tiep la `FRESH`.
- Stale measurement khong tao environmental alert.
- History giu timestamp/freshness va JSON serializable.

## 4. Isolation va concurrency

- Hai sequential requests cung seed co simulation data bang nhau.
- Mutation response/request thu nhat khong anh huong request sau.
- Hai request dung threshold input dictionary giong nhau van isolated.
- Parallel random/demo requests khong tron alerts, errors, snapshots, seed hay summary.
- Stress local: 4 concurrent requests, moi request 100 steps.
- Khong file output chung va khong co file moi trong repository/temp session path ngoai library internals.

## 5. Security va performance

- Body vuot app limit -> 413.
- Khong cho filesystem path field.
- Error 500 khong lo stack/path.
- CORS preflight chi chap nhan approved origin/method/header.
- Benchmark p50/p95 cho 10, 100, 500 steps; do response bytes va peak memory.
- Response 500 steps phai nam duoi platform payload budget co safety margin.
- OpenAPI chi liet ke ba endpoint da trien khai.

## 6. Console regression

- 92 core tests PASS.
- `python main.py`, random, demo PASS.
- CSV/JSON CLI export van strict-valid.
- TV2/TV3 standalone demos van PASS.
- Standard-library statistics khong bi shadow.

## 7. Deployment smoke tests

- `/api/health`, `/api/config` tren preview deployment.
- Random/demo small request.
- CORS tu preview frontend.
- Cold start va warm latency.
- Logs khong co secret/local path.
- Verify platform timeout, body/response limit va Python version thuc te.
