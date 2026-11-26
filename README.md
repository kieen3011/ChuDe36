# ChuDe36 — IoT Warehouse Monitoring System

Chương trình Python mô phỏng giám sát nhiệt độ và độ ẩm cho ba khu vực kho.

## Chạy chương trình

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
