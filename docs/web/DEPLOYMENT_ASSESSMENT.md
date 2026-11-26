# Deployment Assessment Candidate

Assessment date: 2026-11-26.

## 1. Vercel evidence

Vercel Python runtime van la Beta, ho tro FastAPI va hien liet ke Python 3.12, 3.13, 3.14; dependency co the khai bao bang `requirements.txt` theo [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python).

Current documented constraints:

- Python bundle toi da 500 MB.
- Function filesystem read-only, chi `/tmp` writable scratch toi da 500 MB; xem [Vercel runtimes](https://vercel.com/docs/functions/runtimes).
- Request/response payload mac dinh toi da 4.5 MB; xem [Vercel Functions limits](https://vercel.com/docs/functions/limitations).
- Hobby memory hien tai 2 GB/1 vCPU theo official limits.
- Duration phu thuoc Fluid Compute/plan/config va co the thay doi; can verify project settings truoc deploy, khong dua vao maximum marketing de thiet ke MVP.
- Python runtime dang Beta, day la rui ro deployment chu khong phai bang chung khong dung duoc.

## 2. Fit voi kien truc candidate

Stateless synchronous request phu hop serverless hon session/background loop. Backend khong can persistent filesystem; export in-memory phu hop ephemeral/read-only filesystem. Core chi dung Standard Library ngoai FastAPI stack, nen bundle du kien nho.

Rui ro chinh la response timeline tang theo `sensor_count * step_count`. Benchmark local public max 100 steps cho response lon nhat 204,875 bytes, nho hon nhieu default 4.5 MB. Day khong phai benchmark production/cold-start. Internal 500 steps dat toi da 995,131 bytes va van khong duoc public.

## 3. Routing va frontend

Candidate repo co the dat FastAPI ASGI app trong `api/index.py` cho Vercel va static frontend o framework/project rieng hoac cung deployment sau Phase 5. CORS chi can khi frontend/backend khac origin. Exact routing/vercel.json phai duoc prove tren preview deployment Phase 4B/4C.

## 4. Alternative hosting

Render, Railway, Fly.io hoac container host co the phu hop neu can predictable long-running process, persistent service hoac it phu thuoc Python Beta. MVP hien tai khong can cac tinh nang do. Khong chot provider o Phase 4A; chay benchmark va preview smoke test tren Vercel truoc, giu ASGI app portable de co the chuyen host.

## 5. Recommendation

Vercel la **conditional candidate**, khong phai approved production host. Dieu kien:

1. Preview deployment dung supported Python version.
2. Lap lai benchmark tren preview, gom cold/warm latency va 100-step response.
3. Cold start chap nhan duoc cho demo hoc phan.
4. CORS/static routing duoc smoke test.
5. Free-tier quota va Fluid Compute setting duoc Product Owner xac nhan.

Neu mot dieu kien that bai, dung portable ASGI deployment tren host khac thay vi thay doi Stable Python Core.
