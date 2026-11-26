# Performance Benchmark — Phase 4B

Ngay do: 2026-11-26. Runtime: CPython 3.13.14, Windows 11 10.0.26300, Intel64 Family 6 Model 186, 16 logical CPUs. Service duoc goi in-process; do bang `perf_counter`, `tracemalloc` va strict `json.dumps`. Khong bao gom HTTP network, cold start hoac hosting overhead.

| Steps | Samples | Execution p50/p95 ms | Serialization p50/p95 ms | Max response bytes | Max traced peak bytes |
|---:|---:|---:|---:|---:|---:|
| 10 | 20 | 3.755 / 4.686 | 1.435 / 1.795 | 21,510 | 106,738 |
| 100 | 10 | 35.315 / 37.521 | 15.389 / 24.294 | 204,875 | 885,375 |
| 500 internal | 5 | 172.266 / 198.389 | 72.558 / 79.175 | 995,131 | 4,190,541 |

Bon request dong thoi, moi request 100 steps: wall time 182.101 ms; 4/4 request ID rieng; moi timeline co 100 steps.

Public limit 100 co safety margin lon so voi default Vercel Function payload 4.5 MB va duration hien hanh, nhung benchmark local khong xac nhan cold start, quota, noisy-neighbor hoac production latency. Vercel Python runtime dang Beta. Giu public max 100; chi xem xet tang sau preview benchmark va Product Owner approval.

Nguon doi chieu: [Vercel Functions limits](https://vercel.com/docs/functions/limitations), [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python).
