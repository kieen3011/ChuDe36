# ChuDe36 — IoT Warehouse Monitoring System

Chương trình Python mô phỏng giám sát nhiệt độ và độ ẩm cho ba khu vực kho.

## Cai dependency Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements.txt` la runtime; `requirements-dev.txt` them HTTPX cho test. Console Core van chay doc lap ma khong can FastAPI.

## Chay Console

```powershell
python main.py
python main.py --mode random
python main.py --mode demo
```

Mặc định là `random`: chương trình chạy 10 bước bằng DataSimulator thật, mỗi bước tương ứng 60 giây mô phỏng, dùng seed công khai `CHUDE36-DEMO` và không sleep thực tế. `demo` chạy chuỗi event xác định qua cùng pipeline production để minh họa NORMAL, WARNING, CRITICAL, vi phạm hai metric, disconnect, recovery và invalid data.

Kết quả được ghi vào:

- `output/alert_logs.csv`
- `output/report.json`

## Kiến trúc

- TV1: `sensor.py`, `monitoring_manager.py`, `main.py`, `config.py`.
- TV2: `data_simulator.py`, được nối qua `SimulationAdapter`.
- TV3: `alert_system.py`, được nối qua `AlertAdapter`.
- TV4: `statistics_tracker.py`.
- TV5: `display.py`.
- Contract adapters: `integration_adapters.py`.

Core Location ID là `A`, `B`, `C`. Các nhãn `Khu A/B/C` chỉ được dùng tại biên tương thích với module cũ.

## Kiểm thử

```powershell
python -m unittest discover -v
python -m compileall -q sensor.py monitoring_manager.py main.py config.py data_simulator.py alert_system.py statistics_tracker.py integration_adapters.py display.py tests
```

Phase 3B: 92 test PASS, gồm 77 test cũ được bảo toàn và 15 regression test cho export fail-closed, freshness, session isolation, CLI demo và encoding portability.

Chi tiết contract và kết quả tích hợp nằm trong `docs/integration/`.

## Chay FastAPI Backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn web_api.app:app --host 127.0.0.1 --port 8000
```

Mo Swagger UI tai `http://127.0.0.1:8000/docs`. Endpoint:

- `GET /api/health`
- `GET /api/config`
- `POST /api/simulations/run`

Random body: `{"mode":"random","seed":"sample-01","step_count":10,"step_interval_seconds":60}`.

Demo body: `{"mode":"demo"}`. Backend tra full timeline de frontend replay va khong ghi report file trong HTTP request.

## Chay tat ca test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m compileall -q .
```

Tai lieu Backend nam trong `docs/web/`.
